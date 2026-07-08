# 安全漏洞审计报告

**项目名称**：用户信息管理平台（Flask）  
**审计日期**：2026年7月7日  
**审计版本对比**：  
- **原版（v1）**：`4ac6889` — https://github.com/nnm78956/user-management-original  
- **修复版（v2）**：`638ff95` — https://github.com/nnm78956/user-management  
**审计类型**：源码安全审计  

---

## 审计概述

本次审计针对一个基于 Python Flask 框架开发的简易用户信息管理平台进行安全评估。该平台提供用户登录认证和个人信息展示功能。审计共发现 **5 项安全漏洞**，按严重程度分级如下：

| 严重程度 | 数量 |
|----------|------|
| 🔴 高危 | 2 |
| 🟠 中危 | 2 |
| 🟡 低危 | 1 |

---

## 漏洞详情

---

### 漏洞一：密码明文存储 🔴 高危

**漏洞编号**：SEC-2026-001  
**发现文件**：`app.py` — `USERS` 字典  
**CVSS 评分**：7.5（高危）  

#### 漏洞描述

用户密码以 **明文形式** 存储在 `USERS` 字典中，未做任何哈希处理。任何人获得源代码或数据库访问权限即可直接获取所有用户的明文密码。

#### 原版代码（存在漏洞）

```python
USERS = {
    "admin": {
        "password": "admin123",  # ← 明文密码
    },
    "alice": {
        "password": "alice2025",  # ← 明文密码
    }
}

# 登录比对也使用明文直接比较
if USERS[username]["password"] == password:  # ← 明文 == 对比
```

#### 风险分析

- 源码泄露 → 所有密码直接暴露
- 用户常跨平台复用密码 → 可被撞库攻击
- 违反《网络安全法》及等保 2.0 密码存储要求

#### 修复方案

使用 `werkzeug.security` 对密码进行 PBKDF2 哈希存储，登录时使用 `check_password_hash()` 进行安全比对。

#### 修复后代码

```python
from werkzeug.security import generate_password_hash, check_password_hash

USERS = {
    "admin": {
        "password": generate_password_hash("admin123"),  # ← 哈希存储
    },
    "alice": {
        "password": generate_password_hash("alice2025"),  # ← 哈希存储
    }
}

# 登录使用安全比对
if user and check_password_hash(user["password"], password):  # ← 哈希比对
```

---

### 漏洞二：密码明文展示 🔴 高危

**漏洞编号**：SEC-2026-002  
**发现文件**：`app.py` + `templates/index.html`  
**CVSS 评分**：6.5（中危）  

#### 漏洞描述

用户登录成功后，密码被完整传递给前端模板，并直接渲染在 HTML 页面上。这导致密码可被任何能接触到用户屏幕的人看到，且浏览器缓存/历史记录中可能留存敏感信息。

#### 原版代码（存在漏洞）

```python
# app.py - 将包含密码的完整用户信息传给模板
user_info = USERS[username]  # ← password 字段未过滤
return render_template("index.html", user=user_info)
```

```html
<!-- index.html - 直接展示密码 -->
<ul class="info-list">
    <li><span class="info-label">用户名：</span>{{ user.username }}</li>
    <li><span class="info-label">密码：</span>{{ user.password }}</li>  <!-- ← 明文密码展示 -->
</ul>
```

#### 风险分析

- 肩窥攻击：他人从屏幕直接看到密码
- 浏览器快照/缓存可能留存含密码的页面
- 截屏分享时无意泄露凭证

#### 修复方案

在传递给模板时排除 `password` 字段，模板中删除密码展示行。

#### 修复后代码

```python
# app.py - 过滤密码字段
user_info = {k: v for k, v in user.items() if k != "password"}
```

```html
<!-- index.html - 移除密码展示 -->
<ul class="info-list">
    <li><span class="info-label">用户名：</span>{{ user.username }}</li>
    <li><span class="info-label">邮箱：</span>{{ user.email }}</li>
    <!-- password 行已移除 -->
</ul>
```

---

### 漏洞三：CSRF 防护缺失 🟠 中危

**漏洞编号**：SEC-2026-003  
**发现文件**：`app.py` + `templates/login.html`  
**CVSS 评分**：5.3（中危）  

#### 漏洞描述

登录表单未包含 CSRF Token，也未对 POST 请求来源进行校验。攻击者可构造恶意页面，诱导已登录用户（或利用用户浏览器自动填充）提交伪造的登录请求。

#### 原版代码（存在漏洞）

```python
# app.py - GET 登录页不生成 CSRF Token
# POST 登录时不校验任何来源标识
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # ... 直接处理登录请求，无 CSRF 校验
```

```html
<!-- login.html - 表单没有隐藏的 CSRF 字段 -->
<form method="POST" action="/login" class="login-form">
    <input type="text" name="username">
    <input type="password" name="password">
    <button>登录</button>
</form>
```

#### 风险分析

- 攻击者可构造跨站请求伪造用户登录
- 结合会话固定攻击可能导致账号接管
- 违背 OWASP Top 10 A1 安全要求

#### 修复方案

- GET 请求时生成 `secrets.token_hex(32)` 存入 Session
- 表单添加隐藏 `csrf_token` 字段
- POST 请求时校验 Token 一致性

#### 修复后代码

```python
import secrets

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        csrf_token = request.form.get("csrf_token", "")
        if csrf_token != session.get("csrf_token"):
            error = "表单已过期，请重新提交"
            return render_template("login.html", error=error, ...)
        # ... 继续处理登录
    # GET 请求时生成新 Token
    session["csrf_token"] = secrets.token_hex(32)
    return render_template("login.html", csrf_token=session["csrf_token"])
```

```html
<!-- login.html - 表单添加 CSRF 隐藏字段 -->
<form method="POST" action="/login" class="login-form">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <input type="text" name="username">
    <input type="password" name="password">
    <button>登录</button>
</form>
```

---

### 漏洞四：敏感信息硬编码泄露 🟠 中危

**漏洞编号**：SEC-2026-004  
**发现文件**：`templates/login.html`  
**CVSS 评分**：4.0（中危）  

#### 漏洞描述

登录页面 HTML 源码的注释中直接写入了默认管理员账号和密码，任何查看页面源码的人都可以获取管理员凭证。

#### 原版代码（存在漏洞）

```html
<!-- 调试信息 - 默认管理员账号 用户名: admin 密码: admin123 -->
<!DOCTYPE html>
<html>
```

#### 风险分析

- 查看网页源码即可获取管理员密码
- 浏览器开发者工具或 `curl` 直接可见
- 搜索引擎可能索引到该敏感信息

#### 修复方案

删除包含账号密码的 HTML 注释，默认凭证仅在非代码文档中提及。

#### 修复后代码

```html
<!-- 注释已移除 -->
{% extends "base.html" %}
```

---

### 漏洞五：生产环境开启 Debug 模式 🟡 低危

**漏洞编号**：SEC-2026-005  
**发现文件**：`app.py`  
**CVSS 评分**：3.5（低危）  

#### 漏洞描述

Flask 以 `debug=True` 模式运行，开启了 Werkzeug 调试器。该调试器在发生异常时会显示完整的堆栈跟踪，并在允许远程访问时可能被用于执行任意 Python 代码。

#### 原版代码（存在漏洞）

```python
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
    #       ^^^^^^^^^^ 生产环境不应开启
```

#### 风险分析

- 调试器控制台可执行任意 Python 代码
- 堆栈跟踪泄露应用内部路径和变量
- 应用异常时向用户暴露技术细节

#### 修复方案

将 `debug` 设置为 `False`，或通过环境变量控制。

#### 修复后代码

```python
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
```

---

## 漏洞对比汇总

| 漏洞 | 原版 | 修复版 | 严重程度 | CVSS |
|------|------|--------|----------|------|
| 密码明文存储 | ❌ `"admin123"` 明文 | ✅ PBKDF2 哈希 | 🔴 高危 | 7.5 |
| 密码明文展示 | ❌ 页面直接显示密码 | ✅ 已排除 password 字段 | 🔴 高危 | 6.5 |
| CSRF 防护缺失 | ❌ 无 Token 校验 | ✅ 32 字节随机 Token | 🟠 中危 | 5.3 |
| 敏感信息硬编码 | ❌ HTML 注释泄露密码 | ✅ 已删除泄露注释 | 🟠 中危 | 4.0 |
| Debug 模式 | ❌ `debug=True` | ✅ `debug=False` | 🟡 低危 | 3.5 |

---

## 已确认安全的设计

以下安全防护在代码审计中确认为**有效**，无需修复：

| 防护项 | 状态 | 说明 |
|--------|------|------|
| ✅ XSS 防护 | 有效 | Jinja2 模板引擎默认开启 auto-escaping，所有 `{{ }}` 变量中的 HTML 特殊字符自动转义 |
| ✅ Session 管理 | 有效 | 使用 Flask 签名 Session，`secret_key` 已配置 |
| ✅ 登出机制 | 有效 | 清除 `username` 和 `csrf_token` 两个 Session 键，防止会话残留 |
| ✅ 输入转义 | 有效 | 模板渲染时用户名等内容被正确转义，无法注入 HTML/JavaScript |

---

## 修复建议总结

### 紧急修复（高危）
1. 对 `USERS` 字典中的密码使用 `generate_password_hash()` 进行哈希存储
2. 登录比对改用 `check_password_hash()` 安全函数
3. 用户信息传递到模板前过滤 `password` 字段
4. 模板中删除密码展示行

### 建议修复（中危）
5. 引入 `secrets.token_hex()` 生成 CSRF Token
6. 表单添加隐藏字段 `{{ csrf_token }}`
7. POST 路由校验 Token 一致性
8. 删除 HTML 源码中的管理员凭证注释

### 最佳实践（低危）
9. 关闭 `debug` 模式或通过 `FLASK_ENV` 环境变量控制

---

## 参考标准

- **OWASP Top 10 (2021)**：A01（失效的访问控制）、A04（不安全的设计）、A05（安全配置错误）
- **OWASP ASVS**：V2.1（密码安全）、V3.1（会话管理）、V12.1（CSRF 防护）
- **等保 2.0**：三级安全要求 — 身份鉴别、访问控制、安全审计
- **CWE**：CWE-256（明文密码存储）、CWE-200（信息泄露）、CWE-352（CSRF）、CWE-489（Debug 后门）

---

## 审计结论

原版项目存在 **5 项安全漏洞**，其中高危 2 项、中危 2 项、低危 1 项。修复版已针对全部 5 项漏洞完成修复，代码达到基本安全水平。

> **报告生成工具**：Claude Code（Anthropic）  
> **审计方法**：静态源代码审计  
> **仓库地址**：  
> - 原版（未修复）：https://github.com/nnm78956/user-management-original  
> - 修复版：https://github.com/nnm78956/user-management  
