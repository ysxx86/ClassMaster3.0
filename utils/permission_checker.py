#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
权限检查工具
用于验证用户是否有权限访问特定功能和数据
"""

import sqlite3
from functools import wraps
from flask import jsonify
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

DATABASE = 'students.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_subjects(user_id):
    """获取用户任教的学科列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.name 
            FROM subjects s
            JOIN teacher_subjects ts ON s.id = ts.subject_id
            WHERE ts.teacher_id = ?
        ''', (user_id,))
        subjects = cursor.fetchall()
        conn.close()
        return [{'id': s['id'], 'name': s['name']} for s in subjects]
    except Exception as e:
        logger.error(f"获取用户任教学科失败: {str(e)}")
        return []

def is_super_admin(user):
    """检查是否是超级管理员"""
    return user.is_admin if hasattr(user, 'is_admin') else False

def is_head_teacher(user):
    """检查是否是正班主任"""
    role = getattr(user, 'primary_role', None)
    return role == '正班主任'

def is_vice_teacher(user):
    """检查是否是副班主任"""
    role = getattr(user, 'primary_role', None)
    return role == '副班主任'

def is_subject_teacher(user):
    """检查是否是科任老师"""
    role = getattr(user, 'primary_role', None)
    return role == '科任老师'

def is_admin_staff(user):
    """检查是否是行政"""
    role = getattr(user, 'primary_role', None)
    return role == '行政'

def is_school_leader(user):
    """检查是否是校级领导"""
    role = getattr(user, 'primary_role', None)
    return role == '校级领导'

def can_access_students(user, target_class_id=None):
    """
    检查是否有权限访问学生管理
    
    Args:
        user: 当前用户对象
        target_class_id: 目标班级ID（可选）
    
    Returns:
        bool: 是否有权限
    """
    # 超级管理员可以访问所有学生
    if is_super_admin(user):
        return True
    
    # 正班主任可以访问自己班级的学生
    if is_head_teacher(user):
        if target_class_id is None:
            return True  # 可以访问学生管理页面
        return str(user.class_id) == str(target_class_id)
    
    return False

def can_edit_grade(user, target_class_id, target_subject):
    """
    检查是否有权限编辑成绩
    
    Args:
        user: 当前用户对象
        target_class_id: 目标班级ID
        target_subject: 目标学科名称
    
    Returns:
        bool: 是否有权限
    """
    # 超级管理员可以编辑所有成绩
    if is_super_admin(user):
        return True
    
    # 正班主任可以编辑自己班级的所有成绩
    if is_head_teacher(user) and str(user.class_id) == str(target_class_id):
        return True
    
    # 其他角色只能编辑自己任教学科的成绩
    user_subjects = get_user_subjects(user.id)
    subject_names = [s['name'] for s in user_subjects]
    
    return target_subject in subject_names

def can_access_deyu(user, target_class_id=None):
    """
    检查是否有权限访问德育管理
    
    Args:
        user: 当前用户对象
        target_class_id: 目标班级ID（可选）
    
    Returns:
        bool: 是否有权限
    """
    # 超级管理员可以访问所有德育数据
    if is_super_admin(user):
        return True
    
    # 正班主任可以访问自己班级的德育数据
    if is_head_teacher(user):
        if target_class_id is None:
            return True
        return str(user.class_id) == str(target_class_id)
    
    return False

def can_access_comments(user, target_class_id=None):
    """
    检查是否有权限访问评语管理
    
    Args:
        user: 当前用户对象
        target_class_id: 目标班级ID（可选）
    
    Returns:
        bool: 是否有权限
    """
    # 超级管理员可以访问所有评语
    if is_super_admin(user):
        return True
    
    # 正班主任可以访问自己班级的评语
    if is_head_teacher(user):
        if target_class_id is None:
            return True
        return str(user.class_id) == str(target_class_id)
    
    return False

def can_access_grade_analysis(user):
    """
    检查是否有权限访问成绩分析
    所有教师都可以访问
    
    Args:
        user: 当前用户对象
    
    Returns:
        bool: 是否有权限
    """
    return True  # 所有教师都可以访问成绩分析

def can_access_performance(user):
    """
    检查是否有权限访问班主任考核
    只有超级管理员、行政、校级领导可以访问
    
    Args:
        user: 当前用户对象
    
    Returns:
        bool: 是否有权限
    """
    return is_super_admin(user) or is_admin_staff(user) or is_school_leader(user)

def can_export_report(user, target_class_id=None):
    """
    检查是否有权限导出报告
    
    Args:
        user: 当前用户对象
        target_class_id: 目标班级ID（可选）
    
    Returns:
        bool: 是否有权限
    """
    # 超级管理员可以导出所有报告
    if is_super_admin(user):
        return True
    
    # 正班主任可以导出自己班级的报告
    if is_head_teacher(user):
        if target_class_id is None:
            return True
        return str(user.class_id) == str(target_class_id)
    
    return False

def can_access_admin_panel(user):
    """
    检查是否有权限访问管理后台
    只有超级管理员可以访问
    
    Args:
        user: 当前用户对象
    
    Returns:
        bool: 是否有权限
    """
    return is_super_admin(user)

def get_accessible_classes(user):
    """
    获取用户有权限访问的班级列表
    
    Args:
        user: 当前用户对象
    
    Returns:
        list: 班级ID列表
    """
    # 超级管理员可以访问所有班级
    if is_super_admin(user):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM classes')
            classes = cursor.fetchall()
            conn.close()
            return [c['id'] for c in classes]
        except Exception as e:
            logger.error(f"获取所有班级失败: {str(e)}")
            return []
    
    # 正班主任只能访问自己的班级
    if is_head_teacher(user) and user.class_id:
        return [user.class_id]
    
    # 其他角色不能访问班级
    return []

def get_editable_subjects(user, class_id=None):
    """
    获取用户可以编辑成绩的学科列表
    
    Args:
        user: 当前用户对象
        class_id: 班级ID（可选）
    
    Returns:
        list: 学科名称列表
    """
    # 超级管理员可以编辑所有学科
    if is_super_admin(user):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM subjects')
            subjects = cursor.fetchall()
            conn.close()
            return [s['name'] for s in subjects]
        except Exception as e:
            logger.error(f"获取所有学科失败: {str(e)}")
            return []
    
    # 正班主任可以编辑自己班级的所有学科
    # 注意：正班主任在成绩管理页面只能看到自己的班级，所以这里不需要检查class_id
    if is_head_teacher(user):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM subjects')
            subjects = cursor.fetchall()
            conn.close()
            return [s['name'] for s in subjects]
        except Exception as e:
            logger.error(f"获取所有学科失败: {str(e)}")
            return []
    
    # 其他角色只能编辑自己任教的学科
    user_subjects = get_user_subjects(user.id)
    return [s['name'] for s in user_subjects]

# 装饰器：要求超级管理员权限
def require_admin(f):
    """装饰器：要求超级管理员权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': '请先登录'}), 401
        
        if not is_super_admin(current_user):
            return jsonify({'status': 'error', 'message': '只有超级管理员可以访问此功能'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# 装饰器：要求班主任权限
def require_head_teacher(f):
    """装饰器：要求正班主任权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': '请先登录'}), 401
        
        if not (is_super_admin(current_user) or is_head_teacher(current_user)):
            return jsonify({'status': 'error', 'message': '只有超级管理员或正班主任可以访问此功能'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# 装饰器：要求班主任考核权限
def require_performance_access(f):
    """装饰器：要求班主任考核访问权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': '请先登录'}), 401
        
        if not can_access_performance(current_user):
            return jsonify({'status': 'error', 'message': '只有超级管理员、行政或校级领导可以访问班主任考核'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def get_user_permissions(user):
    """
    获取用户的所有权限信息
    
    Args:
        user: 当前用户对象
    
    Returns:
        dict: 权限信息字典
    """
    role = getattr(user, 'primary_role', '科任老师')
    
    permissions = {
        'role': role,
        'is_admin': is_super_admin(user),
        'class_id': getattr(user, 'class_id', None),
        'subjects': get_user_subjects(user.id),
        'can_access': {
            'students': can_access_students(user),
            'grades': True,  # 所有人都能访问成绩管理（但编辑权限不同）
            'deyu': can_access_deyu(user),
            'comments': can_access_comments(user),
            'grade_analysis': can_access_grade_analysis(user),
            'performance': can_access_performance(user),
            'export': can_export_report(user),
            'admin_panel': can_access_admin_panel(user)
        },
        'accessible_classes': get_accessible_classes(user),
        'editable_subjects': get_editable_subjects(user)
    }
    
    return permissions
