#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
添加教师信息确认相关字段和表
"""

import sqlite3
import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE = 'students.db'

def migrate():
    """执行数据库迁移"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        logger.info("开始数据库迁移：添加教师信息确认功能")
        
        # 1. 检查并添加用户表的新字段
        logger.info("检查users表字段...")
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'info_confirmed' not in columns:
            logger.info("添加 info_confirmed 字段")
            cursor.execute("ALTER TABLE users ADD COLUMN info_confirmed INTEGER DEFAULT 0")
        
        if 'last_confirmed_date' not in columns:
            logger.info("添加 last_confirmed_date 字段")
            cursor.execute("ALTER TABLE users ADD COLUMN last_confirmed_date TEXT")
        
        if 'current_semester' not in columns:
            logger.info("添加 current_semester 字段")
            cursor.execute("ALTER TABLE users ADD COLUMN current_semester TEXT")
        
        # 2. 创建教师信息修改历史表
        logger.info("创建 teacher_info_history 表")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS teacher_info_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT NOT NULL,
            action TEXT NOT NULL,
            action_type TEXT,
            old_data TEXT,
            new_data TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # 3. 创建索引
        logger.info("创建索引")
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_teacher_info_history_teacher 
        ON teacher_info_history(teacher_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_teacher_info_history_date 
        ON teacher_info_history(created_at)
        ''')
        
        # 4. 获取当前学期（从system_settings表）
        cursor.execute("SELECT value FROM system_settings WHERE key = 'school_year'")
        school_year_row = cursor.fetchone()
        school_year = school_year_row[0] if school_year_row else '2025-2026'
        
        cursor.execute("SELECT value FROM system_settings WHERE key = 'semester'")
        semester_row = cursor.fetchone()
        semester = semester_row[0] if semester_row else '1'
        
        semester_text = '第一学期' if semester == '1' else '第二学期'
        current_semester = f"{school_year}学年{semester_text}"
        
        # 5. 初始化现有教师的学期信息
        logger.info(f"初始化教师学期信息为: {current_semester}")
        cursor.execute('''
        UPDATE users 
        SET current_semester = ? 
        WHERE is_admin = 0 AND current_semester IS NULL
        ''', (current_semester,))
        
        conn.commit()
        logger.info("✅ 数据库迁移完成！")
        
        # 显示统计信息
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
        teacher_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0 AND info_confirmed = 1")
        confirmed_count = cursor.fetchone()[0]
        
        logger.info(f"教师总数: {teacher_count}")
        logger.info(f"已确认信息: {confirmed_count}")
        logger.info(f"未确认信息: {teacher_count - confirmed_count}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        if conn:
            conn.rollback()
            conn.close()
        raise

if __name__ == '__main__':
    migrate()
