#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库外键约束迁移脚本
为所有表添加外键约束，提高数据一致性和完整性
"""

import sqlite3
import logging
import datetime
import shutil

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库路径
DATABASE = 'students.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def add_foreign_keys():
    """添加外键约束到所有表"""
    logger.info("开始添加外键约束到数据库")
    
    # 创建数据库备份
    backup_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"students_backup_{backup_date}.db"
    
    try:
        shutil.copy2(DATABASE, backup_file)
        logger.info(f"已创建数据库备份: {backup_file}")
    except Exception as e:
        logger.error(f"创建数据库备份失败: {str(e)}")
        return False
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 临时关闭外键约束
    cursor.execute('PRAGMA foreign_keys=OFF')
    
    # 开始事务
    cursor.execute('BEGIN TRANSACTION')
    
    try:
        # 1. 处理classes表
        # classes表不需要外键约束，它是主表
        
        # 2. 处理users表
        logger.info("修改users表添加外键约束")
        cursor.execute('''
        CREATE TABLE users_new (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            class_id TEXT,
            reset_password TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (class_id) REFERENCES classes(id)
                ON UPDATE CASCADE
                ON DELETE SET NULL
        )
        ''')
        cursor.execute('INSERT INTO users_new SELECT * FROM users')
        cursor.execute('DROP TABLE users')
        cursor.execute('ALTER TABLE users_new RENAME TO users')
        logger.info("users表外键约束添加完成")
        
        # 3. 处理students表
        logger.info("修改students表添加外键约束")
        cursor.execute('''
        CREATE TABLE students_new (
            id TEXT NOT NULL,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            class TEXT,
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
            class_id TEXT,
            PRIMARY KEY (id, class_id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
        ''')
        cursor.execute('INSERT INTO students_new SELECT * FROM students')
        cursor.execute('DROP TABLE students')
        cursor.execute('ALTER TABLE students_new RENAME TO students')
        logger.info("students表外键约束添加完成")
        
        # 4. 处理comments表
        logger.info("修改comments表添加外键约束")
        cursor.execute('''
        CREATE TABLE comments_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            content TEXT NOT NULL,
            user_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON UPDATE CASCADE
                ON DELETE SET NULL
        )
        ''')
        cursor.execute('INSERT INTO comments_new SELECT * FROM comments')
        cursor.execute('DROP TABLE comments')
        cursor.execute('ALTER TABLE comments_new RENAME TO comments')
        logger.info("comments表外键约束添加完成")
        
        # 5. 处理todos表
        logger.info("修改todos表添加外键约束")
        cursor.execute('''
        CREATE TABLE todos_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'pending',
            user_id TEXT,
            class_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (class_id) REFERENCES classes(id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        ''')
        cursor.execute('INSERT INTO todos_new SELECT * FROM todos')
        cursor.execute('DROP TABLE todos')
        cursor.execute('ALTER TABLE todos_new RENAME TO todos')
        logger.info("todos表外键约束添加完成")
        
        # 6. 处理activities表
        logger.info("修改activities表添加外键约束")
        cursor.execute('''
        CREATE TABLE activities_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            user_id TEXT,
            class_id TEXT,
            details TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON UPDATE CASCADE
                ON DELETE SET NULL,
            FOREIGN KEY (class_id) REFERENCES classes(id)
                ON UPDATE CASCADE
                ON DELETE SET NULL
        )
        ''')
        cursor.execute('INSERT INTO activities_new SELECT * FROM activities')
        cursor.execute('DROP TABLE activities')
        cursor.execute('ALTER TABLE activities_new RENAME TO activities')
        logger.info("activities表外键约束添加完成")
        
        # 提交事务
        conn.commit()
        logger.info("所有表格外键约束添加成功！")
        
        # 开启外键约束
        cursor.execute('PRAGMA foreign_keys=ON')
        
        # 验证外键约束是否工作
        cursor.execute('PRAGMA foreign_key_check')
        violations = cursor.fetchall()
        if violations:
            logger.warning(f"检测到外键约束违规: {violations}")
            logger.warning("您可能需要清理这些违规数据")
        else:
            logger.info("未检测到外键约束违规，所有数据符合完整性要求")
        
        return True
        
    except Exception as e:
        # 出错回滚
        conn.rollback()
        logger.error(f"添加外键约束失败: {str(e)}")
        return False
    finally:
        conn.close()

def verify_foreign_keys():
    """验证外键约束是否正确添加"""
    logger.info("验证外键约束")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 开启外键约束
    cursor.execute('PRAGMA foreign_keys=ON')
    
    # 检查所有表的外键约束
    tables = ['users', 'students', 'comments', 'todos', 'activities']
    
    for table in tables:
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        foreign_keys = cursor.fetchall()
        logger.info(f"表 {table} 的外键约束: {len(foreign_keys)}")
        
        for fk in foreign_keys:
            logger.info(f"  - 外键: {fk}")
    
    conn.close()
    logger.info("外键约束验证完成")

if __name__ == "__main__":
    if add_foreign_keys():
        verify_foreign_keys()
        print("外键约束添加成功！数据库结构已更新。")
    else:
        print("外键约束添加失败，请检查日志获取详细信息。")
