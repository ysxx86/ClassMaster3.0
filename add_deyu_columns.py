#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
添加德育维度字段到students表
"""

import sqlite3
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/add_deyu_columns.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据库文件
DATABASE = 'students.db'

def add_deyu_columns():
    """添加德育维度字段到students表"""
    logger.info("开始添加德育维度字段")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 检查现有字段
    cursor.execute("PRAGMA table_info(students)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    logger.info(f"现有数据库列: {existing_columns}")
    
    # 要添加的字段
    deyu_columns = {
        'pinzhi': 'INTEGER',     # 品质 30分
        'xuexi': 'INTEGER',      # 学习 20分
        'jiankang': 'INTEGER',   # 健康 20分
        'shenmei': 'INTEGER',    # 审美 10分
        'shijian': 'INTEGER',    # 实践 10分
        'shenghuo': 'INTEGER'    # 生活 10分
    }
    
    # 添加缺失的列
    for column, col_type in deyu_columns.items():
        if column not in existing_columns:
            logger.warning(f"添加德育维度列: {column} ({col_type})")
            try:
                cursor.execute(f"ALTER TABLE students ADD COLUMN {column} {col_type}")
                conn.commit()
                logger.info(f"成功添加德育维度列: {column}")
            except sqlite3.Error as e:
                logger.error(f"添加德育维度列 {column} 时出错: {e}")
                logger.error(f"可能该列已存在，或者表结构不允许修改")
    
    # 检查是否成功添加了字段
    cursor.execute("PRAGMA table_info(students)")
    updated_columns = [row[1] for row in cursor.fetchall()]
    logger.info(f"更新后的数据库列: {updated_columns}")
    
    # 检查是否所有德育维度字段都添加成功
    all_added = all(column in updated_columns for column in deyu_columns)
    if all_added:
        logger.info("所有德育维度字段已成功添加")
    else:
        missing_columns = [col for col in deyu_columns if col not in updated_columns]
        logger.error(f"以下德育维度字段未添加成功: {missing_columns}")
    
    # 关闭连接
    conn.close()
    logger.info("字段添加操作完成")

if __name__ == "__main__":
    add_deyu_columns()
    print("德育维度字段添加完成，请查看日志获取详细信息") 