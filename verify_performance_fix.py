#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能修复验证脚本
用于验证评语管理性能优化是否生效
"""

import sqlite3
import time
import sys

DATABASE = 'students.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def test_query_performance():
    """测试查询性能"""
    print("=" * 60)
    print("评语管理性能测试")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 测试1: 查询所有学生数量
    print("\n[测试1] 查询学生总数...")
    start = time.time()
    cursor.execute('SELECT COUNT(*) as count FROM students')
    total_students = cursor.fetchone()['count']
    elapsed = time.time() - start
    print(f"✅ 学生总数: {total_students}")
    print(f"⏱️  查询耗时: {elapsed*1000:.2f}ms")
    
    # 测试2: 查询有评语的学生数量
    print("\n[测试2] 查询有评语的学生数量...")
    start = time.time()
    cursor.execute("SELECT COUNT(*) as count FROM students WHERE comments IS NOT NULL AND comments != ''")
    comments_count = cursor.fetchone()['count']
    elapsed = time.time() - start
    print(f"✅ 有评语学生: {comments_count}")
    print(f"⏱️  查询耗时: {elapsed*1000:.2f}ms")
    
    # 测试3: 查询所有学生(只返回必要字段)
    print("\n[测试3] 查询所有学生(优化后的8个字段)...")
    start = time.time()
    cursor.execute('''
        SELECT 
            s.rowid AS rowid,
            s.id,
            s.name,
            s.gender,
            s.class_id,
            s.comments,
            s.updated_at,
            c.class_name
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        ORDER BY CAST(s.id AS INTEGER)
    ''')
    students = cursor.fetchall()
    elapsed = time.time() - start
    print(f"✅ 查询到 {len(students)} 个学生")
    print(f"⏱️  查询耗时: {elapsed*1000:.2f}ms")
    
    # 测试4: 按班级查询
    print("\n[测试4] 按班级分组统计...")
    start = time.time()
    cursor.execute('''
        SELECT c.class_name, COUNT(*) as count
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        GROUP BY s.class_id
        ORDER BY c.class_name
    ''')
    classes = cursor.fetchall()
    elapsed = time.time() - start
    print(f"✅ 共 {len(classes)} 个班级:")
    for cls in classes:
        print(f"   - {cls['class_name']}: {cls['count']} 名学生")
    print(f"⏱️  查询耗时: {elapsed*1000:.2f}ms")
    
    # 性能评估
    print("\n" + "=" * 60)
    print("性能评估")
    print("=" * 60)
    
    if total_students > 1000:
        expected_time = 100  # 1000+学生应该在100ms内完成
    elif total_students > 100:
        expected_time = 50   # 100+学生应该在50ms内完成
    else:
        expected_time = 20   # 少量学生应该在20ms内完成
    
    actual_time = elapsed * 1000
    
    if actual_time < expected_time:
        print(f"✅ 性能优秀! 查询 {total_students} 个学生只需 {actual_time:.2f}ms")
        print(f"   (预期: <{expected_time}ms)")
    elif actual_time < expected_time * 2:
        print(f"⚠️  性能一般。查询 {total_students} 个学生需要 {actual_time:.2f}ms")
        print(f"   (预期: <{expected_time}ms)")
    else:
        print(f"❌ 性能较差! 查询 {total_students} 个学生需要 {actual_time:.2f}ms")
        print(f"   (预期: <{expected_time}ms)")
        print("\n建议:")
        print("1. 检查数据库索引是否存在")
        print("2. 运行 optimize_database.py 添加索引")
        print("3. 检查数据库文件是否过大")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n下一步:")
    print("1. 重启服务器: python server.py")
    print("2. 强制刷新浏览器: Ctrl+Shift+R (或 Cmd+Shift+R)")
    print("3. 打开评语管理,观察加载速度")
    print("4. 检查后台日志,确认没有 /api/check-updates 轮询")

if __name__ == '__main__':
    try:
        test_query_performance()
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
