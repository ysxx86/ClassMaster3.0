import shutil, sqlite3, sys, os
src='students.db'
backup='students_test_copy.db'
if os.path.exists(backup): os.remove(backup)
shutil.copy2(src, backup)
conn=sqlite3.connect(backup)
conn.row_factory=sqlite3.Row
c=conn.cursor()
try:
    c.execute('PRAGMA foreign_keys=ON')
    student_id='41'
    class_id='11'
    print('before comments count:', c.execute('SELECT COUNT(*) FROM comments WHERE student_id=?',(student_id,)).fetchone()[0])
    print('before students exists:', c.execute('SELECT COUNT(*) FROM students WHERE id=? AND class_id=?',(student_id,class_id)).fetchone()[0])
    try:
        c.execute('DELETE FROM comments WHERE student_id=?',(student_id,))
        print('deleted comments')
    except Exception as e:
        print('delete comments error', e)
    try:
        c.execute('DELETE FROM students WHERE id=? AND class_id=?',(student_id,class_id))
        print('deleted student')
    except Exception as e:
        print('delete student error', e)
    conn.commit()
    print('after comments count:', c.execute('SELECT COUNT(*) FROM comments WHERE student_id=?',(student_id,)).fetchone()[0])
    print('after students exists:', c.execute('SELECT COUNT(*) FROM students WHERE id=? AND class_id=?',(student_id,class_id)).fetchone()[0])
except Exception as e:
    print('error', e)
finally:
    conn.close()
    if os.path.exists(backup): os.remove(backup)
