#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试班级API的脚本
"""

import sqlite3
import json

# 数据库路径
DATABASE = 'students.db'

def get_classes():
    """获取所有班级列表"""
    try:
        # 建立数据库连接
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询班级基本信息
        cursor.execute('''
            SELECT id, class_name, created_at, updated_at 
            FROM classes 
            ORDER BY class_name
        ''')
        classes_data = cursor.fetchall()
        print(f"从数据库获取到 {len(classes_data)} 个班级")
        
        # 准备返回数据
        classes = []
        for row in classes_data:
            class_id = row['id']
            class_info = {
                'id': class_id,
                'class_name': row['class_name'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'teacher_name': '未分配',  # 默认值
                'student_count': 0  # 默认值
            }
            
            # 查询班级的班主任信息
            try:
                cursor.execute('''
                    SELECT username FROM users 
                    WHERE class_id = ? AND is_admin = 0
                ''', (class_id,))
                teacher = cursor.fetchone()
                if teacher:
                    class_info['teacher_name'] = teacher['username']
            except Exception as e:
                print(f"查询班级 {class_id} 班主任信息时出错: {str(e)}")
            
            # 查询班级的学生数量
            try:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM students 
                    WHERE class_id = ?
                ''', (class_id,))
                count_row = cursor.fetchone()
                if count_row:
                    class_info['student_count'] = count_row['count']
            except Exception as e:
                print(f"查询班级 {class_id} 学生数量时出错: {str(e)}")
            
            classes.append(class_info)
        
        conn.close()
        
        result = {'status': 'ok', 'classes': classes}
        return result
    except Exception as e:
        print(f"获取班级列表时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'message': f'获取班级列表失败: {str(e)}'}

if __name__ == "__main__":
    result = get_classes()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"总共获取到 {len(result.get('classes', []))} 个班级") 