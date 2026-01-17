# 角色系统重新设计 V2.0

## 需求分析

### 角色定义

#### 1. 超级管理员
- **原名称**: 管理员
- **新名称**: 超级管理员
- **权限**: 系统最高权限
- **特点**: 
  - 不是班主任
  - 可以兼任科任老师
  - `is_admin = 1`

#### 2. 行政
- **定义**: 学校行政人员
- **特点**:
  - 不是班主任
  - 可以兼任科任老师
  - 无班级管理权限

#### 3. 校级领导
- **定义**: 学校领导层
- **特点**:
  - 不是班主任
  - 可以兼任科任老师
  - 可能有特殊权限

#### 4. 正班主任
- **定义**: 班级主要负责人
- **特点**:
  - **只能管理唯一的班级**
  - 可以兼任科任老师（教多个班级、多个学科）
  - 参与绩效考核
  - `class_id` 字段有值且唯一

#### 5. 副班主任
- **定义**: 班级辅助负责人
- **特点**:
  - **只能管理唯一的班级**
  - 可以兼任科任老师（教多个班级、多个学科）
  - 不参与绩效考核
  - `class_id` 字段有值且唯一

#### 6. 科任老师
- **定义**: 任课教师
- **特点**:
  - 不是班主任
  - **可以教多个学科**
  - **可以教多个班级**
  - 通过 `teaching_assignments` 表管理任课信息

### 角色关系图

```
超级管理员 ─┐
行政 ────────┤
校级领导 ────┤─── 可以兼任 ──→ 科任老师（多学科、多班级）
正班主任 ────┤
副班主任 ────┘

班级约束：
- 一个班级 = 1个正班主任 + 1个副班主任（可选）
- 正副班主任只能管理1个班级
```

## 数据库设计

### 1. users 表（用户表）

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,  -- 1=超级管理员, 0=其他
    primary_role TEXT DEFAULT '科任老师',  -- 主要角色
    class_id TEXT,  -- 班级ID（仅正副班主任有值）
    reset_password TEXT,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (class_id) REFERENCES classes(id)
);

-- primary_role 可选值：
-- '超级管理员', '行政', '校级领导', '正班主任', '副班主任', '科任老师'
```

### 2. teaching_assignments 表（任课分配表）- 新增

```sql
CREATE TABLE teaching_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id TEXT NOT NULL,  -- 教师ID
    class_id TEXT NOT NULL,    -- 班级ID
    subject TEXT NOT NULL,     -- 学科名称
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    UNIQUE(teacher_id, class_id, subject)  -- 同一教师不能在同一班级重复教同一学科
);
```

### 3. classes 表（班级表）- 添加约束

```sql
-- 添加唯一约束，确保一个班级只有一个正班主任和一个副班主任
-- 通过应用层逻辑实现
```

## 业务规则

### 规则1：班级管理约束
- 正班主任：`primary_role = '正班主任'` AND `class_id` 有值
- 副班主任：`primary_role = '副班主任'` AND `class_id` 有值
- 一个班级只能有1个正班主任
- 一个班级只能有1个副班主任（可选）
- 一个教师只能是1个班级的正班主任或副班主任

### 规则2：科任老师管理
- 任何角色都可以兼任科任老师
- 科任老师可以教多个班级
- 科任老师可以教多个学科
- 通过 `teaching_assignments` 表管理

### 规则3：角色权限
- 超级管理员：`is_admin = 1`，所有权限
- 其他角色：`is_admin = 0`，根据 `primary_role` 判断权限

### 规则4：绩效考核
- 只有 `primary_role = '正班主任'` 的用户参与考核
- 排除 `is_admin = 1` 的用户

## 实现步骤

### 步骤1：数据库迁移
1. 重命名 `role` 字段为 `primary_role`
2. 将所有 `is_admin = 1` 的用户的 `primary_role` 改为 '超级管理员'
3. 创建 `teaching_assignments` 表
4. 添加数据验证约束

### 步骤2：后端API更新
1. 更新用户管理API
   - 添加班级唯一性验证
   - 添加科任老师分配API
2. 更新绩效考核API
   - 确保只查询正班主任
3. 新增任课管理API
   - 添加/删除/查询任课分配

### 步骤3：前端界面更新
1. 后台管理页面
   - 角色选择更新
   - 添加任课管理界面
2. 绩效考核页面
   - 确保只显示正班主任
3. 新增任课管理页面
   - 教师任课分配
   - 班级任课查询

### 步骤4：数据验证
1. 班级正副班主任唯一性检查
2. 教师班级管理唯一性检查
3. 任课分配合理性检查

## API设计

### 1. 用户管理API

#### 获取用户列表
```
GET /api/users
返回：包含 primary_role 和任课信息
```

#### 更新用户
```
PUT /api/users/<user_id>
请求体：{
  "username": "张老师",
  "primary_role": "正班主任",
  "class_id": "5",  // 仅正副班主任需要
  "is_admin": false
}
验证：
- 如果是正副班主任，检查班级是否已有同角色的教师
- 如果修改班级，检查新班级是否已满
```

### 2. 任课管理API

#### 获取教师任课列表
```
GET /api/teaching-assignments/teacher/<teacher_id>
返回：该教师的所有任课信息
```

#### 获取班级任课列表
```
GET /api/teaching-assignments/class/<class_id>
返回：该班级的所有任课教师
```

#### 添加任课分配
```
POST /api/teaching-assignments
请求体：{
  "teacher_id": "3",
  "class_id": "5",
  "subject": "数学"
}
```

#### 删除任课分配
```
DELETE /api/teaching-assignments/<assignment_id>
```

### 3. 班级管理API

#### 获取班级详情（包含正副班主任）
```
GET /api/classes/<class_id>/details
返回：{
  "class_info": {...},
  "head_teacher": {...},      // 正班主任
  "vice_teacher": {...},      // 副班主任
  "subject_teachers": [...]   // 科任老师列表
}
```

## 界面设计

### 1. 后台管理 - 用户编辑

```
┌─────────────────────────────────────┐
│ 编辑用户                             │
├─────────────────────────────────────┤
│ 用户名：[张老师        ]             │
│ 主要角色：[正班主任 ▼]               │
│ 管理班级：[五年级1班 ▼]  ← 仅正副班主任显示
│ 超级管理员：☐                        │
│                                      │
│ 任课信息：                           │
│ ┌──────────────────────────────┐   │
│ │ 班级      学科      [操作]    │   │
│ │ 五年级1班  数学     [删除]    │   │
│ │ 五年级2班  数学     [删除]    │   │
│ │ 六年级1班  数学     [删除]    │   │
│ │ [+ 添加任课]                  │   │
│ └──────────────────────────────┘   │
│                                      │
│ [取消]  [保存]                       │
└─────────────────────────────────────┘
```

### 2. 任课管理页面（新增）

```
┌─────────────────────────────────────────────┐
│ 任课管理                                     │
├─────────────────────────────────────────────┤
│ 查看方式：[按教师 ▼] [按班级]               │
│                                              │
│ 教师：[张老师 ▼]                             │
│                                              │
│ ┌─────────────────────────────────────┐    │
│ │ 班级        学科      添加时间  [操作]│    │
│ │ 五年级1班   数学      2025-01-17  [删除]│  │
│ │ 五年级2班   数学      2025-01-17  [删除]│  │
│ │ 六年级1班   数学      2025-01-17  [删除]│  │
│ └─────────────────────────────────────┘    │
│                                              │
│ [+ 添加任课分配]                             │
└─────────────────────────────────────────────┘
```

## 数据迁移脚本

```python
# migrate_role_system_v2.py

def migrate():
    # 1. 重命名字段（如果需要）
    # ALTER TABLE users RENAME COLUMN role TO primary_role
    
    # 2. 更新超级管理员
    # UPDATE users SET primary_role = '超级管理员' WHERE is_admin = 1
    
    # 3. 创建任课分配表
    # CREATE TABLE teaching_assignments (...)
    
    # 4. 验证数据完整性
    # 检查班级正副班主任唯一性
```

## 验证清单

- [ ] 数据库表结构正确
- [ ] 超级管理员角色正确
- [ ] 班级正副班主任唯一性
- [ ] 任课分配功能正常
- [ ] 绩效考核只显示正班主任
- [ ] 后台管理界面更新
- [ ] API权限验证正确
- [ ] 数据迁移成功

## 优势

1. **清晰的角色定义**：每个角色职责明确
2. **灵活的任课管理**：支持多学科、多班级
3. **严格的约束**：班级管理唯一性保证
4. **可扩展性**：易于添加新角色或功能
5. **数据完整性**：外键约束保证数据一致性

---

**设计版本**: 2.0  
**设计日期**: 2026-01-17  
**状态**: 待实现
