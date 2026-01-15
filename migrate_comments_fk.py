import sqlite3
import shutil
import os

DB = 'students.db'
BACKUP = 'students.db.bak'

print('备份数据库...')
if not os.path.exists(BACKUP):
    shutil.copyfile(DB, BACKUP)
    print('备份到', BACKUP)
else:
    print('备份已存在，跳过复制')

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('PRAGMA foreign_keys = OFF')
conn.commit()

# 检查是否已有 class_id 列
cur.execute("PRAGMA table_info('comments')")
cols = [r[1] for r in cur.fetchall()]
if 'class_id' in cols:
    print('comments 表已包含 class_id 列，尝试直接创建新表')
else:
    print('向 comments 表添加 class_id 列')
    cur.execute("ALTER TABLE comments ADD COLUMN class_id TEXT")
    conn.commit()

print('为 comments.class_id 填充值（从 students 表关联）')
cur.execute('''
    UPDATE comments
    SET class_id = (
        SELECT class_id FROM students WHERE students.id = comments.student_id LIMIT 1
    )
''')
conn.commit()

print('创建新表 comments_new，带复合外键 (student_id, class_id) -> students(id, class_id)')
cur.execute('''
CREATE TABLE IF NOT EXISTS comments_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    class_id TEXT,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (student_id, class_id) REFERENCES students(id, class_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')
conn.commit()

print('将数据复制到 comments_new')
cur.execute('''
    INSERT INTO comments_new (id, student_id, class_id, user_id, content, created_at, updated_at)
    SELECT id, student_id, class_id, user_id, content, created_at, updated_at FROM comments
''')
conn.commit()

print('验证复制行数')
cur.execute('SELECT COUNT(*) FROM comments')
old_count = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM comments_new')
new_count = cur.fetchone()[0]
print('old_count=', old_count, 'new_count=', new_count)

if new_count >= old_count:
    print('替换旧表')
    cur.execute('ALTER TABLE comments RENAME TO comments_old')
    cur.execute('ALTER TABLE comments_new RENAME TO comments')
    conn.commit()
    print('已重命名并替换表')
    print('可选择删除旧表 comments_old（保留备份）')
else:
    print('复制行数不一致，取消迁移，恢复备份')
    conn.close()
    shutil.copyfile(BACKUP, DB)
    print('已从备份恢复')
    raise SystemExit('迁移失败：行数不一致')

# 尝试重新启用 foreign_keys
cur.execute('PRAGMA foreign_keys = ON')
conn.commit()
print('重新启用 foreign_keys')

conn.close()
print('迁移完成')
