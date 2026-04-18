#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
权限检查工具
用于验证用户是否有权限访问特定功能和数据
"""

from functools import wraps
from flask import jsonify
from flask_login import current_user
import logging
from utils.db import get_db_connection, DATABASE

logger = logging.getLogger(__name__)

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
    
    # 副班主任可以访问自己班级的学生
    if is_vice_teacher(user):
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
    
    # 其他角色：必须精确匹配班级和学科（从 teaching_assignments 表）
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM teaching_assignments
            WHERE teacher_id = ? AND class_id = ? AND subject = ?
        ''', (user.id, str(target_class_id), target_subject))
        result = cursor.fetchone()
        conn.close()
        return result['count'] > 0
    except Exception as e:
        logger.error(f"检查编辑权限失败: {str(e)}")
        return False

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
    
    # 副班主任：优先返回自己的班级，如果还有任教其他班级，也一并返回
    if is_vice_teacher(user):
        accessible = []
        # 添加自己的班级
        if user.class_id:
            accessible.append(user.class_id)
        # 添加任教的其他班级
        teaching_classes = get_teaching_classes(user.id)
        for class_id in teaching_classes:
            if class_id not in accessible:
                accessible.append(class_id)
        return accessible if accessible else []
    
    # 其他角色（科任老师、行政、校级领导）从 teaching_assignments 表获取任教的班级
    return get_teaching_classes(user.id)

def get_teaching_classes(user_id):
    """
    获取教师任教的班级列表（从 teaching_assignments 表）
    
    Args:
        user_id: 用户ID
    
    Returns:
        list: 班级ID列表（去重）
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT class_id 
            FROM teaching_assignments 
            WHERE teacher_id = ?
            ORDER BY class_id
        ''', (user_id,))
        classes = cursor.fetchall()
        conn.close()
        # class_id 在 teaching_assignments 表中是 TEXT 类型，需要转换为整数
        return [int(c['class_id']) for c in classes if c['class_id']]
    except Exception as e:
        logger.error(f"获取教师任教班级失败: {str(e)}")
        return []

def get_editable_subjects(user, class_id=None):
    """
    获取用户可以编辑成绩的学科列表
    
    Args:
        user: 当前用户对象
        class_id: 班级ID（必需，用于精确匹配）
    
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
    if is_head_teacher(user) and str(user.class_id) == str(class_id):
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
    
    # 其他角色：从 teaching_assignments 表获取该班级的任教学科
    if not class_id:
        return []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT subject
            FROM teaching_assignments
            WHERE teacher_id = ? AND class_id = ?
        ''', (user.id, str(class_id)))
        subjects = cursor.fetchall()
        conn.close()
        return [s['subject'] for s in subjects]
    except Exception as e:
        logger.error(f"获取任教学科失败: {str(e)}")
        return []

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
    
    # 获取教师的任教信息（班级-学科映射）
    teaching_map = {}
    if not is_super_admin(user):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT class_id, subject
                FROM teaching_assignments
                WHERE teacher_id = ?
            ''', (user.id,))
            assignments = cursor.fetchall()
            conn.close()
            
            # 构建映射：{class_id: [subject1, subject2, ...]}
            for assignment in assignments:
                class_id = assignment['class_id']
                subject = assignment['subject']
                if class_id not in teaching_map:
                    teaching_map[class_id] = []
                teaching_map[class_id].append(subject)
        except Exception as e:
            logger.error(f"获取任教信息失败: {str(e)}")
    
    permissions = {
        'role': role,
        'is_admin': is_super_admin(user),
        'class_id': getattr(user, 'class_id', None),
        'subjects': get_user_subjects(user.id),
        'teaching_map': teaching_map,  # 新增：班级-学科映射
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
