# -*- coding: utf-8 -*-
"""
统一数据库连接模块
提供标准的数据库连接获取方式
"""

import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DATABASE = 'students.db'

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    获取数据库连接（统一入口）

    Args:
        db_path: 可选的数据库路径，默认使用 DATABASE

    Returns:
        sqlite3.Connection: 配置好的数据库连接
    """
    actual_db_path = db_path or DATABASE
    try:
        conn = sqlite3.connect(actual_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except sqlite3.Error as e:
        logger.error(f"数据库连接失败: {e}")
        raise

def close_db_connection(conn: sqlite3.Connection) -> None:
    """
    安全关闭数据库连接

    Args:
        conn: 数据库连接对象
    """
    if conn:
        try:
            conn.close()
        except Exception as e:
            logger.warning(f"关闭数据库连接时出错: {e}")
