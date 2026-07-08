import secrets
import sqlite3
import os
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev-key-2025"

# 用户数据库 - 密码使用哈希存储
USERS = {
    "admin": {
        "username": "admin",
        "password": generate_password_hash("admin123"),
        "role": "admin",
        "email": "admin@example.com",
        "phone": "13800138000",
        "balance": 99999
    },
    "alice": {
        "username": "alice",
        "password": generate_password_hash("alice2025"),
        "role": "user",
        "email": "alice@example.com",
        "phone": "13900139001",
        "balance": 100
    }
}


def init_db():
    """初始化 SQLite 数据库，创建表并插入默认用户"""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/users.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT,
        phone TEXT
    )""")
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)",
              ("admin", "admin123", "admin@example.com", "13800138000"))
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)",
              ("alice", "alice2025", "alice@example.com", "13900139001"))
    conn.commit()
    conn.close()


@app.route("/")
def index():
    username = session.get("username")
    user_info = None
    if username and username in USERS:
        # 取用户信息时排除密码字段，防止泄露
        user_info = {k: v for k, v in USERS[username].items() if k != "password"}
    return render_template("index.html", user=user_info)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        # CSRF 校验
        csrf_token = request.form.get("csrf_token", "")
        if csrf_token != session.get("csrf_token"):
            error = "表单已过期，请重新提交"
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            user = USERS.get(username)
            if user and check_password_hash(user["password"], password):
                session["username"] = username
                # 登录成功后排除密码字段
                user_info = {k: v for k, v in user.items() if k != "password"}
                return render_template("index.html", user=user_info)
            else:
                error = "用户名或密码错误"

    # 生成新的 CSRF token
    session["csrf_token"] = secrets.token_hex(32)
    return render_template("login.html", error=error, csrf_token=session["csrf_token"])


@app.route("/register", methods=["GET", "POST"])
def register():
    message = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        conn = sqlite3.connect("data/users.db")
        c = conn.cursor()
        # 使用参数化查询防止 SQL 注入
        sql = "INSERT INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)"
        params = (username, password, email, phone)
        print(f"[SQL] {sql} | params={params}")
        try:
            c.execute(sql, params)
            conn.commit()
            message = "注册成功，请登录"
        except Exception as e:
            message = f"注册失败：{e}"
        conn.close()
        return render_template("register.html", message=message)

    return render_template("register.html", message=message)


@app.route("/search")
def search():
    keyword = request.args.get("keyword", "")
    results = []

    # 获取当前登录用户信息
    username = session.get("username")
    user_info = None
    if username and username in USERS:
        user_info = {k: v for k, v in USERS[username].items() if k != "password"}

    if keyword:
        conn = sqlite3.connect("data/users.db")
        c = conn.cursor()
        # 使用参数化查询防止 SQL 注入
        sql = "SELECT id, username, email, phone FROM users WHERE username LIKE ? OR email LIKE ?"
        like_pattern = f"%{keyword}%"
        print(f"[SQL] {sql} | keyword=%{keyword}%")
        c.execute(sql, (like_pattern, like_pattern))
        rows = c.fetchall()
        for row in rows:
            results.append({"id": row[0], "username": row[1], "email": row[2], "phone": row[3]})
        conn.close()

    return render_template("index.html", user=user_info, results=results, keyword=keyword)


@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("csrf_token", None)
    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="0.0.0.0", port=5000)
