#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从整个代码库中移除 class 字段的依赖，改用 class_id 关联到 classes 表
"""

import sqlite3
import glob
import os
import re
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE = 'students.db'
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def get_db_connection():
    """创建数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def update_sql_queries_in_file(file_path):
    """更新文件中的 SQL 查询"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 记录原始内容以检测是否有变化
    original_content = content

    # 替换模式1: SELECT ... c.class_name as class FROM students s LEFT JOIN classes c ON s.class_id = c.id
    pattern1 = r"SELECT\s+.*?\bclass\b.*?\bFROM\s+students\b"
    matches = re.finditer(pattern1, content, re.IGNORECASE)
    for match in matches:
        old_query = match.group(0)
        # 在查询中添加 classes 表的连接
        new_query = old_query.replace("students", "students s")
        new_query = new_query.replace("class", "c.class_name as class")
        new_query = new_query.replace("FROM students s", "FROM students s LEFT JOIN classes c ON s.class_id = c.id")
        content = content.replace(old_query, new_query)

    # 替换模式2: WHERE class_id = ?
    pattern2 = r"WHERE\s+class\s*=\s*\?"
    matches = re.finditer(pattern2, content, re.IGNORECASE)
    for match in matches:
        old_where = match.group(0)
        new_where = "WHERE class_id = ?"
        content = content.replace(old_where, new_where)

    # 如果内容有变化，写回文件
    if content != original_content:
        logger.info(f"更新文件: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def migrate_codebase():
    """迁移整个代码库"""
    # 获取所有 Python 文件
    python_files = glob.glob(os.path.join(PROJECT_ROOT, "**/*.py"), recursive=True)
    
    updated_files = []
    for file_path in python_files:
        try:
            if update_sql_queries_in_file(file_path):
                updated_files.append(os.path.basename(file_path))
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
    
    if updated_files:
        logger.info(f"已更新以下文件: {', '.join(updated_files)}")
    else:
        logger.info("没有文件需要更新")

if __name__ == "__main__":
    logger.info("开始迁移代码库...")
    migrate_codebase()
    logger.info("代码库迁移完成")
