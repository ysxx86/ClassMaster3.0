#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import json
import os

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_system_settings_table():
    """添加系统设置表到数据库"""
    try:
        # 连接到数据库
        conn = sqlite3.connect('students.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 创建系统设置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 添加默认设置
        default_settings = [
            ('school_year', '2024-2025', '学年设置'),
            ('semester', '2', '学期设置 (1: 第一学期, 2: 第二学期)'),
            ('start_date', '2025-03-01', '开学时间')
        ]
        
        # 插入默认设置
        for key, value, description in default_settings:
            cursor.execute('''
            INSERT OR IGNORE INTO system_settings (key, value, description)
            VALUES (?, ?, ?)
            ''', (key, value, description))
        
        # 提交更改
        conn.commit()
        logger.info("系统设置表创建成功")
        
        # 导入现有配置（如果存在）
        if os.path.exists('config.json'):
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 将现有配置导入到数据库
                for key, value in config.items():
                    # 跳过已存在的默认设置
                    if key in ['school_year', 'semester', 'start_date']:
                        continue
                    
                    # 将值转换为JSON字符串
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    else:
                        value = str(value)
                    
                    cursor.execute('''
                    INSERT OR REPLACE INTO system_settings (key, value)
                    VALUES (?, ?)
                    ''', (key, value))
                
                conn.commit()
                logger.info("现有配置导入成功")
            except Exception as e:
                logger.error(f"导入现有配置时出错: {str(e)}")
        
        # 关闭连接
        conn.close()
        return True
    except Exception as e:
        logger.error(f"创建系统设置表时出错: {str(e)}")
        return False

if __name__ == "__main__":
    add_system_settings_table()
    print("系统设置表添加完成") 