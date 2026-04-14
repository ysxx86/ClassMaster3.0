import sqlite3

def rebuild_students_table():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    # 关闭外键约束
    cursor.execute('PRAGMA foreign_keys=off')
    
    # 开始事务
    cursor.execute('BEGIN TRANSACTION')
    
    try:
        # 创建新表，主键为id和class_id组合
        cursor.execute('''
        CREATE TABLE students_new (
            id TEXT NOT NULL,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            class TEXT,
            height REAL,
            weight REAL,
            chest_circumference REAL,
            vital_capacity REAL,
            dental_caries TEXT,
            vision_left REAL,
            vision_right REAL,
            physical_test_status TEXT,
            comments TEXT,
            created_at TEXT,
            updated_at TEXT,
            daof TEXT DEFAULT '',
            yuwen TEXT DEFAULT '',
            shuxue TEXT DEFAULT '',
            yingyu TEXT DEFAULT '',
            laodong TEXT DEFAULT '',
            tiyu TEXT DEFAULT '',
            yinyue TEXT DEFAULT '',
            meishu TEXT DEFAULT '',
            kexue TEXT DEFAULT '',
            zonghe TEXT DEFAULT '',
            xinxi TEXT DEFAULT '',
            shufa TEXT DEFAULT '',
            semester TEXT DEFAULT '上学期',
            class_id TEXT,
            PRIMARY KEY (id, class_id)
        )
        ''')
        
        # 复制数据
        cursor.execute('INSERT INTO students_new SELECT * FROM students')
        
        # 删除旧表
        cursor.execute('DROP TABLE students')
        
        # 重命名新表
        cursor.execute('ALTER TABLE students_new RENAME TO students')
        
        # 提交事务
        cursor.execute('COMMIT')
        print('数据库结构更新成功！学生表主键已改为(id, class_id)组合')
    except Exception as e:
        # 出错回滚
        cursor.execute('ROLLBACK')
        print(f'更新失败: {str(e)}')
        
    # 重新开启外键约束
    cursor.execute('PRAGMA foreign_keys=on')
    
    # 关闭连接
    conn.close()

if __name__ == '__main__':
    rebuild_students_table() 