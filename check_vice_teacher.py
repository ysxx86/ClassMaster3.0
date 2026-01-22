#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('students.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查找副班主任用户
cursor.execute('SELECT id, username, primary_role, class_id FROM users WHERE primary_role = "副班主任"')
users = cursor.fetchall()

print('副班主任用户:')
for u in users:
    print(f'  ID: {u["id"]}, 用户名: {u["username"]}, 角色: {u["primary_role"]}, 班级ID: {u["class_id"]}')
    
    # 查找该用户的teaching_assignments记录
    cursor.execute('SELECT class_id, subject FROM teaching_assignments WHERE teacher_id = ?', (u['id'],))
    assignments = cursor.fetchall()
    
    print(f'  teaching_assignments记录 ({len(assignments)}条):')
    for a in assignments:
        print(f'    班级: {a["class_id"]}, 学科: {a["subject"]}')
    print()

conn.close()
