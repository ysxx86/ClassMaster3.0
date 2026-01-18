#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
教师信息确认API
"""

import sqlite3
import datetime
import json
import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

# 配置日志
logger = logging.getLogger(__name__)

# 创建蓝图
teacher_info_bp = Blueprint('teacher_info', __name__)

# 配置
DATABASE = 'students.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def get_current_semester_display():
    """获取当前学期的显示文本"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取学年
        cursor.execute("SELECT value FROM system_settings WHERE key = 'school_year'")
        school_year_row = cursor.fetchone()
        school_year = school_year_row['value'] if school_year_row else '2025-2026'
        
        # 获取学期
        cursor.execute("SELECT value FROM system_settings WHERE key = 'semester'")
        semester_row = cursor.fetchone()
        semester = semester_row['value'] if semester_row else '1'
        
        # 组合成显示文本
        semester_text = '第一学期' if semester == '1' else '第二学期'
        return f"{school_year}学年{semester_text}"
    finally:
        conn.close()

# ==================== 教师信息确认API ====================

@teacher_info_bp.route('/api/teacher-info/check-confirmation', methods=['GET'])
@login_required
def check_confirmation():
    """检查教师是否需要确认信息"""
    try:
        # 超级管理员不需要确认
        if current_user.is_admin:
            return jsonify({
                'status': 'ok',
                'need_confirm': False,
                'reason': 'admin'
            })
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取当前系统学期
        current_semester = get_current_semester_display()
        
        # 获取教师信息
        cursor.execute('''
            SELECT 
                info_confirmed,
                last_confirmed_date,
                current_semester
            FROM users
            WHERE id = ?
        ''', (current_user.id,))
        
        user_info = cursor.fetchone()
        conn.close()
        
        if not user_info:
            return jsonify({
                'status': 'error',
                'message': '用户信息不存在'
            }), 404
        
        # 判断是否需要确认
        need_confirm = False
        reason = ''
        
        # 情况1：从未确认过
        if not user_info['info_confirmed']:
            need_confirm = True
            reason = 'never_confirmed'
        
        # 情况2：学期变更
        elif user_info['current_semester'] != current_semester:
            need_confirm = True
            reason = 'semester_changed'
        
        # 情况3：距离上次确认超过90天（可选）
        elif user_info['last_confirmed_date']:
            last_date = datetime.datetime.strptime(user_info['last_confirmed_date'], '%Y-%m-%d %H:%M:%S')
            days_since = (datetime.datetime.now() - last_date).days
            if days_since > 90:
                need_confirm = True
                reason = 'long_time_no_confirm'
        
        return jsonify({
            'status': 'ok',
            'need_confirm': need_confirm,
            'reason': reason,
            'current_semester': current_semester,
            'last_confirmed_date': user_info['last_confirmed_date']
        })
        
    except Exception as e:
        logger.error(f"检查确认状态失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'检查失败: {str(e)}'
        }), 500

@teacher_info_bp.route('/api/teacher-info/my-info', methods=['GET'])
@login_required
def get_my_info():
    """获取当前教师的任教信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取基本信息
        cursor.execute('''
            SELECT 
                u.id,
                u.username,
                u.primary_role,
                u.class_id,
                c.class_name,
                u.info_confirmed,
                u.last_confirmed_date,
                u.current_semester
            FROM users u
            LEFT JOIN classes c ON u.class_id = c.id
            WHERE u.id = ?
        ''', (current_user.id,))
        
        user_info = cursor.fetchone()
        
        if not user_info:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '用户信息不存在'
            }), 404
        
        # 获取任教学科（从teacher_subjects表）
        cursor.execute('''
            SELECT s.id, s.name
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            WHERE ts.teacher_id = ?
            ORDER BY s.name
        ''', (current_user.id,))
        
        subjects = [{'id': row['id'], 'name': row['name']} for row in cursor.fetchall()]
        
        # 获取学科班级分配（从teaching_assignments表）
        cursor.execute('''
            SELECT 
                ta.id,
                ta.class_id,
                c.class_name,
                ta.subject
            FROM teaching_assignments ta
            JOIN classes c ON CAST(ta.class_id AS INTEGER) = c.id
            WHERE ta.teacher_id = ?
            ORDER BY c.class_name, ta.subject
        ''', (current_user.id,))
        
        assignments = []
        for row in cursor.fetchall():
            assignments.append({
                'id': row['id'],
                'class_id': row['class_id'],
                'class_name': row['class_name'],
                'subject': row['subject']
            })
        
        # 获取当前系统学期
        current_semester = get_current_semester_display()
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'info': {
                'id': user_info['id'],
                'username': user_info['username'],
                'role': user_info['primary_role'] or '科任老师',
                'class_id': user_info['class_id'],
                'class_name': user_info['class_name'],
                'subjects': subjects,
                'assignments': assignments,
                'info_confirmed': bool(user_info['info_confirmed']),
                'last_confirmed_date': user_info['last_confirmed_date'],
                'teacher_semester': user_info['current_semester'],
                'system_semester': current_semester
            }
        })
        
    except Exception as e:
        logger.error(f"获取教师信息失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取失败: {str(e)}'
        }), 500

@teacher_info_bp.route('/api/teacher-info/confirm', methods=['POST'])
@login_required
def confirm_info():
    """确认教师信息"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取当前系统学期
        current_semester = get_current_semester_display()
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 更新确认状态
        cursor.execute('''
            UPDATE users
            SET info_confirmed = 1,
                last_confirmed_date = ?,
                current_semester = ?
            WHERE id = ?
        ''', (now, current_semester, current_user.id))
        
        # 记录历史
        cursor.execute('''
            INSERT INTO teacher_info_history 
            (teacher_id, action, action_type, new_data, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            current_user.id,
            '确认任教信息',
            'confirm',
            json.dumps(data.get('info', {}), ensure_ascii=False),
            request.remote_addr,
            now
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"教师 {current_user.username} 确认了任教信息")
        
        return jsonify({
            'status': 'ok',
            'message': '确认成功'
        })
        
    except Exception as e:
        logger.error(f"确认信息失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'确认失败: {str(e)}'
        }), 500

@teacher_info_bp.route('/api/teacher-info/mark-viewed', methods=['POST'])
@login_required
def mark_viewed():
    """标记为已查看（不修改也算已查看）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取当前系统学期
        current_semester = get_current_semester_display()
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 更新确认状态
        cursor.execute('''
            UPDATE users
            SET info_confirmed = 1,
                last_confirmed_date = ?,
                current_semester = ?
            WHERE id = ?
        ''', (now, current_semester, current_user.id))
        
        # 记录历史
        cursor.execute('''
            INSERT INTO teacher_info_history 
            (teacher_id, action, action_type, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            current_user.id,
            '查看任教信息',
            'view',
            request.remote_addr,
            now
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"教师 {current_user.username} 查看了任教信息")
        
        return jsonify({
            'status': 'ok',
            'message': '已标记为已查看'
        })
        
    except Exception as e:
        logger.error(f"标记失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'标记失败: {str(e)}'
        }), 500

@teacher_info_bp.route('/api/teacher-info/update', methods=['POST'])
@login_required
def update_info():
    """更新教师任教信息"""
    try:
        data = request.get_json()
        subjects = data.get('subjects', [])  # 学科ID列表
        assignments = data.get('assignments', [])  # [{class_id, subject_name}]
        
        logger.info(f"教师 {current_user.username} 请求更新任教信息")
        logger.info(f"学科IDs: {subjects}")
        logger.info(f"班级分配: {assignments}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取旧数据用于记录历史
        cursor.execute('''
            SELECT s.name
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            WHERE ts.teacher_id = ?
        ''', (current_user.id,))
        old_subjects = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT class_id, subject
            FROM teaching_assignments
            WHERE teacher_id = ?
        ''', (current_user.id,))
        old_assignments = [{'class_id': row['class_id'], 'subject': row['subject']} 
                          for row in cursor.fetchall()]
        
        logger.info(f"旧学科: {old_subjects}")
        logger.info(f"旧分配: {old_assignments}")
        
        # 1. 更新任教学科（teacher_subjects表）
        # 删除旧的
        cursor.execute('DELETE FROM teacher_subjects WHERE teacher_id = ?', (current_user.id,))
        
        # 添加新的
        for subject_id in subjects:
            cursor.execute('''
                INSERT INTO teacher_subjects (teacher_id, subject_id)
                VALUES (?, ?)
            ''', (current_user.id, subject_id))
            logger.info(f"添加学科: teacher_id={current_user.id}, subject_id={subject_id}")
        
        # 2. 更新学科班级分配（teaching_assignments表）
        # 删除旧的
        cursor.execute('DELETE FROM teaching_assignments WHERE teacher_id = ?', (current_user.id,))
        
        # 添加新的
        for assignment in assignments:
            class_id = str(assignment['class_id'])
            subject_name = assignment['subject_name']
            cursor.execute('''
                INSERT INTO teaching_assignments (teacher_id, class_id, subject)
                VALUES (?, ?, ?)
            ''', (current_user.id, class_id, subject_name))
            logger.info(f"添加分配: teacher_id={current_user.id}, class_id={class_id}, subject={subject_name}")
        
        # 3. 记录修改历史
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO teacher_info_history 
            (teacher_id, action, action_type, old_data, new_data, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_user.id,
            '修改任教信息',
            'update',
            json.dumps({'subjects': old_subjects, 'assignments': old_assignments}, ensure_ascii=False),
            json.dumps({'subjects': subjects, 'assignments': assignments}, ensure_ascii=False),
            request.remote_addr,
            now
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"教师 {current_user.username} 更新任教信息成功")
        
        return jsonify({
            'status': 'ok',
            'message': '更新成功'
        })
        
    except Exception as e:
        logger.error(f"更新信息失败: {e}")
        if conn:
            conn.rollback()
        return jsonify({
            'status': 'error',
            'message': f'更新失败: {str(e)}'
        }), 500

@teacher_info_bp.route('/api/teacher-info/history', methods=['GET'])
@login_required
def get_history():
    """获取教师信息修改历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                action,
                action_type,
                old_data,
                new_data,
                created_at
            FROM teacher_info_history
            WHERE teacher_id = ?
            ORDER BY created_at DESC
            LIMIT 20
        ''', (current_user.id,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'id': row['id'],
                'action': row['action'],
                'action_type': row['action_type'],
                'old_data': row['old_data'],
                'new_data': row['new_data'],
                'created_at': row['created_at']
            })
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'history': history
        })
        
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取失败: {str(e)}'
        }), 500

# ==================== 管理员API ====================

@teacher_info_bp.route('/api/teacher-info/admin/stats', methods=['GET'])
@login_required
def get_admin_stats():
    """获取教师信息确认统计（管理员）"""
    if not current_user.is_admin:
        return jsonify({
            'status': 'error',
            'message': '权限不足'
        }), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 总教师数
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = 0")
        total = cursor.fetchone()['count']
        
        # 已确认数
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = 0 AND info_confirmed = 1")
        confirmed = cursor.fetchone()['count']
        
        # 未确认列表
        cursor.execute('''
            SELECT id, username, primary_role, last_confirmed_date
            FROM users
            WHERE is_admin = 0 AND (info_confirmed = 0 OR info_confirmed IS NULL)
            ORDER BY username
        ''')
        
        unconfirmed = []
        for row in cursor.fetchall():
            unconfirmed.append({
                'id': row['id'],
                'username': row['username'],
                'role': row['primary_role'] or '科任老师',
                'last_confirmed_date': row['last_confirmed_date']
            })
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'stats': {
                'total': total,
                'confirmed': confirmed,
                'unconfirmed': total - confirmed,
                'unconfirmed_list': unconfirmed
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取失败: {str(e)}'
        }), 500
