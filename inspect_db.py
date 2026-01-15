import sqlite3

db = 'students.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

print('Tables:')
for row in cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    print('\n===', row[0], '===')
    print(row[1])

print('\nPRAGMA foreign_key_list(comments):')
try:
    for r in cur.execute("PRAGMA foreign_key_list('comments')"):
        print(r)
except Exception as e:
    print('ERROR:', e)

print('\nPRAGMA foreign_key_list(students):')
try:
    for r in cur.execute("PRAGMA foreign_key_list('students')"):
        print(r)
except Exception as e:
    print('ERROR:', e)

print('\nPRAGMA table_info(comments):')
for r in cur.execute("PRAGMA table_info('comments')"):
    print(r)

print('\nPRAGMA table_info(students):')
for r in cur.execute("PRAGMA table_info('students')"):
    print(r)

conn.close()
print('\nDone')
