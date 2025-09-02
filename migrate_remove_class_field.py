#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
移除students表中的class字段，统一使用class_id
"""

import sqlite3
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE = 'students.db'

def get_db_connection():
    """创建数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_remove_class_field():
    """移除students表中的class字段，确保所有记录都使用class_id"""
    logger.info("开始迁移：移除class字段")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 开始事务
        cursor.execute('BEGIN TRANSACTION')
        
        # 1. 确保所有记录都有正确的class_id
        cursor.execute('''
            UPDATE students
            SET class_id = (
                SELECT c.id 
                FROM classes c 
                WHERE c.class_name = students.class
            )
            WHERE class_id IS NULL 
            AND class IS NOT NULL
        ''')
        
        # 2. 创建新表（不包含class字段）
        cursor.execute('''
        CREATE TABLE students_new (
            id TEXT NOT NULL,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            class_id TEXT,
            height REAL,
            weight REAL,
            chest_circumference REAL,
            vital_capacity REAL,
            dental_caries TEXT,
            vision_left REAL,
            vision_right REAL,
            physical_test_status TEXT,
            comments TEXT,
            created_at TEXT,
            updated_at TEXT,
            daof TEXT DEFAULT '',
            yuwen TEXT DEFAULT '',
            shuxue TEXT DEFAULT '',
            yingyu TEXT DEFAULT '',
            laodong TEXT DEFAULT '',
            tiyu TEXT DEFAULT '',
            yinyue TEXT DEFAULT '',
            meishu TEXT DEFAULT '',
            kexue TEXT DEFAULT '',
            zonghe TEXT DEFAULT '',
            xinxi TEXT DEFAULT '',
            shufa TEXT DEFAULT '',
            semester TEXT DEFAULT '上学期',
            PRIMARY KEY (id, class_id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )''')
        
        # 3. 复制数据到新表
        cursor.execute('''
            INSERT INTO students_new 
            SELECT id, name, gender, class_id, height, weight, 
                   chest_circumference, vital_capacity, dental_caries,
                   vision_left, vision_right, physical_test_status,
                   comments, created_at, updated_at, daof, yuwen,
                   shuxue, yingyu, laodong, tiyu, yinyue, meishu,
                   kexue, zonghe, xinxi, shufa, semester
            FROM students
        ''')
        
        # 4. 删除旧表并重命名新表
        cursor.execute('DROP TABLE students')
        cursor.execute('ALTER TABLE students_new RENAME TO students')
        
        # 提交事务
        cursor.execute('COMMIT')
        logger.info("迁移完成：成功移除class字段")
        
    except Exception as e:
        cursor.execute('ROLLBACK')
        logger.error(f"迁移失败：{str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_remove_class_field()
