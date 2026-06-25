import numpy as np
from numpy.typing import NDArray
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,QHBoxLayout,QDialog,QTableWidget,QTableWidgetItem,
    QLabel, QMessageBox,QGroupBox,QLineEdit,QRadioButton,QPushButton,QTextEdit,QGridLayout
)
from PySide6.QtGui import QAction, QKeySequence,QDoubleValidator
from PySide6.QtCore import Qt

from src.data import CPSC_Data,PipCalculate

class ResultDialog(QDialog):
    """结果展示弹窗"""
    def __init__(self,score:float,R:NDArray[np.float64],data:dict[str,str|float|None],parent = None):
        """分数，隶属矩阵，输入数据字典"""
        super().__init__(parent)
        self.setWindowTitle("评价结果")
        self.resize(600, 700)

        layout = QVBoxLayout()
        
        
        # ===== 数据区、评价区（只读，但可鼠标选中复制）=====
        self.data_text_edit=QTextEdit()
        self.data_text_edit.setReadOnly(True)  # 禁止编辑，但保留选中
        self.result_text_edit = QTextEdit()
        self.result_text_edit.setReadOnly(True)  # 禁止编辑，但保留选中
        # 确保文本可被鼠标选中
        self.result_text_edit.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.data_text_edit.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.data_text_edit.setFixedHeight(100)
        self.result_text_edit.setFixedHeight(100)
        data_text=''
        for key,value in data.items():
            data_text += f"{CPSC_Data.alias_name_trans()[key]}：{value}； " if value else ''
        result_text = f"腐蚀防护系统质量评价得分为{score:.2f}，"
        if score>=90:
            result_text+='等级评价为“1”级，系统功能完好，满足设计要求，在6年的检验周期内能有效使用'
        elif score>=80:
            result_text+='等级评价为“2”级，系统基本完好但存在一些不影响防护效果的缺陷,能基本满足设计要求,3年~6年的检验周期内能使用'
        elif score>=70:
            result_text+='等级评价为“3”级，系统整体状况较差，存在缺陷，不能完全满足设计要求，在使用单位采取适当措施后，可在1年~3年检验周期内在限定的条件下使用'
        else:
            result_text+='等级评价为“4”级，系统缺陷严重,不能满足设计要求,不能有效防止金属管体腐蚀,使用单位应采取重大维修'

        self.data_text_edit.setPlainText(data_text)
        self.result_text_edit.setPlainText(result_text)
        layout.addWidget(QLabel("输入数据"))
        layout.addWidget(self.data_text_edit)
        layout.addWidget(QLabel("评价文本"))
        layout.addWidget(self.result_text_edit)
        
        #   隶属矩阵展示
        self.detail_matrix=QGroupBox('隶属矩阵')
        detail_layout=QVBoxLayout()
        rows,cols=R.shape
        headers=[
            '外防腐层状况',
            '阴极保护有效性',
            '土壤腐蚀性',
            '杂散电流干扰',
            '排流效果'
            ]
        self.table=QTableWidget()
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        self.table.setVerticalHeaderLabels(headers)
        for i in range(rows):
            for j in range(cols):
                item = QTableWidgetItem(f"{R[i, j]:.3f}")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, j,item)
        detail_layout.addWidget(self.table)

        lines = ["$\\begin{bmatrix}"]
    
        for row in R:
            line = "    " + " & ".join(f"{x:.3f}" for x in row) + " \\\\"
            lines.append(line)
        
        lines.append("\\end{bmatrix}$")

        self.latex_text = "\n".join(lines)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_copy_table = QPushButton("📊 复制表格到 Excel")
        btn_copy_latex = QPushButton("📄 复制 LaTeX")
        btn_copy_table.clicked.connect(self._copy_table)
        btn_copy_latex.clicked.connect(self._copy_latex)

        btn_row.addWidget(btn_copy_table)
        btn_row.addWidget(btn_copy_latex)
        btn_row.addStretch()
        detail_layout.addLayout(btn_row)
        self.detail_matrix.setLayout(detail_layout)
        layout.addWidget(self.detail_matrix)
        self.setLayout(layout)

    def _copy_table(self):
        """把整个表格转为制表符分隔文本，写入剪贴板"""
        table = self.table

        rows = table.rowCount()
        cols = table.columnCount()
        
        lines = []
      
        for r in range(rows):
            line = [table.item(r, c).text() for c in range(cols)]
            lines.append("\t".join(line))
        
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)

    def _copy_latex(self):
        """复制 LaTeX 公式源码到系统剪贴板"""
        text = self.latex_text
        QApplication.clipboard().setText(text)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("基于GB/T 19285-2026 的埋地钢质管道腐蚀防护系统质量等级评价")
        self.resize(400, 300)

        central=QWidget()
        
        main=QVBoxLayout()

        #   防腐层参数
        c_coat=QGroupBox("防腐层参数")
        c_coat_layout=QHBoxLayout()
        rg_value=QHBoxLayout()
        self.coat=QRadioButton("PE防腐层")
        self.coat_0=QRadioButton("沥青防腐层")
        c_coat_layout.addWidget(self.coat)
        c_coat_layout.addWidget(self.coat_0)
        rg_value.addWidget(QLabel("管径（mm）"))
        self.d_input=QLineEdit()
        self.d_input.setValidator(QDoubleValidator(25.0, 10000.0, 0))  # 设置输入范围和小数位数
        self.d_input.setPlaceholderText("请输入25-10000的数值")
        rg_value.addWidget(self.d_input)
        rg_value.addWidget(QLabel("Rg值（kΩ·m²）"))
        self.rg_input=QLineEdit()
        self.rg_input.setValidator(QDoubleValidator(0.1, 10000.0, 2))  # 设置输入范围和小数位数
        self.rg_input.setPlaceholderText("请输入0.1-10000的数值")
        rg_value.addWidget(self.rg_input)
        # rg_value.addWidget(QLabel("kΩ·m²"))
        c_coat_layout.addLayout(rg_value)

        y_value=QHBoxLayout()
        y_value.addWidget(QLabel("Y值（dB/m）"))
        self.y_input=QLineEdit()
        self.y_input.setValidator(QDoubleValidator(0.001, 0.5, 3))  # 设置输入范围和小数位数
        self.y_input.setPlaceholderText("请输入0.001-0.5的数值")
        y_value.addWidget(self.y_input)
        # y_value.addWidget(QLabel("dB/m"))
        c_coat_layout.addLayout(y_value)
        
        p_value=QHBoxLayout()
        p_value.addWidget(QLabel("P值（处/100m）"))
        self.p_input=QLineEdit()
        self.p_input.setValidator(QDoubleValidator(0.1, 5.0, 1))  # 设置输入范围和小数位数
        self.p_input.setPlaceholderText("请输入0.1-5.0的数值")
        p_value.addWidget(self.p_input)
        # p_value.addWidget(QLabel("处/100m"))
        c_coat_layout.addLayout(p_value)

        c_coat.setLayout(c_coat_layout)

        #   阴极保护
        cp=QGroupBox("阴极保护参数")
        cp_value=QHBoxLayout()
        cp_value.addWidget(QLabel("保护率（%）"))
        self.cp_input=QLineEdit()
        self.cp_input.setValidator(QDoubleValidator(0.1, 100.0, 1))  # 设置输入范围和小数位数
        self.cp_input.setPlaceholderText("请输入0.1-100.0的数值")
        cp_value.addWidget(self.cp_input)
        # cp_value.addWidget(QLabel("%"))
        cp.setLayout(cp_value)

        #   土壤腐蚀性
        soil_corrosion=QGroupBox("土壤腐蚀性")
        soil_layout=QHBoxLayout()
        soil_layout.addWidget(QLabel("土壤腐蚀性N值"))
        self.soil_input=QLineEdit()
        self.soil_input.setValidator(QDoubleValidator(0.1, 35.0, 1))  # 设置输入范围和小数位数
        self.soil_input.setPlaceholderText("请输入0.1-35.0的数值")
        soil_layout.addWidget(self.soil_input)
        soil_corrosion.setLayout(soil_layout)

        #   杂散电流干扰
        stray_current=QGroupBox("杂散电流干扰")
        stray_layout=QHBoxLayout()
        stray_grid=QGridLayout()
        self.cp=QRadioButton("有阴极保护")
        self.cp_0=QRadioButton("未实施阴极保护")
        stray_grid.addWidget(self.cp,0,0)
        stray_grid.addWidget(self.cp_0,0,1)

        self.soil_rho = QLineEdit()
        self.soil_rho.setValidator(QDoubleValidator(0, 10000.0, 0))  # 设置输入范围和小数位数
        self.soil_rho.setPlaceholderText("请输入0~10000的数值")
        stray_grid.addWidget(QLabel('土壤电阻率（Ω·m）'),0,2)
        stray_grid.addWidget(self.soil_rho,0,3)
        
        self.stable_stray_input=QLineEdit()
        self.stable_stray_input.setValidator(QDoubleValidator(-10000.0, 10000.0, 0))  # 设置输入范围和小数位数
        self.stable_stray_input.setPlaceholderText("请输入-10000~+10000的数值")
        stray_grid.addWidget(QLabel('稳态直流干扰—含IR降电位正向偏移（mV）'),1,0)
        stray_grid.addWidget(self.stable_stray_input,1,1)
        
        self.stable_stray_input_noir=QLineEdit()
        self.stable_stray_input_noir.setValidator(QDoubleValidator(-10000.0, 10000.0, 0))  # 设置输入范围和小数位数
        self.stable_stray_input_noir.setPlaceholderText("请输入-10000~+10000的数值")
        stray_grid.addWidget(QLabel('稳态直流干扰—无IR降电位正向偏移（mV）'),1,2)
        stray_grid.addWidget(self.stable_stray_input_noir,1,3)
        self.stray_input=QLineEdit()
        self.stray_input.setValidator(QDoubleValidator(0.1, 100.0, 1))  # 设置输入范围和小数位数
        self.stray_input.setPlaceholderText("请输入0.1-100.0的数值")
        stray_grid.addWidget(QLabel("动态直流干扰-电位正于阴保要求（或正于自然电位20mV）的占比%"),2,0)
        stray_grid.addWidget(self.stray_input,2,1)
        self.ac_input=QLineEdit()
        self.ac_input.setValidator(QDoubleValidator(0, 1000, 2))  # 设置输入范围和小数位数
        self.ac_input.setPlaceholderText("请输入0-1000的数值")
        stray_grid.addWidget(QLabel("交流电流密度（A/m²）"),2,2)
        stray_grid.addWidget(self.ac_input,2,3)
        stray_layout.addLayout(stray_grid)
        stray_current.setLayout(stray_layout)

        #   排流效果
        drainage=QGroupBox("排流效果")
        drainage_layout=QHBoxLayout()
        drainage_layout.addWidget(QLabel("排流效果评价（当杂散电流干扰评价为弱时有效，否则无效）"))
        self.drainage=QRadioButton("有效")
        self.drainage_0=QRadioButton("无效")
        drainage_layout.addWidget(self.drainage)
        drainage_layout.addWidget(self.drainage_0)
        drainage.setLayout(drainage_layout)

        #   控制按钮
        calculate_btn=QPushButton("计算")
        calculate_btn.clicked.connect(self.on_calculate)

        main.addWidget(c_coat)
        main.addWidget(cp)
        main.addWidget(soil_corrosion)
        main.addWidget(stray_current)
        main.addWidget(drainage)
        main.addWidget(calculate_btn)
        central.setLayout(main)
        self.setCentralWidget(central)
        
        menubar = self.menuBar()
        
        # --- 文件菜单 ---
        file_menu = menubar.addMenu("文件(&F)")  # &F 表示 Alt+F 快捷键
        
        # 新建：带图标、快捷键、状态栏提示
        action_new = QAction("新建(&N)", self)
        action_new.setShortcut(QKeySequence("Ctrl+N"))  # 快捷键
        action_new.setStatusTip("创建新文件")            # 状态栏提示
        action_new.triggered.connect(self.on_new)
        file_menu.addAction(action_new)
        
        file_menu.addSeparator()
        
        # 退出
        action_exit = QAction("退出(&Q)", self)
        action_exit.setShortcut(QKeySequence("Ctrl+Q"))
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # --- 编辑菜单（带子菜单） ---
        edit_menu = menubar.addMenu("编辑(&E)")
        
        # 子菜单：格式
        format_menu = edit_menu.addMenu("格式")  # 注意是 addMenu，不是 addAction
        format_menu.addAction("字体")
        format_menu.addAction("颜色")
        
        edit_menu.addSeparator()
        edit_menu.addAction("撤销")
        
        # 状态栏
        self.statusBar().showMessage("就绪")

    def on_new(self):
        self.label.setText("Ctrl+N 或 菜单→新建 被触发")

    def on_calculate(self):
        
       
        #   防腐层隶属向量计算
        d=float(self.d_input.text()) if self.d_input.text() else None
        y_input=float(self.y_input.text()) if self.y_input.text() else None
        p_input=float(self.p_input.text()) if self.p_input.text() else None
        rg_input=float(self.rg_input.text()) if self.rg_input.text() else None
        
        c_type="PE防腐层" if self.coat.isChecked() else "沥青防腐层"
        if not self.coat.isChecked() and not self.coat_0.isChecked():
            c_type = None
        
        #   阴极保护
        cp_input=0.01*float(self.cp_input.text()) if self.cp_input.text() else None
        # v_cp=MainWindow._vertical_calculate(cp_input,data["阴极保护区间"],True)
        
        #   土壤腐蚀性
        soil_input=float(self.soil_input.text()) if self.soil_input.text() else None
        # v_soil=MainWindow._vertical_calculate(soil_input,data["土壤腐蚀性区间"])

        #   杂散电流
        cp_exist='有阴保' if self.cp.isChecked()  else '无阴保'
        if not self.cp.isChecked() and not self.cp_0.isChecked():
            cp_exist=None
        soil_rho_input = float(self.soil_rho.text()) if self.soil_rho.text() else None
        p_move_ir_input = float(self.stable_stray_input.text()) if self.stable_stray_input.text() else None
        p_move_noir_input = float(self.stable_stray_input_noir.text()) if self.stable_stray_input_noir.text() else None
        stray_input=0.01*float(self.stray_input.text()) if self.stray_input.text() else None
        stray_input_ac=float(self.ac_input.text()) if self.ac_input.text() else None
   

        #   排流隶属向量
        # v_dra = np.array([1.0,0.0,0.0,0.0] if self.drainage.isChecked() else [0.0,0.0,0.0,1.0]) 
        drainage_eff='有效' if self.drainage.isChecked() else '无效'
        if not self.drainage.isChecked() and not self.drainage_0.isChecked():
            drainage_eff=None
        
        try:
            data0 = CPSC_Data(
                pip_d=d,
                c_rg=rg_input,
                c_p=p_input,
                c_y=y_input,
                c_type=c_type,
                cp_exist=cp_exist,
                cp_value=cp_input,
                dc_stray=stray_input,
                ac_stray=stray_input_ac,
                soil_n=soil_input,
                drainage=drainage_eff,
                soil_rho=soil_rho_input,
                p_move_ir=p_move_ir_input,
                p_move_noir = p_move_noir_input
            )
            result=PipCalculate(data0).calculate()     
            self.show_result(R=result[0],final_score=result[1],data=result[2])
        except ValueError as e:
            QMessageBox.warning(self, "输入验证失败", str(e))
    


    def show_result(self,R,final_score,data):
        dialog=ResultDialog(parent=self,R=R,score=final_score,data=data)
        dialog.exec()
