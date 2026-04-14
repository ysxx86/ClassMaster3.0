#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试教师班级分配API
"""

import sqlite3

DATABASE = 'students.db'

def test_api_query():
    """测试API使用的查询"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    teacher_id = '88'
    
    print(f"测试教师ID: {teacher_id}")
    print("=" * 60)
    
    # 测试API使用的查询
    cursor.execute('''
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
        WHERE ta.teacher_id = ?
        ORDER BY c.class_name, s.name
    ''', (teacher_id,))
    
    results = cursor.fetchall()
    
    print(f"\n查询结果数量: {len(results)}")
    print("-" * 60)
    
    for row in results:
        print(f"ID: {row['id']}")
        print(f"班级ID: {row['class_id']}")
        print(f"班级名称: {row['class_name']}")
        print(f"学科ID: {row['subject_id']}")
        print(f"学科名称: {row['subject_name']}")
        print(f"创建时间: {row['created_at']}")
        print("-" * 60)
    
    conn.close()

if __name__ == '__main__':
    test_api_query()
