#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理孤立的学科班级分配记录

问题：当从 teacher_subjects 表删除教师的任教学科时，
teaching_assignments 表中的相关记录没有被同步删除，
导致教师在成绩管理中仍然可以编辑已删除学科的成绩。

此脚本会：
1. 查找所有孤立的 teaching_assignments 记录
2. 显示这些记录的详情
3. 询问是否删除
4. 执行清理操作
"""

import sqlite3
import sys

DATABASE = 'students.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def find_orphaned_assignments():
    """查找孤立的学科班级分配记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查找 teaching_assignments 中存在，但对应学科不在 teacher_subjects 中的记录
    cursor.execute('''
        SELECT 
            ta.id,
            ta.teacher_id,
            u.username,
            ta.class_id,
            c.class_name,
            ta.subject,
            ta.created_at
        FROM teaching_assignments ta
        JOIN users u ON ta.teacher_id = u.id
        LEFT JOIN classes c ON CAST(ta.class_id AS INTEGER) = c.id
        WHERE NOT EXISTS (
            SELECT 1 
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            WHERE ts.teacher_id = ta.teacher_id 
            AND s.name = ta.subject
        )
        ORDER BY u.username, ta.subject, c.class_name
    ''')
    
    orphaned = cursor.fetchall()
    conn.close()
    
    return orphaned

def display_orphaned_assignments(orphaned):
    """显示孤立记录的详情"""
    if not orphaned:
        print("\n✅ 太好了！没有发现孤立的学科班级分配记录。")
        return False
    
    print(f"\n⚠️  发现 {len(orphaned)} 条孤立的学科班级分配记录：\n")
    print("=" * 100)
    print(f"{'ID':<6} {'教师':<15} {'班级':<15} {'学科':<10} {'创建时间':<20}")
    print("=" * 100)
    
    for record in orphaned:
        print(f"{record['id']:<6} {record['username']:<15} {record['class_name'] or '未知':<15} "
              f"{record['subject']:<10} {record['created_at']:<20}")
    
    print("=" * 100)
    print("\n说明：这些记录在 teaching_assignments 表中存在，")
    print("但对应的学科已经从 teacher_subjects 表中删除。")
    print("这会导致教师在成绩管理中仍然可以编辑这些学科的成绩。\n")
    
    return True

def clean_orphaned_assignments(orphaned):
    """清理孤立的记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    deleted_count = 0
    for record in orphaned:
        try:
            cursor.execute('DELETE FROM teaching_assignments WHERE id = ?', (record['id'],))
            deleted_count += 1
            print(f"✓ 已删除：{record['username']} - {record['class_name']} - {record['subject']}")
        except Exception as e:
            print(f"✗ 删除失败 (ID: {record['id']}): {e}")
    
    conn.commit()
    conn.close()
    
    return deleted_count

def main():
    print("\n" + "=" * 100)
    print("清理孤立的学科班级分配记录")
    print("=" * 100)
    
    # 1. 查找孤立记录
    print("\n正在扫描数据库...")
    orphaned = find_orphaned_assignments()
    
    # 2. 显示孤立记录
    has_orphaned = display_orphaned_assignments(orphaned)
    
    if not has_orphaned:
        return
    
    # 3. 询问是否清理
    print("\n是否要清理这些孤立记录？")
    print("清理后，教师将无法编辑这些学科的成绩（除非重新分配）。")
    
    while True:
        choice = input("\n请输入 (y/n): ").strip().lower()
        if choice in ['y', 'yes', '是']:
            break
        elif choice in ['n', 'no', '否']:
            print("\n已取消清理操作。")
            return
        else:
            print("无效输入，请输入 y 或 n")
    
    # 4. 执行清理
    print("\n正在清理...")
    deleted_count = clean_orphaned_assignments(orphaned)
    
    print(f"\n✅ 清理完成！共删除 {deleted_count} 条孤立记录。")
    print("\n建议：")
    print("1. 重启服务器，让权限系统重新加载")
    print("2. 让相关教师重新登录，刷新权限缓存")
    print("3. 如果需要，在教师分配页面重新分配学科和班级\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消。")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
