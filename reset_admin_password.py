import sqlite3
from werkzeug.security import generate_password_hash

# 生成密码哈希
password_hash = generate_password_hash('123456')
print(f"生成的密码哈希: {password_hash}")

# 连接数据库
conn = sqlite3.connect('students.db')
cursor = conn.cursor()

# 更新admin用户的密码
cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", 
               (password_hash, 'admin'))

# 提交更改
conn.commit()

# 验证更新
cursor.execute("SELECT username, password_hash FROM users WHERE username = 'admin'")
result = cursor.fetchone()
print(f"更新后的记录: {result}")

# 关闭连接
conn.close()

print("密码重置完成") 