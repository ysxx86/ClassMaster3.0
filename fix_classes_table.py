#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速修复：创建 classes 表
"""

import sqlite3
import datetime

DATABASE = 'students.db'

def fix_classes_table():
    """创建 classes 表（如果不存在）"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 检查 classes 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='classes'")
        if cursor.fetchone():
            print("✓ classes 表已存在")
            return
        
        print("创建 classes 表...")
        
        # 创建 classes 表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL UNIQUE,
            grade TEXT,
            school_year TEXT,
            description TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        # 从 students 表中提取现有班级
        cursor.execute("""
            SELECT DISTINCT class_id 
            FROM students 
            WHERE class_id IS NOT NULL AND class_id != ''
        """)
        
        existing_class_ids = [row[0] for row in cursor.fetchall()]
        
        if existing_class_ids:
            print(f"发现 {len(existing_class_ids)} 个班级ID，正在创建班级记录...")
            
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for class_id in existing_class_ids:
                # 尝试从 class_id 推断班级名称
                # 如果 class_id 是数字，生成默认名称
                try:
                    class_num = int(class_id)
                    class_name = f"班级{class_num}"
                except ValueError:
                    # 如果不是数字，直接使用 class_id 作为名称
                    class_name = str(class_id)
                
                cursor.execute('''
                INSERT OR IGNORE INTO classes (id, class_name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ''', (class_id, class_name, now, now))
            
            print(f"✓ 已创建 {len(existing_class_ids)} 个班级记录")
        else:
            print("未发现现有班级数据")
        
        conn.commit()
        print("✓ classes 表创建成功")
        
    except Exception as e:
        print(f"✗ 创建 classes 表失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("====== 修复 classes 表 ======")
    fix_classes_table()
    print("====== 修复完成 ======")
