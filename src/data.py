import json
from functools import lru_cache, total_ordering
from typing import Sequence, Self

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.interpolate import CubicSpline
from pydantic import BaseModel, Field,model_validator

from utils import resource_path

def matrix_to_latex(arr: NDArray[np.float64], env: str = 'bmatrix') -> str:
    """numpy 二维数组 → LaTeX 矩阵公式"""
    lines = [' & '.join(f"{x:.3f}" for x in row) for row in arr]
    body = ' \\\\\n'.join(lines)
    return f"\\begin{{{env}}}\n{body}\n\\end{{{env}}}"

class B_matrix(np.ndarray):
    """相关矩阵类"""
    def __new__(cls, data:None|NDArray[np.float64] = None)->"B_matrix":
        obj = np.ones((5,5),dtype=np.float64).view(cls)

        if data is not None:
            arr = np.asarray(data, dtype=np.float64)
            if arr.shape != (5, 5):
                raise ValueError(f"优先度矩阵要求 shape=(5,5)，收到 {arr.shape}")
            # 以上三角（不含对角线）为准，强制下三角为倒数
            for i in range(5):
                for j in range(i + 1, 5):
                    v = float(arr[i, j])
                    if v == 0:
                        raise ZeroDivisionError(f"({i},{j}) 不能为 0，否则倒数无意义")
                    np.ndarray.__setitem__(obj, (i, j), v)
                    np.ndarray.__setitem__(obj, (j, i), 1.0 / v)
        return obj


#   优先度矩阵的特征向量
WEIGHTS: NDArray[np.float64] = np.array([0.402, 0.269, 0.099, 0.066, 0.163])
#   最终评分的向量
SCORE_HIGH: NDArray[np.float64] = np.array([100, 89, 79, 69])
SCORE_MID: NDArray[np.float64] = np.array([95, 85, 75, 65])
SCORE_LOW: NDArray[np.float64] = np.array([90, 80, 70, 60])


def _compute_membership(value: float, interval: Sequence[float]) -> NDArray[np.float64]:
    """根据分段线性隶属函数计算 4 维隶属向量。"""
    a, b, c = float(interval[0]), float(interval[1]), float(interval[2])
    u0, u1 = (a + b) / 2.0, (b + c) / 2.0
    v = np.zeros(4, dtype=np.float64)

    if value <= a:
        v[0] = 1.0
    elif value <= u0:
        v[0] = (value - u0) / (a - u0)

    if a <= value <= u0:
        v[1] = (value - a) / (u0 - a)
    elif u0 < value <= u1:
        v[1] = (value - u1) / (u0 - u1)

    if u0 <= value <= u1:
        v[2] = (value - u0) / (u1 - u0)
    elif u1 < value <= c:
        v[2] = (value - c) / (u1 - c)

    if u1 <= value <= c:
        v[3] = (value - u1) / (c - u1)
    elif value > c:
        v[3] = 1.0

    return v


@total_ordering
class V_membership(np.ndarray):
    """隶属向量类，即长度为4的向量，由取变量：值、区间、是否反转"""
    def __new__(
        cls,
        value: float | None = None,
        interval: Sequence[float] | pd.Series | NDArray[np.float64] | None = None,
        reverse: bool = False,
    ) -> "V_membership":
        obj = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64).view(cls)
        if value is None:
            return np.flip(obj).view(cls) if reverse else obj

        interval_arr = np.asarray(interval, dtype=np.float64)
        if interval_arr.size < 3:
            raise ValueError("interval 至少包含 3 个边界值")

        v = _compute_membership(float(value), interval_arr)
        if reverse:
            v = np.flip(v)
        return v.view(cls)

    def __lt__(self, other: "V_membership") -> bool:
        return tuple(np.round(self,4)) < tuple(np.round(other,4))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, np.ndarray):
            return NotImplemented
        return bool(np.allclose(self, other))

    def __hash__(self) -> int:
        # np.ndarray 默认不可 hash；此处仅作最小兼容，避免 total_ordering 在集合/字典中异常。
        return id(self)


@lru_cache(maxsize=None)
def _load_config() -> dict:
    with open(resource_path("19285-2026.json"), encoding="UTF-8") as f:
        return json.load(f)

class PipCalculate:
    def __init__(self,params:'CPSC_Data'):
        self.p = params

    @staticmethod
    def _interpolate(y: pd.Series, x: NDArray[np.float64] | list[float], x_new: float) -> float:
        """插值计算"""
        cs = CubicSpline(np.array(x), y.to_numpy())
        return float(cs(x_new))
    
    def _calc_coating(self, config: dict) -> V_membership:
        """计算防腐层评价隶属向量"""
        # Rg值，Y值计算
        coating_rg = V_membership(self.p.c_rg, config[f"{self.p.c_type}Rg值区间"], True)
        coating_p = V_membership(self.p.c_p, config[f"{self.p.c_type}P值区间"])

        # Y 值计算
        y_config = config[f"{self.p.c_type}Y值区间"]
        df = pd.DataFrame(y_config)
        pip_d_list = [float(t) for t in df.columns.to_list()]

        if self.p.pip_d is None:
            coating_y = V_membership()
        elif self.p.pip_d <= min(pip_d_list):
            coating_y = V_membership(self.p.c_y, y_config[str(int(min(pip_d_list)))])
        elif self.p.pip_d >= max(pip_d_list):
            coating_y = V_membership(self.p.c_y, y_config[str(int(max(pip_d_list)))])
        else:
            df["inter"] = df.apply(self._interpolate, axis=1, x=pip_d_list, x_new=self.p.pip_d)
            coating_y = V_membership(self.p.c_y, df["inter"])

        return min(coating_rg, coating_p, coating_y)
    
    def _calc_cp(self, config: dict) -> V_membership:
        """阴极保护隶属向量计算"""
        return V_membership(self.p.cp_value, config["阴极保护区间"], True)

    def _calc_soil(self, config: dict) -> V_membership:
        """土壤腐蚀性隶属向量计算"""
        return V_membership(self.p.soil_n, config["土壤腐蚀性区间"])

    def _calc_stray(self, config: dict) -> V_membership:
        """杂散电流隶属向量计算"""
        if self.p.dc_stray or self.p.ac_stray:
            # 存在动态干扰时，稳态干扰直接取无
            v_stable = V_membership()
        elif self.p.cp_exist == "有阴保":
            # 不存在动态干扰，且阴保全部有效，稳态干扰取无，否则取最大
            v_stable = V_membership() if not abs(self.p.cp_value - 1.0) < 1e-5 else V_membership(reverse=True)
        elif self.p.p_move_noir:
            v_stable = V_membership() if self.p.p_move_noir <= 20.0 else V_membership(reverse=True)
        elif self.p.soil_rho > 200.0:
            v_stable = V_membership() if self.p.p_move_ir <= 300.0 else V_membership(reverse=True)
        elif self.p.soil_rho < 15.0:
            v_stable = V_membership() if self.p.p_move_ir <= 20.0 else V_membership(reverse=True)
        else:
            v_stable = V_membership() if self.p.p_move_ir <= 1.5 * self.p.soil_rho else V_membership(reverse=True)

        v_dc = V_membership(self.p.dc_stray, config[f"直流干扰区间-{self.p.cp_exist}"])
        v_ac = V_membership(self.p.ac_stray, config["交流干扰区间"])
        return min(v_dc, v_ac, v_stable)

    def _calc_drainage(self) -> V_membership:
        """排流隶属向量"""
        return V_membership() if self.p.drainage == "有效" else V_membership(reverse=True)
    
    def _result(
        self,
        v_coat: V_membership,
        v_cp: V_membership,
        v_soil: V_membership,
        v_stray: V_membership,
        v_dra: V_membership,
    ) -> tuple[NDArray[np.float64], float, NDArray[np.float64],CPSC_Data]:
        """返回隶属矩阵及其LaTeX公式，最终得分，结果向量，原输入参数对象"""
        R_matrix = np.array([v_coat, v_cp, v_soil, v_stray, v_dra])
        R_matrix = np.where(np.abs(R_matrix) < 1e-5, 0.0, R_matrix)
        v_a = WEIGHTS @ R_matrix

        s_h = np.sum(v_a * SCORE_HIGH) / np.sum(v_a)
        s_m = np.sum(v_a * SCORE_MID) / np.sum(v_a)
        s_l = np.sum(v_a * SCORE_LOW) / np.sum(v_a)
        s_ = (s_h + s_m + s_l) / 3.0

        return R_matrix, matrix_to_latex(R_matrix), s_, v_a, self.p

    def calculate(self) -> tuple[NDArray[np.float64], str, float, NDArray[np.float64], CPSC_Data]:
        """返回隶属矩阵及其LaTeX公式、最终得分，结果向量，原输入参数对象"""
        config = _load_config()

        v_coat = self._calc_coating(config)
        v_cp = self._calc_cp(config)
        v_soil = self._calc_soil(config)
        v_stray = self._calc_stray(config)
        v_dra = self._calc_drainage()

        return self._result(v_coat, v_cp, v_soil, v_stray, v_dra)

# @dataclass
class CPSC_Data(BaseModel):
    """全体参数类"""
    model_config = {"populate_by_name": True}

    pip_d: float | None = Field(default = None,alias="管径（mm）")
    c_type: str | None = Field(default = None,alias="防腐层类型")
    c_rg: float | None = Field(default = None,alias="防腐层绝缘电阻率Rg值（kΩ·㎡）")
    c_p: float | None = Field(default = None,alias="防腐层破损点密度P值（处/100m）")
    c_y: float | None = Field(default = None,alias="防腐层电流衰减率Y值（dB/m）")
    cp_exist: str | None = Field(default = None,alias="是否建设有阴极保护")
    cp_value: float | None = Field(default = None,alias="阴极保护率")
    soil_n: float | None = Field(default = None,alias="土壤腐蚀性评价N值")
    soil_rho: float | None = Field(default = None,alias="土壤电阻率（Ω·m）")
    p_move_ir: float | None = Field(default = None,alias="含IR降的电位正向偏移（mV）")
    p_move_noir: float | None = Field(default = None,alias="无IR降的电位正向偏移（mV）")
    dc_stray: float | None = Field(default = None,alias="阴保管道电位正于要求的比例或无阴保管道正于自然电位20mV的比例")
    ac_stray: float | None = Field(default = None,alias="交流电流密度")
    drainage: str | None = Field(default = None,alias="排流效果")

    # def __post_init__(self):
    #     errors = self._validate()
    #     if errors:
    #         raise ValueError("；".join(errors))
    @model_validator(mode="after")
    def _validate(self) -> Self:
        errors: list[str] = []
        if not (self.pip_d and self.c_type):
            errors.append("缺少管径,防腐层类型")
        if not (self.c_rg or self.c_p or self.c_y):
            errors.append("缺少外防腐层评价")
        if not self.dc_stray and not self.ac_stray:
            if self.cp_exist == "无阴保" and not self.p_move_noir and not (self.soil_rho and self.p_move_ir):
                errors.append("缺少杂散电流评价")
        if not self.cp_exist:
            errors.append("缺少是否有阴极保护")
        if not self.cp_value and self.cp_exist == "有阴保":
            errors.append("缺少阴极保护率")
        if not self.soil_n:
            errors.append("缺少土壤腐蚀性得分")
        if not self.drainage:
            errors.append("缺少排流评价")
        if errors:
            raise ValueError('；'.join(errors))
        return self



   
