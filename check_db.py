#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3

# 连接数据库
conn = sqlite3.connect('students.db')
cursor = conn.cursor()

# 获取exams表结构
print("exams表结构:")
cursor.execute('PRAGMA table_info(exams)')
for row in cursor.fetchall():
    print(row)

# 关闭连接
conn.close() 