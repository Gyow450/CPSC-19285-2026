from functools import wraps
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, request, jsonify, session, redirect, url_for

from src.data import CPSC_Data, PipCalculate

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# 默认管理员账号：admin / admin123
# 首次运行后建议立即修改默认密码
DB_PATH = "users.db"

def init_db()->None:
    """初始化数据库，创建用户表并插入默认管理员"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)
    # 插入默认管理员（首次运行后应删除或改密码）
    admin_hash = generate_password_hash("admin123")
    conn.execute("""
        INSERT OR IGNORE INTO users (id, username, password_hash, is_admin)
        VALUES (1, 'admin', ?, 1)
    """, (admin_hash,))
    conn.commit()
    conn.close()

def verify_user(username, password)->bool:
    """验证用户名密码"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()
    
    if row is None:
        return False
    return check_password_hash(row[0], password)


def get_user(username: str) -> dict | None:
    """查询用户信息（包含管理员标识）"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, username, is_admin FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "username": row[1], "is_admin": bool(row[2])}


def admin_required(view):
    """仅管理员可访问"""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in") or not session.get("is_admin"):
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped_view


def login_required(view):
    """未登录用户重定向到登录页"""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def _get_float(form, key)-> float|None:
    val = form.get(key, "").strip()
    return float(val) if val else None

def _get_str(form, key)-> str|None:
    val = form.get(key, "").strip()
    return val if val else None

@app.route("/")
@login_required
def index():
    return render_template("index.html", active_page="index")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if verify_user(username, password):
            user = get_user(username)
            session["logged_in"] = True
            session["username"] = username
            session["is_admin"] = user.get("is_admin", False) if user else False
            return redirect(url_for("index"))
        return render_template("login.html", error="用户名或密码错误")
    return render_template("login.html", error=None)

@app.route("/admin/users")
@admin_required
def user_list():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, username, is_admin FROM users").fetchall()
    conn.close()
    return render_template("users.html", users=rows, active_page="users")


@app.route("/admin/users/add", methods=["POST"])
@admin_required
def user_add():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    is_admin = 1 if request.form.get("is_admin") == "1" else 0

    if not username or not password:
        return render_template("users.html", error="用户名和密码不能为空", users=get_all_users(), active_page="users")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), is_admin)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return render_template("users.html", error="用户名已存在", users=get_all_users(), active_page="users")
    finally:
        conn.close()
    return redirect(url_for("user_list"))


@app.route("/admin/users/<int:user_id>/reset", methods=["POST"])
@admin_required
def user_reset(user_id: int):
    new_password = request.form.get("new_password", "").strip()
    if not new_password:
        return render_template("users.html", error="新密码不能为空", users=get_all_users(), active_page="users")

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), user_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("user_list"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if row and row[0] == session.get("username"):
        conn.close()
        return render_template("users.html", error="不能删除当前登录用户", users=get_all_users(), active_page="users")
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("user_list"))


def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, username, is_admin FROM users").fetchall()
    conn.close()
    return rows


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/calculate", methods=["POST"])
@login_required
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
            "dc_stray": _get_float(request.form, "dc_stray"),   # 注意：后面要 /100
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
        matrix, matrix_latex, score, a_vec, _  = calc.calculate()
        a_text = f"结果向量A = [ {', '.join(f'{x:.4f}' for x in a_vec)} ]"
        return jsonify({
            "success": True,
            "score": round(float(score), 2),
            "matrix": matrix.tolist(),  # 5×4 嵌套数组
            "a_text": a_text,  # 1×4 数组
            "matrix_latex": matrix_latex  # LaTeX 格式的矩阵
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"计算异常: {str(e)}"}), 500

if __name__ == "__main__":
    init_db()  # 初始化数据库
    # print(f"DB_PATH: {os.path.abspath(DB_PATH)}")
    app.run(debug=True, port=5000)