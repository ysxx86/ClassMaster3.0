import sqlite3
import shutil
import os
DB='students.db'
BAK='students.db.pre_drop_comments_old.bak'
print('备份数据库到',BAK)
shutil.copyfile(DB,BAK)
conn=sqlite3.connect(DB)
cur=conn.cursor()
try:
    # 检查表是否存在
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comments_old'")
    if not cur.fetchone():
        print('comments_old 表不存在，跳过删除')
    else:
        print('发现 comments_old 表，尝试删除')
        cur.execute('PRAGMA foreign_keys = OFF')
        conn.commit()
        cur.execute('DROP TABLE IF EXISTS comments_old')
        conn.commit()
        cur.execute('PRAGMA foreign_keys = ON')
        conn.commit()
        print('已删除 comments_old')
except Exception as e:
    print('删除 comments_old 时出错:', e)
finally:
    conn.close()
    print('完成')
