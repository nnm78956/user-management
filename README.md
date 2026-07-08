# 用户信息管理平台

一个基于 **Python Flask** 构建的简易用户信息管理平台，提供用户登录认证、信息展示等功能。该项目专注于**安全性最佳实践**，适合作为 Flask 入门学习和安全编码参考。

---

## 功能特性

- ✅ **用户登录认证** — 基于 Session 的登录态管理
- ✅ **用户注册** — 新用户可自行注册账号
- ✅ **用户搜索** — 登录后可按用户名或邮箱模糊搜索用户
- ✅ **用户信息展示** — 登录后可查看个人完整信息
- ✅ **安全登出** — 清除 Session 安全退出
- ✅ **密码哈希存储** — 使用 Werkzeug 安全哈希，不存明文密码
- ✅ **CSRF 防护** — 登录表单携带一次性 Token，防止跨站请求伪造
- ✅ **SQL 注入防护** — 所有数据库查询使用参数化查询（? 占位符）
- ✅ **SQLite 数据库** — 注册和搜索数据持久化存储
- ✅ **响应式界面** — 简洁现代的 UI 设计，适配多种屏幕

---

## 快速开始

### 环境要求

- Python 3.8+
- pip（Python 包管理器）

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/nnm78956/user-management.git
cd user-management

# 2. 安装依赖
pip install flask

# 3. 启动服务
python app.py
```

### 访问应用

打开浏览器访问：**http://localhost:5000**

---

## 默认测试账号

| 用户名 | 密码 | 角色 | 邮箱 | 余额 |
|--------|------|------|------|------|
| `admin` | `admin123` | admin | admin@example.com | 99,999 |
| `alice` | `alice2025` | user | alice@example.com | 100 |

---

## 项目结构

```
user-management/
│
├── app.py                      # Flask 主应用（路由、认证、注册、搜索）
├── data/                       # SQLite 数据库文件目录（自动创建）
├── templates/                  # HTML 模板文件夹
│   ├── base.html               # 基础模板（导航栏、布局）
│   ├── index.html              # 首页（用户信息展示 + 搜索）
│   ├── login.html              # 登录页面
│   └── register.html           # 注册页面
├── static/
│   └── css/
│       └── style.css           # 全局样式文件
└── README.md                   # 本文件
```

---

## 技术栈

| 技术 | 用途 |
|------|------|
| **Python 3** | 后端编程语言 |
| **Flask 3.x** | Web 框架 |
| **Jinja2** | 模板引擎（HTML 渲染） |
| **Werkzeug** | 密码哈希（`generate_password_hash` / `check_password_hash`） |
| **SQLite 3** | 数据库（注册、搜索数据持久化） |
| **secrets** | CSRF Token 生成 |

---

## 安全设计

本项目在开发过程中注重安全性，实施了以下防护措施：

### 1. 密码安全

- **哈希存储**：密码使用 `werkzeug.security.generate_password_hash()` 进行 PBKDF2 哈希，数据库/字典中不保存明文密码
- **安全比对**：登录验证使用 `check_password_hash()`，防止时序攻击

### 2. CSRF 防护

- 登录表单生成一次性 `csrf_token`（32 字节随机十六进制字符串）
- Token 存储在服务端 Session 中
- 每次 POST 请求校验 Token 一致性，防止跨站请求伪造

### 3. 敏感信息保护

- 用户密码**不在前端页面展示**
- 非敏感信息（用户名、邮箱、手机号、角色、余额）正常展示

### 4. 调试安全

- 生产环境关闭 `debug` 模式，防止调试器远程代码执行

### 5. XSS 防护

- Jinja2 模板引擎默认开启自动转义，所有 `{{ }}` 变量中的 HTML 特殊字符会被转义，防止跨站脚本攻击

### 6. SQL 注入防护

- 所有数据库查询使用**参数化查询**（`?` 占位符）
- 用户输入作为数据传入，不会被解析为 SQL 代码
- 注册和搜索功能均经过安全加固

---

## API 接口一览

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页，已登录显示用户信息，未登录提示登录 |
| `/login` | GET | 显示登录表单 |
| `/login` | POST | 提交用户名和密码进行登录 |
| `/register` | GET | 显示注册表单 |
| `/register` | POST | 提交用户名、密码、邮箱、手机号进行注册 |
| `/search` | GET | 按用户名或邮箱模糊搜索用户（需登录） |
| `/logout` | GET | 清除 Session 并重定向到首页 |

---

## 自定义扩展

### 添加新用户

**方式一**：在 `app.py` 的 `USERS` 字典中添加新条目（登录可用）：

```python
USERS = {
    # ... 已有用户 ...
    "bob": {
        "username": "bob",
        "password": generate_password_hash("bob2025"),
        "role": "user",
        "email": "bob@example.com",
        "phone": "13700137001",
        "balance": 500
    }
}
```

**方式二**：通过网页 `/register` 注册（写入 SQLite 数据库）

### 修改监听端口

```python
app.run(debug=False, host="0.0.0.0", port=8080)  # 改为 8080 端口
```

---

## 开发参考

- [Flask 官方文档](https://flask.palletsprojects.com/)
- [Werkzeug 密码哈希](https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security)
- [Jinja2 模板文档](https://jinja.palletsprojects.com/)

---

## 许可证

本项目仅供学习参考使用。
