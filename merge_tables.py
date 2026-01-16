# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import os
from datetime import datetime

def merge_tables():
    """
    合并students和grades表，移除grades表，将成绩字段添加到students表中
    """
    db_path = 'students.db'
    
    if not os.path.exists(db_path):
        print(f"数据库文件 {db_path} 不存在!")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查students表是否已有成绩字段
        cursor.execute("PRAGMA table_info(students)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # 需要添加的成绩字段
        grade_fields = [
            'daof', 'yuwen', 'shuxue', 'yingyu', 'laodong', 
            'tiyu', 'yinyue', 'meishu', 'kexue', 'zonghe', 
            'xinxi', 'shufa', 'xinli'
        ]
        
        # 检查是否有学期字段
        if 'semester' not in column_names:
            print("添加学期字段到students表")
            cursor.execute("ALTER TABLE students ADD COLUMN semester TEXT DEFAULT '上学期'")
        
        # 为students表添加成绩字段
        for field in grade_fields:
            if field not in column_names:
                print(f"添加 {field} 字段到students表")
                cursor.execute(f"ALTER TABLE students ADD COLUMN {field} TEXT DEFAULT ''")
        
        # 检查grades表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grades'")
        grades_exists = cursor.fetchone() is not None
        
        # 如果grades表存在，合并数据
        if grades_exists:
            print("发现grades表，开始合并数据...")
            # 获取所有年级记录
            cursor.execute('''
                SELECT student_id, class_id, 
                       daof, yuwen, shuxue, yingyu, laodong, 
                       tiyu, yinyue, meishu, kexue, zonghe, 
                       xinxi, shufa 
                FROM grades
            ''')
            grades = cursor.fetchall()
            
            # 更新学生表
            update_count = 0
            for grade in grades:
                student_id, class_id = grade[0], grade[1]
                grade_values = grade[2:]  # 从第三列开始是成绩
                
                # 检查学生是否存在
                cursor.execute("SELECT id FROM students WHERE id = ? AND class_id = ?", (student_id, class_id))
                if cursor.fetchone():
                    # 更新学生的成绩
                    set_clauses = []
                    values = []
                    
                    # 处理每个成绩字段
                    for i, field in enumerate(grade_fields[:-1]):  # 排除新增的xinli字段
                        if i < len(grade_values) and grade_values[i]:  # 确保有成绩值
                            set_clauses.append(f"{field} = ?")
                            values.append(grade_values[i])
                    
                    if set_clauses:
                        # 添加学生ID和班级ID
                        values.extend([student_id, class_id])
                        
                        # 执行更新
                        cursor.execute(f'''
                            UPDATE students 
                            SET {', '.join(set_clauses)} 
                            WHERE id = ? AND class_id = ?
                        ''', values)
                        update_count += 1
            
            print(f"已更新 {update_count} 条学生成绩记录")
            
            # 备份grades表
            print("备份grades表...")
            cursor.execute("ALTER TABLE grades RENAME TO grades_backup")
            
            # 提交更改
            conn.commit()
            print("数据合并完成")
        else:
            print("grades表不存在，无需合并数据")
    
    except Exception as e:
        print(f"合并表时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    merge_tables()
    print("表合并操作完成")
