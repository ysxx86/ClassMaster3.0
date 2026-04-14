#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
权限检查逻辑更新示例
用于迁移后的数据库结构，提供基于班级ID的权限检查
"""

import sqlite3
import logging
from flask_login import current_user
from flask import jsonify

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库路径
DATABASE = 'students.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

# 权限检查通用函数
def check_student_access(student_id):
    """
    检查当前用户是否有权限访问指定学生
    
    Args:
        student_id: 学生ID
        
    Returns:
        bool: 是否有访问权限
    """
    # 管理员可以访问所有学生
    if current_user.is_admin:
        return True
    
    # 获取学生的班级ID
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT class_id FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    
    if not student:
        return False
    
    # 班主任只能访问自己班级的学生
    student_class_id = student['class_id']
    teacher_class_id = current_user.class_id
    
    # 记录详细的权限检查日志
    logger.info(f"权限检查: 用户={current_user.username}, 学生ID={student_id}, "
               f"学生班级ID={student_class_id}, 班主任班级ID={teacher_class_id}")
    
    # 检查班级ID是否匹配
    return student_class_id == teacher_class_id

# 应用于get_student API
def get_student_with_permission_check(student_id):
    """
    获取单个学生API的实现，包含权限检查
    
    Args:
        student_id: 学生ID
        
    Returns:
        Response: API响应
    """
    # 获取数据库连接
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查询学生信息
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    # 如果学生不存在，直接返回404
    if not student:
        conn.close()
        return jsonify({'status': 'error', 'message': '未找到学生'}), 404
    
    # 权限检查：管理员可以查看所有学生，班主任只能查看自己班级的学生
    if not current_user.is_admin:
        student_class_id = student['class_id']
        if student_class_id != current_user.class_id:
            conn.close()
            logger.warning(f"用户 {current_user.username} (ID: {current_user.id}) "
                          f"尝试访问非本班学生 {student_id}，权限不足")
            return jsonify({'status': 'error', 'message': '权限不足，无法访问非本班学生'}), 403
    
    # 关闭数据库连接
    conn.close()
    
    # 返回学生信息
    return jsonify({
        'status': 'ok',
        'student': dict(student)
    })

# 应用于update_student API
def update_student_with_permission_check(student_id):
    """
    更新学生API的实现，包含权限检查
    
    Args:
        student_id: 学生ID
        
    Returns:
        Response: API响应
    """
    # 示例代码，实际实现根据您的API需求调整
    if not check_student_access(student_id):
        return jsonify({
            'status': 'error', 
            'message': '权限不足，无法修改非本班学生'
        }), 403
    
    # 执行正常的更新逻辑...
    return jsonify({'status': 'ok', 'message': '学生信息已更新'})

# 应用于delete_student API
def delete_student_with_permission_check(student_id):
    """
    删除学生API的实现，包含权限检查
    
    Args:
        student_id: 学生ID
        
    Returns:
        Response: API响应
    """
    # 示例代码，实际实现根据您的API需求调整
    if not check_student_access(student_id):
        return jsonify({
            'status': 'error', 
            'message': '权限不足，无法删除非本班学生'
        }), 403
    
    # 执行正常的删除逻辑...
    return jsonify({'status': 'ok', 'message': '学生已删除'})

# 如何在server.py中应用新的权限检查逻辑
def usage_example():
    """权限检查使用示例"""
    example_code = """
# 在server.py中使用权限检查

# 导入权限检查函数
from auth_update import check_student_access

# 修改获取学生API的实现
@app.route('/api/students/<student_id>', methods=['GET'], strict_slashes=False)
@login_required
def get_student(student_id):
    # 获取数据库连接
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查询学生信息
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    # 如果学生不存在，直接返回404
    if not student:
        conn.close()
        return jsonify({'status': 'error', 'message': '未找到学生'}), 404
    
    # 使用权限检查函数
    if not check_student_access(student_id):
        conn.close()
        logger.warning(f"用户 {current_user.username} (ID: {current_user.id}) 尝试访问非本班学生 {student_id}，权限不足")
        return jsonify({'status': 'error', 'message': '权限不足，无法访问非本班学生'}), 403
    
    # 关闭数据库连接
    conn.close()
    
    # 返回学生信息
    return jsonify({
        'status': 'ok',
        'student': dict(student)
    })
    """
    
    print("\n===== 在server.py中应用权限检查示例 =====")
    print(example_code)
    print("======================================\n")

if __name__ == "__main__":
    print("====== ClassMaster 2.0 权限检查更新示例 ======")
    print("此文件包含基于新数据库结构的权限检查逻辑示例")
    print("您可以参考这些代码更新server.py中的权限检查逻辑")
    
    usage_example() 