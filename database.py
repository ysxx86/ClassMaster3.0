import sqlite3
import logging
from utils.db import get_db_connection

logger = logging.getLogger(__name__)

def init_db():
    """初始化数据库"""
    logger.info("初始化数据库")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        gender TEXT NOT NULL,
        class TEXT,
        height REAL,
        weight REAL
    )''')
    conn.commit()
    conn.close()
