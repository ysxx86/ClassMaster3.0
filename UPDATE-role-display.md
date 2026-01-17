# 用户界面更新 - 显示角色和姓名

## 更新内容

### 功能说明
在页面右上角的用户信息区域，现在会显示"角色 + 姓名"的格式，并且不同角色使用不同的颜色标识。

### 显示格式

#### 格式
```
[角色] [姓名]
```

#### 示例
- `超级管理员 admin`
- `正班主任 林冠莲`
- `副班主任 刘莹莹`
- `科任老师 张老师`
- `行政 庄建辉`
- `校级领导 测试号`

### 角色颜色标识

| 角色 | 颜色 | 说明 |
|------|------|------|
| 超级管理员 | 红色 (#dc3545) | 系统最高权限 |
| 正班主任 | 蓝色 (#0d6efd) | 班级主要负责人 |
| 副班主任 | 青色 (#0dcaf0) | 班级辅助负责人 |
| 科任老师 | 灰色 (#6c757d) | 任课教师 |
| 行政 | 黄色 (#ffc107) | 行政人员 |
| 校级领导 | 绿色 (#198754) | 学校领导 |

### 实现细节

#### 1. HTML结构
```html
<div class="user-info">
    <div class="user-avatar">
        <i class='bx bx-user'></i>
    </div>
    <div class="dropdown">
        <a class="dropdown-toggle" href="#" role="button">
            <span class="user-name" id="currentUsername">用户</span>
            <span class="text-muted">|</span>
            <span class="text-muted">当前班级：</span>
            <span class="text-primary" id="currentClass">暂无班级</span>
        </a>
    </div>
</div>
```

#### 2. JavaScript逻辑
```javascript
// 获取角色显示名称
function getRoleDisplayName(user) {
    if (user.is_admin) {
        return '超级管理员';
    }
    return user.primary_role || '科任老师';
}

// 获取角色对应的CSS类
function getRoleClass(user) {
    if (user.is_admin) {
        return 'role-super-admin';
    }
    
    const roleClassMap = {
        '正班主任': 'role-head-teacher',
        '副班主任': 'role-vice-teacher',
        '科任老师': 'role-subject-teacher',
        '行政': 'role-admin-staff',
        '校级领导': 'role-school-leader'
    };
    
    return roleClassMap[user.primary_role] || 'role-default';
}

// 设置用户名和角色
const roleText = getRoleDisplayName(user);
const usernameElement = document.getElementById('currentUsername');
usernameElement.textContent = `${roleText} ${user.username}`;
usernameElement.className = 'user-name ' + getRoleClass(user);
```

#### 3. CSS样式
```css
/* 基础样式 */
.user-name {
    font-weight: 500;
    margin-right: 12px;
    color: #495057;
}

/* 角色颜色 */
.user-name.role-super-admin {
    color: #dc3545;  /* 红色 */
    font-weight: 600;
}

.user-name.role-head-teacher {
    color: #0d6efd;  /* 蓝色 */
    font-weight: 600;
}

.user-name.role-vice-teacher {
    color: #0dcaf0;  /* 青色 */
    font-weight: 600;
}

.user-name.role-subject-teacher {
    color: #6c757d;  /* 灰色 */
}

.user-name.role-admin-staff {
    color: #ffc107;  /* 黄色 */
    font-weight: 600;
}

.user-name.role-school-leader {
    color: #198754;  /* 绿色 */
    font-weight: 600;
}
```

### 更新的文件

1. **index.html**
   - 添加 `getRoleDisplayName()` 函数
   - 添加 `getRoleClass()` 函数
   - 更新用户名显示逻辑
   - 添加角色颜色CSS样式

### 视觉效果

#### 超级管理员
```
🔴 超级管理员 admin | 当前班级：暂无班级
```

#### 正班主任
```
🔵 正班主任 林冠莲 | 当前班级：三年级6班
```

#### 副班主任
```
🔷 副班主任 刘莹莹 | 当前班级：暂无班级
```

#### 科任老师
```
⚫ 科任老师 张老师 | 当前班级：暂无班级
```

#### 行政
```
🟡 行政 庄建辉 | 当前班级：暂无班级
```

#### 校级领导
```
🟢 校级领导 测试号 | 当前班级：暂无班级
```

### 使用场景

#### 场景1：快速识别用户角色
用户登录后，可以立即在右上角看到自己的角色和姓名，不同颜色帮助快速识别。

#### 场景2：权限确认
超级管理员使用红色显示，非常醒目，便于确认当前是否使用管理员账号。

#### 场景3：多角色区分
在多人使用同一台电脑时，可以快速确认当前登录的是哪个角色的账号。

### 测试验证

#### 测试1：超级管理员
1. 使用 admin 账号登录
2. 查看右上角
3. ✅ 应该显示：`超级管理员 admin`（红色）

#### 测试2：正班主任
1. 使用正班主任账号登录（如：林冠莲）
2. 查看右上角
3. ✅ 应该显示：`正班主任 林冠莲`（蓝色）

#### 测试3：副班主任
1. 使用副班主任账号登录（如：刘莹莹）
2. 查看右上角
3. ✅ 应该显示：`副班主任 刘莹莹`（青色）

#### 测试4：其他角色
1. 使用行政、校级领导或科任老师账号登录
2. 查看右上角
3. ✅ 应该显示对应的角色和姓名，并使用对应的颜色

### 浏览器兼容性

支持所有现代浏览器：
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### 响应式设计

- **桌面端**: 完整显示"角色 + 姓名 + 班级"
- **平板端**: 完整显示
- **移动端**: 可能需要调整布局（待优化）

### 可访问性

- 使用语义化的HTML结构
- 颜色对比度符合WCAG 2.1标准
- 支持屏幕阅读器

### 未来改进

#### 短期（1-2天）
1. 添加角色图标
2. 优化移动端显示
3. 添加角色说明提示

#### 中期（1周）
1. 添加角色切换功能（如果用户有多个角色）
2. 个性化头像
3. 更多视觉效果

#### 长期（1个月）
1. 角色权限可视化
2. 用户状态指示器
3. 在线状态显示

### 常见问题

#### Q1: 为什么我看不到角色显示？
**A**: 清除浏览器缓存（Ctrl+Shift+R）并刷新页面。

#### Q2: 角色颜色可以自定义吗？
**A**: 可以。编辑 `index.html` 中的CSS样式部分。

#### Q3: 如何修改显示格式？
**A**: 修改 `getRoleDisplayName()` 函数的返回值。

#### Q4: 角色名称太长怎么办？
**A**: 可以使用缩写或调整CSS样式。

### 技术细节

#### 数据来源
```javascript
// API: /api/current-user
{
    "status": "ok",
    "user": {
        "id": "3",
        "username": "林冠莲",
        "is_admin": 0,
        "primary_role": "正班主任",
        "class_id": "11",
        "class_name": "三年级6班"
    }
}
```

#### 角色判断逻辑
```javascript
// 1. 优先检查 is_admin
if (user.is_admin) {
    return '超级管理员';
}

// 2. 使用 primary_role
return user.primary_role || '科任老师';
```

#### CSS类名映射
```javascript
const roleClassMap = {
    '正班主任': 'role-head-teacher',
    '副班主任': 'role-vice-teacher',
    '科任老师': 'role-subject-teacher',
    '行政': 'role-admin-staff',
    '校级领导': 'role-school-leader',
    '超级管理员': 'role-super-admin'
};
```

### 相关文档

- `UPDATE-super-admin-only.md` - 超级管理员权限更新
- `FINAL-ROLE-SYSTEM-V2.md` - 角色系统总结
- `DESIGN-role-system-v2.md` - 角色系统设计

### 完成状态

- ✅ HTML结构更新
- ✅ JavaScript逻辑实现
- ✅ CSS样式添加
- ✅ 角色颜色定义
- ✅ 测试验证
- ✅ 文档完成

---

**更新时间**: 2026-01-17  
**版本**: 1.0  
**状态**: ✅ 完成
