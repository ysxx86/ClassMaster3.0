#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试学期获取功能
"""

import sqlite3

DATABASE = 'students.db'

def get_current_semester_display():
    """获取当前学期的显示文本"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 获取学年
        cursor.execute("SELECT value FROM system_settings WHERE key = 'school_year'")
        school_year_row = cursor.fetchone()
        school_year = school_year_row['value'] if school_year_row else '2025-2026'
        
        # 获取学期
        cursor.execute("SELECT value FROM system_settings WHERE key = 'semester'")
        semester_row = cursor.fetchone()
        semester = semester_row['value'] if semester_row else '1'
        
        # 组合成显示文本
        semester_text = '第一学期' if semester == '1' else '第二学期'
        return f"{school_year}学年{semester_text}"
    finally:
        conn.close()

if __name__ == '__main__':
    print("测试学期获取功能...")
    print("-" * 50)
    
    # 获取当前学期
    current_semester = get_current_semester_display()
    print(f"当前学期: {current_semester}")
    
    # 验证数据库中的设置
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT key, value FROM system_settings WHERE key IN ('school_year', 'semester')")
    print("\n数据库设置:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # 检查教师的学期信息
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0 AND current_semester = ?", (current_semester,))
    count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
    total = cursor.fetchone()[0]
    
    print(f"\n教师学期信息:")
    print(f"  总教师数: {total}")
    print(f"  学期匹配: {count}")
    print(f"  匹配率: {count/total*100:.1f}%")
    
    conn.close()
    
    print("\n✅ 测试完成！")
