import sqlite3
import datetime

def add_missing_columns():
    """添加缺失的列到students表"""
    print("开始添加缺失的列...")
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    # 获取现有列
    cursor.execute("PRAGMA table_info(students)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    print(f"现有列: {existing_columns}")
    
    # 需要添加的列
    columns_to_add = {
        'daof': 'TEXT',  # 道德与法治
        'yuwen': 'TEXT',  # 语文
        'shuxue': 'TEXT',  # 数学
        'yingyu': 'TEXT',  # 英语
        'laodong': 'TEXT',  # 劳动
        'tiyu': 'TEXT',  # 体育
        'yinyue': 'TEXT',  # 音乐
        'meishu': 'TEXT',  # 美术
        'kexue': 'TEXT',  # 科学
        'zonghe': 'TEXT',  # 综合
        'xinxi': 'TEXT',  # 信息技术
        'shufa': 'TEXT',  # 书法
        'semester': 'TEXT'  # 学期
    }
    
    # 添加缺失的列
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE students ADD COLUMN {col_name} {col_type}")
                print(f"添加列: {col_name} ({col_type})")
            except sqlite3.Error as e:
                print(f"添加列 {col_name} 时出错: {e}")
    
    conn.commit()
    
    # 创建缺少的表
    try:
        # 创建todos表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'pending',
            user_id INTEGER,
            class_id TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        print("创建todos表")
        
        # 创建activities表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            user_id INTEGER,
            class_id TEXT,
            details TEXT,
            created_at TEXT
        )
        ''')
        print("创建activities表")
        
        # 创建comments表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            content TEXT NOT NULL,
            user_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        print("创建comments表")
        
    except sqlite3.Error as e:
        print(f"创建表时出错: {e}")
    
    conn.commit()
    conn.close()
    
    print("数据库结构修复完成")
    
if __name__ == "__main__":
    add_missing_columns() 