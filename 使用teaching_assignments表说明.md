# 使用 teaching_assignments 表说明

## 发现的问题

数据库中已经存在 `teaching_assignments` 表，而不是我们新创建的 `teacher_classes` 表。

## teaching_assignments 表结构

```sql
CREATE TABLE teaching_assignments (
    id INTEGER PRIMARY KEY,
    teacher_id TEXT NOT NULL,
    class_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

**与 teacher_classes 的区别**：
- `class_id` 是 TEXT 类型（而不是 INTEGER）
- `subject` 是 TEXT 类型存储学科名称（而不是 subject_id 存储学科ID）
- 没有外键约束

## 已完成的适配

### 1. 修改 subjects.py 中的 API
- `get_teacher_classes()` - 通过学科名称关联 subjects 表
- `assign_teacher_to_classes()` - 先查询学科名称，然后存储
- `remove_teacher_class_assignment()` - 直接删除记录
- `get_class_subject_teachers()` - 通过学科名称查询

### 2. 修改 utils/permission_checker.py
- `get_teaching_classes()` - 从 teaching_assignments 表查询
- 将 TEXT 类型的 class_id 转换为整数

### 3. 前端代码
- 无需修改，API 接口保持不变

## 测试步骤

1. 重启服务器
2. 进入"教师分配" → "学科班级分配"
3. 选择一个教师
4. 选择一个学科
5. 勾选几个班级
6. 点击"分配选中的班级"
7. 查看"当前分配"是否正确显示

## 验证数据

```bash
# 查看分配记录
sqlite3 students.db "SELECT * FROM teaching_assignments;"

# 查看某个教师的分配
sqlite3 students.db "SELECT ta.*, c.class_name, s.name as subject_name FROM teaching_assignments ta JOIN classes c ON ta.class_id = c.id JOIN subjects s ON ta.subject = s.name WHERE ta.teacher_id='教师ID';"
```

## 完成时间

2026年1月18日
