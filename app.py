import secrets
import sqlite3
import os
import urllib.request
import urllib.error
import ipaddress
import socket
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev-key-2025"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# 允许上传的图片后缀名
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


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
    # 添加 balance 列（兼容已存在的表）
    try:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    except:
        pass
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone, balance) VALUES (?, ?, ?, ?, ?)",
              ("admin", "admin123", "admin@example.com", "13800138000", 99999))
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone, balance) VALUES (?, ?, ?, ?, ?)",
              ("alice", "alice2025", "alice@example.com", "13900139001", 100))
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


@app.route("/upload", methods=["GET", "POST"])
def upload():
    # 需要登录才能访问
    username = session.get("username")
    if not username:
        return redirect("/login")

    if request.method == "POST":
        # 接收用户上传的文件
        if "file" not in request.files:
            return render_template("upload.html", error="未选择文件")

        file = request.files["file"]
        if file.filename == "":
            return render_template("upload.html", error="未选择文件")

        # 检查文件后缀名，只允许图片格式
        _, ext = os.path.splitext(file.filename)
        ext = ext.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return render_template("upload.html", error="不支持的文件类型，仅允许上传图片文件（jpg、jpeg、png、gif、webp、bmp）")

        # 确保上传目录存在
        upload_dir = os.path.join("static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        # 使用用户上传的原始文件名保存
        save_path = os.path.join(upload_dir, file.filename)
        file.save(save_path)

        file_url = f"/static/uploads/{file.filename}"
        return render_template("upload.html", upload_success=True, file_url=file_url)

    return render_template("upload.html")


@app.route("/profile")
def profile():
    # 需要登录才能访问
    username = session.get("username")
    if not username:
        return redirect("/login")

    # 生成 CSRF token
    session["csrf_token"] = secrets.token_hex(32)

    # 从 session 获取当前登录用户，不从 URL 参数获取 user_id，防止越权查看
    conn = sqlite3.connect("data/users.db")
    c = conn.cursor()
    c.execute("SELECT id, username, email, phone, balance FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if row:
        profile_user = {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "phone": row[3],
            "balance": row[4] if row[4] is not None else 0
        }
    else:
        profile_user = None

    return render_template("profile.html", profile_user=profile_user, csrf_token=session["csrf_token"])


@app.route("/recharge", methods=["POST"])
def recharge():
    # 需要登录才能访问
    username = session.get("username")
    if not username:
        return redirect("/login")

    amount = request.form.get("amount", "").strip()

    # 禁止负数充值
    try:
        amount_val = float(amount)
    except ValueError:
        return redirect("/profile")

    if amount_val <= 0:
        return redirect("/profile")

    # 只能给当前登录用户充值
    conn = sqlite3.connect("data/users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE username = ?", (amount, username))
    conn.commit()
    conn.close()

    return redirect("/profile")


@app.route("/change-password", methods=["POST"])
def change_password():
    # 需要登录才能访问
    login_user = session.get("username")
    if not login_user:
        return redirect("/login")

    # 修复1: CSRF 校验
    csrf_token = request.form.get("csrf_token", "")
    if csrf_token != session.get("csrf_token"):
        return redirect("/profile")

    # 修复2: 验证原密码
    old_password = request.form.get("old_password", "")
    conn = sqlite3.connect("data/users.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (login_user,))
    row = c.fetchone()
    if not row or row[0] != old_password:
        conn.close()
        return redirect("/profile")

    # 修复3: 只修改当前登录用户自己的密码
    new_password = request.form.get("new_password", "")

    c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, login_user))
    conn.commit()
    conn.close()

    return redirect("/profile")


@app.route("/fetch-url", methods=["POST"])
def fetch_url():
    # 需要登录才能访问
    username = session.get("username")
    if not username:
        return redirect("/login")

    url = request.form.get("url", "").strip()

    # 获取当前登录用户信息
    user_info = None
    if username and username in USERS:
        user_info = {k: v for k, v in USERS[username].items() if k != "password"}

    fetch_result = None
    fetch_error = None

    if url:
        try:
            # SSRF 修复：检查 URL 是否安全
            parsed = urlparse(url)

            # 1. 禁止 file:// 协议
            if parsed.scheme == "file":
                raise ValueError("不允许使用 file:// 协议")

            # 2. 对于 HTTP/HTTPS，检查目标 IP 是否为内网地址
            if parsed.scheme in ("http", "https"):
                hostname = parsed.hostname
                if hostname:
                    ip = socket.gethostbyname(hostname)
                    ip_obj = ipaddress.ip_address(ip)
                    if ip_obj.is_private or ip_obj.is_loopback:
                        raise ValueError("不允许访问内网地址: " + ip)

            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=10)
            status_code = response.getcode()
            content = response.read().decode("utf-8", errors="replace")[:5000]
            fetch_result = {
                "status_code": status_code,
                "content": content
            }
        except Exception as e:
            fetch_error = str(e)

    return render_template("index.html", user=user_info, fetch_result=fetch_result, fetch_error=fetch_error, fetch_url=url)


@app.route("/page")
def page():
    name = request.args.get("name", "")

    # 修复文件包含漏洞：移除路径穿越字符
    name = name.replace("../", "").replace("..\\", "")

    username = session.get("username")
    user_info = None
    if username and username in USERS:
        user_info = {k: v for k, v in USERS[username].items() if k != "password"}

    content = None

    file_path = os.path.join("pages", name)

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        html_path = os.path.join("pages", name + ".html")
        if os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = "page not found"

    return render_template("index.html", user=user_info, page_content=content)


@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("csrf_token", None)
    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="0.0.0.0", port=5000)
