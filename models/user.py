import sqlite3
from flask_login import UserMixin

DATABASE = 'students.db'

class User(UserMixin):
    """用户模型，实现了Flask-Login需要的接口"""
    
    def __init__(self, id, username, password_hash, is_admin=False, class_id=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin
        
        # 确保class_id处理正确
        if class_id is not None:
            try:
                # 尝试转换为整数，因为数据库中class_id是INTEGER
                self.class_id = int(class_id)
                print(f"用户{username}的class_id已转换为整数: {self.class_id}")
            except (ValueError, TypeError):
                # 如果转换失败，保留原始值
                self.class_id = class_id
                print(f"用户{username}的class_id无法转换为整数，保留原值: {self.class_id}，类型: {type(self.class_id).__name__}")
        else:
            self.class_id = None
    
    @staticmethod
    def get_db_connection():
        """获取数据库连接"""
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
        return conn
    
    @classmethod
    def get_by_id(cls, user_id):
        """通过用户ID获取用户"""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                # 记录从数据库获取的原始class_id值和类型
                class_id = user_data['class_id']
                print(f"从数据库获取到用户ID={user_id}的class_id={class_id}, 类型={type(class_id).__name__}")
                
                return cls(
                    id=user_data['id'],
                    username=user_data['username'],
                    password_hash=user_data['password_hash'],
                    is_admin=bool(user_data['is_admin']),
                    class_id=class_id
                )
            return None
        finally:
            conn.close()
    
    @classmethod
    def get_by_username(cls, username):
        """通过用户名获取用户"""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user_data = cursor.fetchone()
            
            if user_data:
                return cls(
                    id=user_data['id'],
                    username=user_data['username'],
                    password_hash=user_data['password_hash'],
                    is_admin=bool(user_data['is_admin']),
                    class_id=user_data['class_id']
                )
            return None
        finally:
            conn.close()
    
    def save(self):
        """保存用户到数据库"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查是否存在
            cursor.execute('SELECT id FROM users WHERE id = ?', (self.id,))
            exists = cursor.fetchone()
            
            if exists:
                # 更新现有用户
                cursor.execute('''
                    UPDATE users 
                    SET username = ?, password_hash = ?, is_admin = ?, class_id = ?
                    WHERE id = ?
                ''', (self.username, self.password_hash, int(self.is_admin), self.class_id, self.id))
            else:
                # 创建新用户
                cursor.execute('''
                    INSERT INTO users (id, username, password_hash, is_admin, class_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (self.id, self.username, self.password_hash, int(self.is_admin), self.class_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"保存用户时出错: {e}")
            return False
        finally:
            conn.close()
    
    @classmethod
    def create_table_if_not_exists(cls):
        """创建用户表（如果不存在）"""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    class_id TEXT,
                    is_admin INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            conn.commit()
            return True
        except Exception as e:
            print(f"创建用户表时出错: {e}")
            return False
        finally:
            conn.close()
            
    def get_id(self):
        """返回用户ID（Flask-Login要求）"""
        return self.id 