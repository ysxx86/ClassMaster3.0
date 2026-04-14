import shutil, sqlite3, os
DB='students.db'
TEST='students_test.db'
if os.path.exists(TEST): os.remove(TEST)
shutil.copyfile(DB, TEST)
print('Copied to', TEST)
conn=sqlite3.connect(TEST)
cur=conn.cursor()
class_id='11'
print('Counts before:')
cur.execute('SELECT COUNT(*) FROM students WHERE class_id=?', (class_id,))
print('students:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM comments WHERE class_id=?', (class_id,))
print('comments (with class_id):', cur.fetchone()[0])
# comments may have null class_id; count by join
cur.execute("SELECT COUNT(c.id) FROM comments c JOIN students s ON c.student_id=s.id AND c.class_id=s.class_id WHERE s.class_id=?", (class_id,))
print('comments join count:', cur.fetchone()[0])

try:
    cur.execute('PRAGMA foreign_keys = OFF')
    cur.execute('DELETE FROM comments WHERE student_id IN (SELECT id FROM students WHERE class_id = ?)', (class_id,))
    cur.execute('DELETE FROM students WHERE class_id = ?', (class_id,))
    conn.commit()
    print('Deletes succeeded')
    cur.execute('SELECT COUNT(*) FROM students WHERE class_id=?', (class_id,))
    print('students after:', cur.fetchone()[0])
    cur.execute('SELECT COUNT(*) FROM comments WHERE class_id=?', (class_id,))
    print('comments after:', cur.fetchone()[0])
except Exception as e:
    print('Error during delete:', e)
finally:
    cur.execute('PRAGMA foreign_keys = ON')
    conn.close()
    print('Done')
