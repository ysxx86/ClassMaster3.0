# -*- coding: utf-8 -*-
"""
统一配置管理模块
整合所有配置项，避免在多个文件中重复定义
"""

import os
import json
import logging

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        # 基础路径配置
        self.UPLOAD_FOLDER = 'uploads'
        self.TEMPLATE_FOLDER = 'templates'
        self.EXPORTS_FOLDER = 'exports'
        self.DATABASE = 'students.db'
        self.LOGS_FOLDER = 'logs'
        
        # Flask应用配置
        self.SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")
        self.MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
        self.JSON_AS_ASCII = False
        
        # DeepSeek API配置
        self.DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
        
        # 系统设置 (从config.json加载)
        self.system_settings = self._load_json_config()
        
        # 确保必要的文件夹存在
        self._ensure_directories()
        
        # 设置日志
        self._setup_logging()
    
    def _ensure_directories(self):
        """确保所有必要的文件夹存在"""
        directories = [
            self.UPLOAD_FOLDER,
            self.TEMPLATE_FOLDER, 
            self.EXPORTS_FOLDER,
            self.LOGS_FOLDER,
            os.path.join(self.TEMPLATE_FOLDER, 'docx'),
            os.path.join(self.UPLOAD_FOLDER, 'backups'),
            os.path.join(self.UPLOAD_FOLDER, 'exams')
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _load_json_config(self):
        """从config.json加载系统设置"""
        config_file = 'config.json'
        default_settings = {
            "deepseek_api_key": self.DEEPSEEK_API_KEY,
            "deepseek_api_enabled": bool(self.DEEPSEEK_API_KEY),
            "school_year": "2024-2025",
            "semester": "1", 
            "start_date": "2025-09-01"
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                # 合并默认设置
                default_settings.update(settings)
        except Exception as e:
            logging.warning(f"加载config.json失败: {e}, 使用默认设置")
        
        return default_settings
    
    def _setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.LOGS_FOLDER, "root_server.log"), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def get_db_connection(self):
        """获取数据库连接"""
        import sqlite3
        conn = sqlite3.connect(self.DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    
    def save_json_config(self):
        """保存系统设置到config.json"""
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.system_settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"保存config.json失败: {e}")
            return False
    
    def update_setting(self, key, value):
        """更新系统设置"""
        self.system_settings[key] = value
        return self.save_json_config()
    
    def get_setting(self, key, default=None):
        """获取系统设置"""
        return self.system_settings.get(key, default)

# 全局配置实例
config = ConfigManager()

# 导出常用配置项，保持向后兼容
UPLOAD_FOLDER = config.UPLOAD_FOLDER
TEMPLATE_FOLDER = config.TEMPLATE_FOLDER
EXPORTS_FOLDER = config.EXPORTS_FOLDER
DATABASE = config.DATABASE
SECRET_KEY = config.SECRET_KEY 