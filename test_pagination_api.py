#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试分页API性能
"""

import sqlite3
import time

DATABASE = 'students.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def test_pagination():
    """测试分页查询性能"""
    print("=" * 60)
    print("分页API性能测试")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取总数
    cursor.execute('SELECT COUNT(*) as total FROM students')
    total = cursor.fetchone()['total']
    print(f"\n学生总数: {total}")
    
    # 测试不同页大小的性能
    page_sizes = [50, 100, 200]
    
    for page_size in page_sizes:
        print(f"\n{'='*60}")
        print(f"测试每页 {page_size} 个学生")
        print(f"{'='*60}")
        
        total_pages = (total + page_size - 1) // page_size
        print(f"总页数: {total_pages}")
        
        # 测试第1页
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
            ORDER BY c.class_name, CAST(s.id AS INTEGER)
            LIMIT ? OFFSET ?
        ''', (page_size, 0))
        students = cursor.fetchall()
        elapsed = time.time() - start
        
        print(f"\n第1页:")
        print(f"  - 查询到 {len(students)} 个学生")
        print(f"  - 查询耗时: {elapsed*1000:.2f}ms")
        
        # 测试中间页
        if total_pages > 2:
            middle_page = total_pages // 2
            offset = (middle_page - 1) * page_size
            
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
                ORDER BY c.class_name, CAST(s.id AS INTEGER)
                LIMIT ? OFFSET ?
            ''', (page_size, offset))
            students = cursor.fetchall()
            elapsed = time.time() - start
            
            print(f"\n第{middle_page}页(中间页):")
            print(f"  - 查询到 {len(students)} 个学生")
            print(f"  - 查询耗时: {elapsed*1000:.2f}ms")
        
        # 测试最后一页
        last_offset = (total_pages - 1) * page_size
        
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
            ORDER BY c.class_name, CAST(s.id AS INTEGER)
            LIMIT ? OFFSET ?
        ''', (page_size, last_offset))
        students = cursor.fetchall()
        elapsed = time.time() - start
        
        print(f"\n第{total_pages}页(最后一页):")
        print(f"  - 查询到 {len(students)} 个学生")
        print(f"  - 查询耗时: {elapsed*1000:.2f}ms")
        
        # 性能评估
        if elapsed * 1000 < 10:
            print(f"\n✅ 性能优秀! 分页查询<10ms")
        elif elapsed * 1000 < 50:
            print(f"\n✅ 性能良好! 分页查询<50ms")
        else:
            print(f"\n⚠️  性能一般,分页查询{elapsed*1000:.2f}ms")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("推荐配置")
    print("=" * 60)
    print("\n基于测试结果,推荐:")
    print("- 每页大小: 100个学生")
    print("- 首次加载: 第1页(100个)")
    print("- 按需加载: 点击\"加载更多\"加载下一页")
    print("\n预期效果:")
    print("- 首次加载: <1秒")
    print("- 加载更多: <1秒/页")
    print("- 用户体验: 立即可用")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_pagination()
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
