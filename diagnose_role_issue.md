# 角色更新问题诊断指南

## 问题描述
编辑用户时选择角色，但保存后数据库没有更新，仍然显示"科任老师"。

## 可能的原因

### 1. 浏览器缓存问题 ⭐ 最可能
浏览器可能缓存了旧版本的JavaScript或HTML文件。

**解决方法：**
1. 按 `Ctrl + Shift + R` (Windows/Linux) 或 `Cmd + Shift + R` (Mac) 强制刷新页面
2. 或者清空浏览器缓存：
   - Chrome: 设置 → 隐私和安全 → 清除浏览数据 → 选择"缓存的图片和文件"
   - Firefox: 设置 → 隐私与安全 → Cookie和网站数据 → 清除数据
3. 或者使用无痕/隐私模式打开

### 2. JavaScript文件未更新
检查admin.js文件是否包含最新代码。

**检查方法：**
```bash
# 查看文件修改时间
ls -lh js/admin.js

# 搜索role相关代码
grep -n "editUserRole" js/admin.js
```

**期望输出：**
应该能找到 `document.getElementById('editUserRole')` 这行代码。

### 3. HTML文件未更新
检查admin.html是否包含角色选择框。

**检查方法：**
```bash
# 搜索角色选择框
grep -n "editUserRole" pages/admin.html
```

**期望输出：**
应该能找到 `<select class="form-select" id="editUserRole"` 这行代码。

### 4. 后端API未更新
检查users.py是否处理role字段。

**检查方法：**
```bash
# 搜索角色更新代码
grep -n "角色更新" users.py
```

**期望输出：**
应该能找到角色更新的代码。

## 诊断步骤

### 步骤1: 检查文件是否最新
```bash
# 运行诊断脚本
python3 << 'EOF'
import os
import subprocess

print("=" * 60)
print("角色更新功能诊断")
print("=" * 60)

# 检查文件
files = {
    'js/admin.js': 'editUserRole',
    'pages/admin.html': 'editUserRole',
    'users.py': '角色更新'
}

for file, keyword in files.items():
    if os.path.exists(file):
        result = subprocess.run(['grep', '-c', keyword, file], 
                              capture_output=True, text=True)
        count = result.stdout.strip()
        if int(count) > 0:
            print(f"✓ {file}: 找到 {count} 处 '{keyword}'")
        else:
            print(f"✗ {file}: 未找到 '{keyword}'")
    else:
        print(f"✗ {file}: 文件不存在")

print("=" * 60)
EOF
```

### 步骤2: 检查数据库
```bash
# 查看users表结构
sqlite3 students.db "PRAGMA table_info(users)" | grep role

# 查看现有用户的角色
sqlite3 students.db "SELECT id, username, role FROM users LIMIT 5"
```

### 步骤3: 测试API
```bash
# 运行测试脚本
python3 test_update_role.py
```

### 步骤4: 查看服务器日志
```bash
# 查看最新的日志
tail -50 logs/server.log | grep -i role
```

## 快速修复方案

### 方案1: 强制刷新浏览器
1. 完全关闭浏览器
2. 重新打开浏览器
3. 按 `Ctrl + Shift + R` 强制刷新
4. 打开浏览器开发者工具 (F12)
5. 切换到 Network 标签
6. 勾选 "Disable cache"
7. 刷新页面

### 方案2: 重启服务器
```bash
# 停止服务器 (Ctrl + C)
# 然后重新启动
python3 server.py
```

### 方案3: 清除浏览器缓存
1. 打开浏览器设置
2. 找到"清除浏览数据"
3. 选择"缓存的图片和文件"
4. 点击"清除数据"
5. 刷新页面

## 验证修复

### 1. 打开浏览器开发者工具
按 F12 打开开发者工具

### 2. 查看Console标签
应该能看到类似这样的日志：
```
准备更新用户，角色值: 副班主任
发送的用户数据: {username: "张老师", class_id: "5", role: "副班主任", is_admin: false}
```

### 3. 查看Network标签
找到 PUT /api/users/5 的请求，查看：
- Request Payload 应该包含 `"role": "副班主任"`
- Response 应该返回 `{"status": "ok", "message": "用户信息已成功更新"}`

### 4. 验证数据库
```bash
sqlite3 students.db "SELECT id, username, role FROM users WHERE id = 5"
```

应该看到角色已更新。

## 如果问题仍然存在

### 检查清单
- [ ] 已强制刷新浏览器 (Ctrl + Shift + R)
- [ ] 已清除浏览器缓存
- [ ] 已重启服务器
- [ ] 已检查文件包含最新代码
- [ ] 已查看浏览器Console没有JavaScript错误
- [ ] 已查看Network请求包含role字段
- [ ] 已查看服务器日志

### 手动测试
访问测试页面：
```
http://localhost:5000/test_role_update.html
```

这个页面可以直接测试API，不依赖admin.js。

### 联系支持
如果以上方法都无效，请提供：
1. 浏览器Console的截图
2. Network标签中PUT请求的截图
3. 服务器日志的最后50行
4. 数据库查询结果

---

**最后更新**: 2026-01-17  
**版本**: 1.0
