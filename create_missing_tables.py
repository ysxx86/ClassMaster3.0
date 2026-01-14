import sqlite3

def create_missing_tables():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    # 创建 activities 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        class_id INTEGER,
        action_type TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (class_id) REFERENCES classes(id)
    )
    ''')

    # 创建 comments 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    # 检查 todos 表的字段
    cursor.execute("PRAGMA table_info(todos)")
    columns = [col[1] for col in cursor.fetchall()]

    # 添加缺失的字段到 todos 表
    if 'user_id' not in columns:
        cursor.execute('ALTER TABLE todos ADD COLUMN user_id TEXT REFERENCES users(id)')
    if 'class_id' not in columns:
        cursor.execute('ALTER TABLE todos ADD COLUMN class_id INTEGER REFERENCES classes(id)')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_missing_tables()
    print("缺失的表和字段已创建完成")
