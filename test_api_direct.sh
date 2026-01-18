#!/bin/bash
# 测试 API 是否正常工作

echo "测试 /api/teacher-classes/88"
echo "================================"

# 需要先登录获取 session cookie，这里简化测试
# 直接查询数据库验证数据

sqlite3 students.db << EOF
.mode json
SELECT 
    ta.id,
    ta.class_id,
    c.class_name,
    s.id as subject_id,
    s.name as subject_name,
    ta.created_at
FROM teaching_assignments ta
JOIN classes c ON CAST(ta.class_id AS INTEGER) = c.id
JOIN subjects s ON ta.subject = s.name
WHERE ta.teacher_id = '88'
ORDER BY c.class_name, s.name;
EOF
