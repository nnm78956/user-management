import secrets
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


@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("csrf_token", None)
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
