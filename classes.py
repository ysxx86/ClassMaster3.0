#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
班级管理模块，包含班级相关的API路由和功能
"""

import os
import sqlite3
import traceback
import datetime
import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

# 配置日志
logger = logging.getLogger(__name__)

# 班级蓝图
classes_bp = Blueprint('classes', __name__)

# 配置
DATABASE = 'students.db'

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

# 初始化班级表
def init_classes():
    """初始化班级表，如果不存在则创建"""
    logger.info("初始化班级表")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建班级表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS classes (
        id TEXT PRIMARY KEY,
        class_name TEXT NOT NULL UNIQUE,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    
    # 提交并关闭连接
    conn.commit()
    conn.close()
    
    logger.info("班级表初始化完成")

# 预览批量创建班级
@classes_bp.route('/api/classes/preview', methods=['POST'])
@login_required
def preview_classes():
    """预览批量创建班级，检查哪些已存在"""
    # 只有管理员可以创建班级
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '没有权限创建班级'}), 403
    
    # 获取请求数据
    data = request.json
    if not data or 'class_names' not in data:
        return jsonify({'status': 'error', 'message': '请提供班级名称列表'}), 400
    
    class_names = data.get('class_names', [])
    if not class_names:
        return jsonify({'status': 'error', 'message': '班级名称列表为空'}), 400
    
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取现有班级列表
        cursor.execute('SELECT class_name FROM classes')
        existing_classes = set(row[0] for row in cursor.fetchall())
        
        # 准备预览数据
        preview_data = []
        new_count = 0
        exist_count = 0
        
        # 检查每个班级
        for class_name in class_names:
            class_name = class_name.strip()
            if not class_name:  # 跳过空名称
                continue
                
            if class_name in existing_classes:
                status = '已存在'
                note = '该班级已经存在，将被跳过'
                exist_count += 1
            else:
                status = '新建'
                note = '将创建该班级'
                new_count += 1
                
            preview_data.append({
                'class_name': class_name,
                'status': status,
                'note': note
            })
        
        conn.close()
        
        # 返回预览结果
        return jsonify({
            'status': 'ok',
            'message': f'找到 {len(preview_data)} 个班级，将创建 {new_count} 个新班级，跳过 {exist_count} 个已存在的班级。',
            'preview': preview_data,
            'stats': {
                'total': len(preview_data),
                'new': new_count,
                'existing': exist_count
            }
        })
        
    except Exception as e:
        logger.error(f"预览创建班级时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'预览失败: {str(e)}'}), 500

# 确认批量创建班级
@classes_bp.route('/api/classes/create', methods=['POST'])
@login_required
def create_classes():
    """批量创建班级，跳过已存在的班级"""
    # 只有管理员可以创建班级
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '没有权限创建班级'}), 403
    
    # 获取请求数据
    data = request.json
    if not data or 'class_names' not in data:
        return jsonify({'status': 'error', 'message': '请提供班级名称列表'}), 400
    
    class_names = data.get('class_names', [])
    if not class_names:
        return jsonify({'status': 'error', 'message': '班级名称列表为空'}), 400
    
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取现有班级列表
        cursor.execute('SELECT class_name FROM classes')
        existing_classes = set(row[0] for row in cursor.fetchall())
        
        # 获取当前最大ID
        cursor.execute('SELECT MAX(CAST(id AS INTEGER)) FROM classes')
        max_id = cursor.fetchone()[0]
        current_id = int(max_id) if max_id else 0
        
        # 准备创建结果
        created_classes = []
        skipped_classes = []
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 创建每个班级
        for class_name in class_names:
            class_name = class_name.strip()
            if not class_name:  # 跳过空名称
                continue
                
            if class_name in existing_classes:
                # 跳过已存在的班级
                skipped_classes.append({
                    'class_name': class_name,
                    'reason': '已存在'
                })
                continue
            
            # 生成ID并创建班级
            current_id += 1
            new_id = str(current_id)
            
            cursor.execute('''
            INSERT INTO classes (id, class_name, created_at, updated_at) 
            VALUES (?, ?, ?, ?)
            ''', (new_id, class_name, now, now))
            
            created_classes.append({
                'id': new_id,
                'class_name': class_name,
                'created_at': now
            })
            
            # 添加到已存在集合，防止同一批次重复创建
            existing_classes.add(class_name)
        
        # 提交事务
        conn.commit()
        conn.close()
        
        logger.info(f"批量创建班级成功，创建: {len(created_classes)}，跳过: {len(skipped_classes)}")
        
        return jsonify({
            'status': 'ok',
            'message': f'成功创建 {len(created_classes)} 个班级，跳过 {len(skipped_classes)} 个已存在的班级。',
            'created': created_classes,
            'skipped': skipped_classes
        })
        
    except Exception as e:
        logger.error(f"创建班级时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'创建失败: {str(e)}'}), 500

# 获取所有班级
@classes_bp.route('/api/classes', methods=['GET'])
@login_required
def get_classes():
    """获取所有班级列表"""
    try:
        logger.info("=== CLASSES BLUEPRINT: 接收到获取班级列表请求 ===")
        # 建立数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询班级基本信息
        cursor.execute('''
            SELECT id, class_name, created_at, updated_at 
            FROM classes 
            ORDER BY class_name
        ''')
        classes_data = cursor.fetchall()
        logger.info(f"从数据库获取到 {len(classes_data)} 个班级")
        
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
                logger.error(f"查询班级 {class_id} 班主任信息时出错: {str(e)}")
            
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
                logger.error(f"查询班级 {class_id} 学生数量时出错: {str(e)}")
            
            classes.append(class_info)
        
        conn.close()
        
        # 记录返回的班级数量
        logger.info(f"获取到 {len(classes)} 个班级，准备返回")
        
        return jsonify({'status': 'ok', 'classes': classes})
    except Exception as e:
        logger.error(f"获取班级列表时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'获取班级列表失败: {str(e)}'}), 500

# 获取单个班级信息
@classes_bp.route('/api/classes/<class_id>', methods=['GET'])
def get_class(class_id):
    """获取单个班级信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询指定班级
        cursor.execute('SELECT * FROM classes WHERE id = ?', (class_id,))
        class_data = cursor.fetchone()
        
        if not class_data:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': f'未找到班级 ID: {class_id}'
            }), 404
        
        conn.close()
        
        # 返回班级信息
        return jsonify({
            'status': 'ok',
            'class': dict(class_data)
        })
    except Exception as e:
        print(f"获取班级信息时出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'获取班级信息失败: {str(e)}'
        }), 500

# 更新班级信息
@classes_bp.route('/api/classes/<class_id>', methods=['PUT'])
@login_required
def update_class(class_id):
    """更新班级信息"""
    # 只有管理员可以更新班级
    if not current_user.is_admin:
        logger.warning(f"用户 {current_user.username} 尝试更新班级，但权限不足")
        return jsonify({'status': 'error', 'message': '没有权限修改班级'}), 403
    
    try:
        # 获取请求数据
        data = request.json
        if not data or 'class_name' not in data:
            return jsonify({'status': 'error', 'message': '请提供班级名称'}), 400
        
        class_name = data.get('class_name', '').strip()
        if not class_name:
            return jsonify({'status': 'error', 'message': '班级名称不能为空'}), 400
        
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查班级是否存在
        cursor.execute('SELECT * FROM classes WHERE id = ?', (class_id,))
        class_info = cursor.fetchone()
        
        if not class_info:
            conn.close()
            return jsonify({'status': 'error', 'message': f'班级ID {class_id} 不存在'}), 404
        
        # 检查新名称是否与其他班级重复
        cursor.execute('SELECT id FROM classes WHERE class_name = ? AND id != ?', (class_name, class_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': f'班级名称 {class_name} 已存在'}), 400
        
        # 更新班级名称
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            UPDATE classes SET class_name = ?, updated_at = ? WHERE id = ?
        ''', (class_name, now, class_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功更新班级 ID={class_id} 的名称为: {class_name}")
        return jsonify({
            'status': 'ok',
            'message': f'成功更新班级名称',
            'class': {
                'id': class_id,
                'class_name': class_name,
                'updated_at': now
            }
        })
    except Exception as e:
        logger.error(f"更新班级时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'更新班级失败: {str(e)}'}), 500

# 删除班级
@classes_bp.route('/api/classes/<class_id>', methods=['DELETE'])
@login_required
def delete_class(class_id):
    """删除班级"""
    # 只有管理员可以删除班级
    if not current_user.is_admin:
        logger.warning(f"用户 {current_user.username} 尝试删除班级，但权限不足")
        return jsonify({'status': 'error', 'message': '没有权限删除班级'}), 403
    
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查班级是否存在
        cursor.execute('SELECT class_name FROM classes WHERE id = ?', (class_id,))
        class_info = cursor.fetchone()
        
        if not class_info:
            conn.close()
            return jsonify({'status': 'error', 'message': f'班级ID {class_id} 不存在'}), 404
        
        class_name = class_info['class_name']
        
        # 删除班级
        cursor.execute('DELETE FROM classes WHERE id = ?', (class_id,))
        
        # 同时更新关联的学生和用户记录
        cursor.execute('UPDATE students SET class_id = NULL WHERE class_id = ?', (class_id,))
        cursor.execute('UPDATE users SET class_id = NULL WHERE class_id = ?', (class_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功删除班级 ID={class_id}, 名称={class_name}")
        return jsonify({
            'status': 'ok',
            'message': f'成功删除班级: {class_name}'
        })
    except Exception as e:
        logger.error(f"删除班级时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'删除班级失败: {str(e)}'}), 500

# 获取可用班主任列表
@classes_bp.route('/api/teachers', methods=['GET'])
@login_required
def get_available_teachers():
    """获取可用于分配的班主任列表"""
    # 只有管理员可以查看班主任列表
    if not current_user.is_admin:
        logger.warning(f"用户 {current_user.username} 尝试查看班主任列表，但权限不足")
        return jsonify({'status': 'error', 'message': '没有权限查看班主任列表'}), 403
    
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询所有非管理员用户（潜在班主任）
        cursor.execute('''
            SELECT id, username, class_id FROM users 
            WHERE is_admin = 0
            ORDER BY username
        ''')
        teachers_data = cursor.fetchall()
        
        # 查询班级信息，用于显示当前分配情况
        cursor.execute('SELECT id, class_name FROM classes')
        classes = {row['id']: row['class_name'] for row in cursor.fetchall()}
        
        # 准备返回数据
        teachers = []
        for row in teachers_data:
            teacher_info = {
                'id': row['id'],
                'username': row['username'],
                'class_id': row['class_id'],
                'class_name': classes.get(row['class_id'], '未分配') if row['class_id'] else '未分配',
                'status': '已分配' if row['class_id'] else '未分配'
            }
            teachers.append(teacher_info)
        
        conn.close()
        
        return jsonify({'status': 'ok', 'teachers': teachers})
    except Exception as e:
        logger.error(f"获取班主任列表时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'获取班主任列表失败: {str(e)}'}), 500

# 为班级分配班主任
@classes_bp.route('/api/classes/<class_id>/assign-teacher', methods=['POST'])
@login_required
def assign_teacher(class_id):
    """为班级分配班主任"""
    # 只有管理员可以分配班主任
    if not current_user.is_admin:
        logger.warning(f"用户 {current_user.username} 尝试分配班主任，但权限不足")
        return jsonify({'status': 'error', 'message': '没有权限分配班主任'}), 403
    
    try:
        # 获取请求数据
        data = request.json
        if not data or 'teacher_id' not in data:
            return jsonify({'status': 'error', 'message': '请提供班主任ID'}), 400
        
        teacher_id = data.get('teacher_id')
        # 可以传空字符串表示取消分配
        if teacher_id == '':
            teacher_id = None
        
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查班级是否存在
        cursor.execute('SELECT class_name FROM classes WHERE id = ?', (class_id,))
        class_info = cursor.fetchone()
        
        if not class_info:
            conn.close()
            return jsonify({'status': 'error', 'message': f'班级ID {class_id} 不存在'}), 404
        
        class_name = class_info['class_name']
        
        # 如果提供了班主任ID，则检查用户是否存在且不是管理员
        teacher_name = "无"
        if teacher_id is not None:
            cursor.execute('SELECT username, is_admin FROM users WHERE id = ?', (teacher_id,))
            teacher_info = cursor.fetchone()
            
            if not teacher_info:
                conn.close()
                return jsonify({'status': 'error', 'message': f'用户ID {teacher_id} 不存在'}), 404
            
            if teacher_info['is_admin']:
                conn.close()
                return jsonify({'status': 'error', 'message': '管理员不能被分配为班主任'}), 400
                
            teacher_name = teacher_info['username']
            
            # 检查该教师是否已经被分配给其他班级
            cursor.execute('SELECT class_id FROM users WHERE id = ?', (teacher_id,))
            current_class = cursor.fetchone()['class_id']
            
            if current_class and current_class != class_id:
                # 获取当前班级名称
                cursor.execute('SELECT class_name FROM classes WHERE id = ?', (current_class,))
                current_class_info = cursor.fetchone()
                current_class_name = current_class_info['class_name'] if current_class_info else current_class
                
                # 自动解除之前的分配
                logger.info(f"教师 {teacher_name} 之前分配给班级 {current_class_name}，将自动解除")
                
                # 这里我们允许自动重新分配
                # cursor.execute('UPDATE users SET class_id = NULL WHERE id = ?', (teacher_id,))
                # conn.commit()
                # return jsonify({
                #     'status': 'error', 
                #     'message': f'教师 {teacher_name} 已经被分配给班级 {current_class_name}'
                # }), 400
        
        # 更新当前班级的班主任关联
        if teacher_id is not None:
            # 先解除当前与该班级关联的所有班主任
            cursor.execute('UPDATE users SET class_id = NULL WHERE class_id = ?', (class_id,))
            
            # 然后设置新的班主任
            cursor.execute('UPDATE users SET class_id = ? WHERE id = ?', (class_id, teacher_id))
            action = f"分配班主任 {teacher_name} 给班级 {class_name}"
        else:
            # 解除当前班级的班主任关联
            cursor.execute('UPDATE users SET class_id = NULL WHERE class_id = ?', (class_id,))
            action = f"移除班级 {class_name} 的班主任"
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功{action}")
        return jsonify({
            'status': 'ok',
            'message': f'成功{action}'
        })
    except Exception as e:
        logger.error(f"分配班主任时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'分配班主任失败: {str(e)}'}), 500 