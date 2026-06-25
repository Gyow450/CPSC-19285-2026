from flask import Flask, render_template, request, jsonify
import os
import sys

from src.data import CPSC_Data, PipCalculate

app = Flask(__name__)

def _get_float(form, key):
    val = form.get(key, "").strip()
    return float(val) if val else None

def _get_str(form, key):
    val = form.get(key, "").strip()
    return val if val else None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        # 前端字段 → 后端 CPSC_Data 字段映射
        params = {
            "pip_d": _get_float(request.form, "pip_d"),
            "c_type": _get_str(request.form, "coat_type"),
            "c_rg": _get_float(request.form, "rg_value"),
            "c_p": _get_float(request.form, "p_value"),
            "c_y": _get_float(request.form, "y_value"),
            "cp_exist": _get_str(request.form, "cp_exist"),
            "cp_value": _get_float(request.form, "cp_rate"),   # 注意：后面要 /100
            "soil_n": _get_float(request.form, "soil_n"),
            "soil_rho": _get_float(request.form, "soil_rho"),
            "p_move_ir": _get_float(request.form, "stable_stray_ir"),
            "p_move_noir": _get_float(request.form, "stable_stray_noir"),
            "dc_stray": _get_float(request.form, "dc_stray"),
            "ac_stray": _get_float(request.form, "ac_stray"),
            "drainage": _get_str(request.form, "drainage"),
        }

        # 保护率：前端输入的是 %（如 100），后端需要小数（1.0）
        if params["cp_value"]:
            params["cp_value"] = params["cp_value"] / 100.0
        if params["dc_stray"]:
            params["dc_stray"] = params["dc_stray"] / 100.0

        data_obj = CPSC_Data(**params)
        calc = PipCalculate(data_obj)
        matrix, score, _ = calc.calculate()

        return jsonify({
            "success": True,
            "score": round(float(score), 2),
            "matrix": matrix.tolist()   # 5×4 嵌套数组
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"计算异常: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)