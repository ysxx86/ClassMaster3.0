#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加 teacher_classes 表
用于记录教师任教的班级和学科
"""

import sqlite3
import os

DATABASE = 'students.db'

def migrate():
    """执行迁移"""
    print("开始迁移：添加 teacher_classes 表...")
    
    if not os.path.exists(DATABASE):
        print(f"错误：数据库文件 {DATABASE} 不存在")
        return False
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # 检查表是否已存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='teacher_classes'
        """)
        
        if cursor.fetchone():
            print("teacher_classes 表已存在，跳过创建")
        else:
            # 创建 teacher_classes 表
            cursor.execute("""
                CREATE TABLE teacher_classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id TEXT NOT NULL,
                    class_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                    UNIQUE(teacher_id, class_id, subject_id)
                )
            """)
            print("✓ 创建 teacher_classes 表成功")
        
        # 创建索引以提高查询性能
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_teacher_classes_teacher 
            ON teacher_classes(teacher_id)
        """)
        print("✓ 创建索引 idx_teacher_classes_teacher")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_teacher_classes_class 
            ON teacher_classes(class_id)
        """)
        print("✓ 创建索引 idx_teacher_classes_class")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_teacher_classes_subject 
            ON teacher_classes(subject_id)
        """)
        print("✓ 创建索引 idx_teacher_classes_subject")
        
        conn.commit()
        print("\n迁移完成！")
        return True
        
    except Exception as e:
        print(f"\n迁移失败：{str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
