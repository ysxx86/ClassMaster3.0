import sqlite3
import os

print("开始向students表添加德育维度字段")

# 确保logs目录存在
if not os.path.exists('logs'):
    os.makedirs('logs')
    print("已创建logs目录")

try:
    # 连接数据库
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    print("已连接到数据库")
    
    # 检查现有字段
    cursor.execute("PRAGMA table_info(students)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    print(f"现有数据库列: {existing_columns}")
    
    # 要添加的字段
    deyu_columns = {
        'pinzhi': 'INTEGER',     # 品质 30分
        'xuexi': 'INTEGER',      # 学习 20分
        'jiankang': 'INTEGER',   # 健康 20分
        'shenmei': 'INTEGER',    # 审美 10分
        'shijian': 'INTEGER',    # 实践 10分
        'shenghuo': 'INTEGER'    # 生活 10分
    }
    
    # 添加缺失的列
    for column, col_type in deyu_columns.items():
        if column not in existing_columns:
            print(f"添加德育维度列: {column} ({col_type})")
            try:
                cursor.execute(f"ALTER TABLE students ADD COLUMN {column} {col_type}")
                conn.commit()
                print(f"成功添加德育维度列: {column}")
            except sqlite3.Error as e:
                print(f"添加德育维度列 {column} 时出错: {e}")
    
    # 检查是否成功添加了字段
    cursor.execute("PRAGMA table_info(students)")
    updated_columns = [row[1] for row in cursor.fetchall()]
    print(f"更新后的数据库列: {updated_columns}")
    
    # 检查是否所有德育维度字段都添加成功
    added_columns = [col for col in deyu_columns if col in updated_columns]
    print(f"已成功添加的德育维度字段: {added_columns}")
    
    # 关闭连接
    conn.close()
    print("字段添加操作完成")
    
except Exception as e:
    print(f"添加字段时出错: {e}")

print("德育维度字段添加完成") 