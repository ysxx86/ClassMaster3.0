import sqlite3

# 连接数据库
conn = sqlite3.connect('students.db')
cursor = conn.cursor()

# 获取所有表名
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("数据库中的表:")
for table in tables:
    print(f"\n表名: {table[0]}")
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    print("列:")
    for column in columns:
        print(f"  {column[1]} ({column[2]})")

conn.close()
