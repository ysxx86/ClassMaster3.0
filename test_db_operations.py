#!/usr/bin/env python3
import sqlite3

def test_database_operations():
    try:
        # 连接数据库
        conn = sqlite3.connect('students.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 测试添加一个学生记录
        test_data = {
            'id': '999',
            'name': '测试学生',
            'gender': '男',
            'class_id': '1',
            'height': 165.0,
            'weight': 55.0,
            'chest_circumference': 75.0,
            'vital_capacity': 3000.0,
            'dental_caries': '无',
            'vision_left': 5.0,
            'vision_right': 5.0,
            'physical_test_status': '健康',
            'created_at': '2024-01-01 10:00:00',
            'updated_at': '2024-01-01 10:00:00'
        }
        
        print("测试INSERT语句...")
        cursor.execute('''
        INSERT INTO students (
            id, name, gender, class_id, height, weight,
            chest_circumference, vital_capacity, dental_caries,
            vision_left, vision_right, physical_test_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_data['id'], test_data['name'], test_data['gender'],
            test_data['class_id'], test_data['height'], test_data['weight'], 
            test_data['chest_circumference'], test_data['vital_capacity'], test_data['dental_caries'],
            test_data['vision_left'], test_data['vision_right'], test_data['physical_test_status'],
            test_data['created_at'], test_data['updated_at']
        ))
        
        print("INSERT操作成功！")
        
        # 测试JOIN查询
        print("测试JOIN查询...")
        cursor.execute('''
            SELECT s.*, c.class_name 
            FROM students s 
            LEFT JOIN classes c ON s.class_id = c.id 
            WHERE s.id = ?
        ''', (test_data['id'],))
        
        result = cursor.fetchone()
        if result:
            result_dict = dict(result)
            print(f"查询结果: {result_dict}")
        else:
            print("未找到记录")
        
        # 清理测试数据
        cursor.execute('DELETE FROM students WHERE id = ?', (test_data['id'],))
        print("清理测试数据完成")
        
        conn.commit()
        conn.close()
        
        print("所有数据库操作测试成功！")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database_operations()
