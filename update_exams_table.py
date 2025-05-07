#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新exams表结构，添加has_paper和paper_path列
"""

import sqlite3
import os
import datetime
import logging

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
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

def backup_database():
    """备份数据库"""
    try:
        # 生成备份文件名
        backup_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        backup_file = f"students_backup_{backup_time}.db"
        
        # 复制数据库文件
        import shutil
        shutil.copy2(DATABASE, backup_file)
        
        logger.info(f"数据库已备份至: {backup_file}")
        return True
    except Exception as e:
        logger.error(f"备份数据库时出错: {e}")
        return False

def update_exams_table():
    """更新exams表，添加has_paper和paper_path列"""
    try:
        # 先备份数据库
        if not backup_database():
            logger.error("无法继续更新，备份失败")
            return False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(exams)")
        columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"exams表现有列: {columns}")
        
        # 检查是否已存在目标列
        if 'has_paper' in columns and 'paper_path' in columns:
            logger.info("has_paper和paper_path列已经存在，无需更新")
            conn.close()
            return True
            
        # 添加has_paper列
        if 'has_paper' not in columns:
            cursor.execute("ALTER TABLE exams ADD COLUMN has_paper INTEGER DEFAULT 0")
            logger.info("已添加has_paper列到exams表")
            
        # 添加paper_path列
        if 'paper_path' not in columns:
            cursor.execute("ALTER TABLE exams ADD COLUMN paper_path TEXT")
            logger.info("已添加paper_path列到exams表")
            
        conn.commit()
        conn.close()
        logger.info("exams表结构更新完成")
        return True
        
    except Exception as e:
        logger.error(f"更新exams表结构时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("====== ClassMaster 试卷表结构更新工具 ======")
    print("本工具将更新exams表结构，添加has_paper和paper_path列。")
    print("执行前会自动创建数据库备份。")
    
    success = update_exams_table()
    
    if success:
        print("\n数据库更新已成功完成!")
    else:
        print("\n数据库更新过程中出现错误，请检查日志。")
        print("您可以使用自动创建的备份文件恢复数据库。") 