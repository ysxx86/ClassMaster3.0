#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import traceback
import datetime
import re
from functools import wraps
from flask import Blueprint, request, jsonify, session
import logging

logger = logging.getLogger(__name__)

parent_bp = Blueprint('parent', __name__)

DATABASE = 'students.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_parent(app):
    logger.info("初始化家长端模块")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("家长端模块初始化完成")


def parent_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'parent_student_id' not in session:
            return jsonify({'status': 'error', 'message': '请先验证身份', 'code': 'UNAUTHORIZED'}), 401
        return f(*args, **kwargs)
    return decorated_function


@parent_bp.route('/api/parent/grades', methods=['GET'])
def get_grades():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT class_name FROM classes')
        rows = cursor.fetchall()
        conn.close()

        grade_set = set()
        for row in rows:
            match = re.search(r'([\u4e00-\u9fa5]+年级)', row['class_name'])
            if match:
                grade_set.add(match.group(1))

        grades = sorted(list(grade_set))
        return jsonify({'status': 'ok', 'grades': grades})
    except Exception as e:
        logger.error(f'获取年级列表时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'获取年级列表失败: {str(e)}'}), 500


@parent_bp.route('/api/parent/classes', methods=['GET'])
def get_classes():
    try:
        grade = request.args.get('grade', '')
        if not grade:
            return jsonify({'status': 'error', 'message': '请提供年级参数'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, class_name FROM classes WHERE class_name LIKE ?', (f'%{grade}%',))
        rows = cursor.fetchall()
        conn.close()

        classes = [{'id': row['id'], 'class_name': row['class_name']} for row in rows]
        return jsonify({'status': 'ok', 'classes': classes})
    except Exception as e:
        logger.error(f'获取班级列表时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'获取班级列表失败: {str(e)}'}), 500


@parent_bp.route('/api/parent/verify', methods=['POST'])
def verify():
    try:
        data = request.get_json()
        grade = data.get('grade', '')
        class_id = data.get('class_id', '')
        student_name = data.get('student_name', '')

        if not grade or not class_id or not student_name:
            return jsonify({'status': 'error', 'message': '请提供完整的验证信息'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT s.id, s.name, s.gender, s.class_id, c.class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.class_id = ? AND s.name = ?
        ''', (class_id, student_name))
        student = cursor.fetchone()

        if not student:
            conn.close()
            return jsonify({'status': 'error', 'message': '未找到匹配的学生信息'}), 404

        if grade not in (student['class_name'] or ''):
            conn.close()
            return jsonify({'status': 'error', 'message': '未找到匹配的学生信息'}), 404

        session['parent_student_id'] = student['id']
        session['parent_student_name'] = student['name']

        conn.close()
        return jsonify({
            'status': 'ok',
            'student': {
                'id': student['id'],
                'name': student['name'],
                'gender': student['gender'],
                'class_id': student['class_id'],
                'class_name': student['class_name']
            }
        })
    except Exception as e:
        logger.error(f'验证学生身份时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'验证学生身份失败: {str(e)}'}), 500


@parent_bp.route('/api/parent/student-info', methods=['GET'])
@parent_login_required
def get_student_info():
    try:
        student_id = session.get('parent_student_id')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT name, gender, class_id, comments, pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo,
                   yuwen, shuxue, yingyu, daof, kexue, zonghe, tiyu, yinyue, meishu, laodong, xinxi, shufa, xinli
            FROM students WHERE id = ?
        ''', (student_id,))
        student = cursor.fetchone()

        if not student:
            conn.close()
            return jsonify({'status': 'error', 'message': '未找到学生信息'}), 404

        cursor.execute('SELECT class_name FROM classes WHERE id = ?', (student['class_id'],))
        class_row = cursor.fetchone()
        class_name = class_row['class_name'] if class_row else ''
        conn.close()

        deyu_map = {
            'pinzhi': '品质',
            'xuexi': '学习',
            'jiankang': '健康',
            'shenmei': '审美',
            'shijian': '实践',
            'shenghuo': '生活'
        }

        score_map = {
            'yuwen': '语文',
            'shuxue': '数学',
            'yingyu': '英语',
            'daof': '道法',
            'kexue': '科学',
            'zonghe': '综合',
            'tiyu': '体育',
            'yinyue': '音乐',
            'meishu': '美术',
            'laodong': '劳动',
            'xinxi': '信息',
            'shufa': '书法',
            'xinli': '心理'
        }

        deyu = {}
        for field, label in deyu_map.items():
            deyu[label] = student[field] if student[field] is not None else 0

        scores = {}
        for field, label in score_map.items():
            scores[label] = student[field] if student[field] is not None else ''

        return jsonify({
            'status': 'ok',
            'student': {
                'id': student_id,
                'name': student['name'],
                'gender': student['gender'],
                'class_id': student['class_id'],
                'class_name': class_name,
                'comments': student['comments'] or '',
                'deyu': deyu,
                'scores': scores
            }
        })
    except Exception as e:
        logger.error(f'获取学生信息时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'获取学生信息失败: {str(e)}'}), 500


@parent_bp.route('/api/parent/student-history-grades', methods=['GET'])
@parent_login_required
def get_student_history_grades():
    try:
        student_id = session.get('parent_student_id')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT es.subject, es.score, e.exam_name, e.exam_date
            FROM exam_scores es
            JOIN exams e ON es.exam_id = e.id
            WHERE es.student_id = ?
            ORDER BY e.exam_date DESC
        ''', (student_id,))
        rows = cursor.fetchall()
        conn.close()

        subject_map = {
            'yuwen': '语文',
            'shuxue': '数学',
            'yingyu': '英语',
            'daof': '道法',
            'kexue': '科学',
            'zonghe': '综合',
            'tiyu': '体育',
            'yinyue': '音乐',
            'meishu': '美术',
            'laodong': '劳动',
            'xinxi': '信息',
            'shufa': '书法',
            'xinli': '心理'
        }

        history = []
        for row in rows:
            subject_display = subject_map.get(row['subject'], row['subject'])
            history.append({
                'exam_name': row['exam_name'],
                'exam_date': row['exam_date'],
                'subject': subject_display,
                'score': row['score']
            })

        return jsonify({'status': 'ok', 'history': history})
    except Exception as e:
        logger.error(f'获取历史成绩时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'获取历史成绩失败: {str(e)}'}), 500


@parent_bp.route('/api/parent/messages', methods=['GET'])
@parent_login_required
def get_messages():
    try:
        student_id = session.get('parent_student_id')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, student_id, content, created_at, updated_at FROM parent_messages WHERE student_id = ? ORDER BY created_at DESC',
            (student_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        messages = [dict(row) for row in rows]
        return jsonify({'status': 'ok', 'messages': messages})
    except Exception as e:
        logger.error(f'获取寄语列表时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'获取寄语列表失败: {str(e)}'}), 500


@parent_bp.route('/api/parent/messages', methods=['POST'])
@parent_login_required
def create_message():
    try:
        data = request.get_json()
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'status': 'error', 'message': '寄语内容不能为空'}), 400

        if len(content) > 200:
            return jsonify({'status': 'error', 'message': '寄语内容不能超过200字'}), 400

        student_id = session.get('parent_student_id')
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO parent_messages (student_id, content, created_at, updated_at) VALUES (?, ?, ?, ?)',
            (student_id, content, now, now)
        )
        conn.commit()
        conn.close()

        return jsonify({'status': 'ok', 'message': '寄语提交成功'})
    except Exception as e:
        logger.error(f'提交寄语时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'提交寄语失败: {str(e)}'}), 500


@parent_bp.route('/api/parent/messages/<int:message_id>', methods=['PUT'])
@parent_login_required
def update_message(message_id):
    try:
        data = request.get_json()
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'status': 'error', 'message': '寄语内容不能为空'}), 400

        if len(content) > 200:
            return jsonify({'status': 'error', 'message': '寄语内容不能超过200字'}), 400

        student_id = session.get('parent_student_id')
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT student_id FROM parent_messages WHERE id = ?', (message_id,))
        msg = cursor.fetchone()

        if not msg:
            conn.close()
            return jsonify({'status': 'error', 'message': '寄语不存在'}), 404

        if msg['student_id'] != student_id:
            conn.close()
            return jsonify({'status': 'error', 'message': '无权修改此寄语'}), 403

        cursor.execute(
            'UPDATE parent_messages SET content = ?, updated_at = ? WHERE id = ?',
            (content, now, message_id)
        )
        conn.commit()
        conn.close()

        return jsonify({'status': 'ok', 'message': '寄语修改成功'})
    except Exception as e:
        logger.error(f'修改寄语时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'修改寄语失败: {str(e)}'}), 500


@parent_bp.route('/api/parent/messages/<int:message_id>', methods=['DELETE'])
@parent_login_required
def delete_message(message_id):
    try:
        student_id = session.get('parent_student_id')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT student_id FROM parent_messages WHERE id = ?', (message_id,))
        msg = cursor.fetchone()

        if not msg:
            conn.close()
            return jsonify({'status': 'error', 'message': '寄语不存在'}), 404

        if msg['student_id'] != student_id:
            conn.close()
            return jsonify({'status': 'error', 'message': '无权删除此寄语'}), 403

        cursor.execute('DELETE FROM parent_messages WHERE id = ?', (message_id,))
        conn.commit()
        conn.close()

        return jsonify({'status': 'ok', 'message': '寄语删除成功'})
    except Exception as e:
        logger.error(f'删除寄语时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'删除寄语失败: {str(e)}'}), 500


@parent_bp.route('/api/parent/logout', methods=['POST'])
def logout():
    session.pop('parent_student_id', None)
    session.pop('parent_student_name', None)
    return jsonify({'status': 'ok', 'message': '已退出'})
