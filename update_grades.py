# -*- coding: utf-8 -*-
"""
此脚本用于更新数据库中的成绩值

注意：
- 空字符串("") 表示该学生该科目的成绩尚未填写
- "/" 表示该科目免修/不需要上课
这两者含义不同，不要互相转换
"""

import sqlite3

# # 连接数据库
# conn = sqlite3.connect('students.db')
# cursor = conn.cursor()

# # 更新字段 - 现在不需要将"/"更新为空值
# subjects = ['yuwen', 'shuxue', 'yingyu', 'daof', 'kexue', 'tiyu', 'yinyue', 'meishu', 'zonghe', 'xinxi', 'shufa']
# for subject in subjects:
#     query = f"UPDATE students SET {subject} = '' WHERE {subject} = '/'"
#     cursor.execute(query)
#     updated = cursor.rowcount
#     print(f'更新{subject}字段: {updated}行')

# # 提交事务并关闭连接
# conn.commit()
# print('所有更新已完成')
# conn.close()

print("脚本已停用 - '/'表示免修，''表示未填写成绩，这两者含义不同") 