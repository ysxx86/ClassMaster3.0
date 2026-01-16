import sqlite3
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

def init_db():
    """初始化数据库"""
    logger.info("初始化数据库")
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    cursor = conn.cursor()
    
    # 创建学生表 - 移除了birth_date、phone、address和notes字段
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
