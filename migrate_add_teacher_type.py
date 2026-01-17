#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为users表添加teacher_type字段
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """执行数据库迁移"""
    try:
        conn = sqlite3.connect('students.db')
        cursor = conn.cursor()
        
        # 检查teacher_type字段是否已存在
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'teacher_type' in columns:
            logger.info("teacher_type字段已存在，无需迁移")
            conn.close()
            return True
        
        # 添加teacher_type字段
        logger.info("开始添加teacher_type字段...")
        cursor.execute('''
            ALTER TABLE users ADD COLUMN teacher_type TEXT DEFAULT '正班主任'
        ''')
        
        conn.commit()
        logger.info("✓ teacher_type字段添加成功")
        
        # 验证字段是否添加成功
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'teacher_type' in columns:
            logger.info("✓ 验证成功：teacher_type字段已存在")
            conn.close()
            return True
        else:
            logger.error("✗ 验证失败：teacher_type字段未找到")
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"✗ 迁移失败: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("开始数据库迁移：添加teacher_type字段")
    logger.info("=" * 50)
    
    success = migrate()
    
    if success:
        logger.info("=" * 50)
        logger.info("✓ 数据库迁移完成")
        logger.info("=" * 50)
    else:
        logger.error("=" * 50)
        logger.error("✗ 数据库迁移失败")
        logger.error("=" * 50)
        exit(1)
