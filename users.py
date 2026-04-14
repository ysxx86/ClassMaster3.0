#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户管理模块，包含用户相关的API路由和功能
"""

import os
import json
import sqlite3
import traceback
import datetime
import string
import random
import pandas as pd
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
import logging
from models.user import User
from werkzeug.utils import secure_filename

# 配置日志
logger = logging.getLogger(__name__)

# 用户蓝图
users_bp = Blueprint('users', __name__)

# 配置
DATABASE = 'students.db'

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

# 初始化用户表
def init_users():
    """初始化用户表，如果不存在则创建，必要时添加新列"""
    logger.info("初始化用户表")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        class_id TEXT,
        reset_password TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    
    # 检查是否所有必要的列都存在，如果不存在则添加
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    logger.info(f"用户表现有列: {existing_columns}")
    
    # 定义应该存在的列及其类型
    expected_columns = {
        'reset_password': 'TEXT',
        'class_id': 'TEXT',
        'is_admin': 'INTEGER',
        'created_at': 'TEXT',
        'updated_at': 'TEXT'
    }
    
    # 添加缺失的列
    for column, col_type in expected_columns.items():
        if column not in existing_columns:
            logger.warning(f"用户表添加缺失的列: {column} ({col_type})")
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {col_type}")
                conn.commit()
                logger.info(f"成功添加列: {column}")
            except sqlite3.Error as e:
                logger.error(f"添加列 {column} 时出错: {e}")
    
    # 检查是否有管理员账号
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    admin_count = cursor.fetchone()[0]
    
    # 如果没有管理员，创建默认管理员账号
    if admin_count == 0:
        logger.warning("未发现管理员账号，创建默认管理员")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        default_password = "admin123"
        password_hash = generate_password_hash(default_password)
        
        try:
            cursor.execute('''
            INSERT INTO users (id, username, password_hash, is_admin, reset_password, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('1', 'admin', password_hash, 1, default_password, now, now))
            conn.commit()
            logger.info("创建默认管理员成功")
            print(f"\n✅ 已创建默认管理员账号 - 用户名: admin, 密码: {default_password}")
        except sqlite3.Error as e:
            logger.error(f"创建默认管理员时出错: {e}")
    
    # 提交并关闭连接
    conn.commit()
    conn.close()
    
    logger.info("用户表初始化完成")

# 登录页面
@users_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            if request.is_json:
                return jsonify({'status': 'error', 'message': '请输入用户名和密码'}), 400
            else:
                return render_template('login.html', error='请输入用户名和密码')
        
        # 查询用户
        user = User.get_by_username(username)
        
        # 验证密码
        if user and check_password_hash(user.password_hash, password):
            # 更新reset_password字段为当前登录密码
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                cursor.execute('''
                UPDATE users SET reset_password = ?, updated_at = ? WHERE id = ?
                ''', (password, now, user.id))
                conn.commit()
                logger.info(f"用户 {username} 登录成功，已更新reset_password")
            except Exception as e:
                logger.error(f"更新reset_password时出错: {str(e)}")
            finally:
                conn.close()
            
            # 登录用户
            login_user(user)
            
            # 判断是否为AJAX请求
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'ok', 'message': '登录成功', 'redirect': '/'})
            else:
                # 检查是否有next参数（重定向目标）
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('index'))
        else:
            if request.is_json:
                return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 401
            else:
                return render_template('login.html', error='用户名或密码错误')
    
    # GET请求返回登录页面
    return render_template('login.html')

# 注销
@users_bp.route('/logout')
@login_required
def logout():
    logout_user()
    # 确保清除session
    session.clear()
    # 重定向到登录页面而不是首页
    return redirect(url_for('users.login'))

# 修改密码
@users_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
            
            if not current_password or not new_password:
                if request.is_json:
                    return jsonify({'status': 'error', 'message': '当前密码和新密码是必填的'}), 400
                else:
                    return render_template('change_password.html', error='当前密码和新密码是必填的')
            
            if confirm_password and new_password != confirm_password:
                if request.is_json:
                    return jsonify({'status': 'error', 'message': '新密码与确认密码不匹配'}), 400
                else:
                    return render_template('change_password.html', error='新密码与确认密码不匹配')
            
            # 获取当前用户
            user = User.get_by_id(current_user.id)
            
            # 验证当前密码
            if not user or not check_password_hash(user.password_hash, current_password):
                if request.is_json:
                    return jsonify({'status': 'error', 'message': '当前密码不正确'}), 401
                else:
                    return render_template('change_password.html', error='当前密码不正确')
            
            # 更新密码
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_password_hash = generate_password_hash(new_password)
                
                cursor.execute('''
                UPDATE users SET password_hash = ?, updated_at = ?, reset_password = ? WHERE id = ?
                ''', (new_password_hash, now, new_password, user.id))
                
                conn.commit()
                conn.close()
                
                if request.is_json:
                    return jsonify({'status': 'ok', 'message': '密码已成功更新'})
                else:
                    return render_template('change_password.html', success='密码已成功更新')
            except Exception as e:
                conn.close()
                logger.error(f"更新密码时出错: {str(e)}")
                if request.is_json:
                    return jsonify({'status': 'error', 'message': f'更新密码失败: {str(e)}'}), 500
                else:
                    return render_template('change_password.html', error=f'更新密码失败: {str(e)}')
        except Exception as e:
            logger.error(f"处理密码修改请求时出错: {str(e)}")
            if request.is_json:
                return jsonify({'status': 'error', 'message': f'处理请求失败: {str(e)}'}), 500
            else:
                return render_template('change_password.html', error=f'处理请求失败: {str(e)}')
    
    # GET请求返回修改密码页面
    return render_template('change_password.html')

# 获取所有用户
@users_bp.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """获取所有用户列表"""
    # 只有管理员可以访问用户管理
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '只有管理员可以访问用户管理功能'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash, class_id, is_admin, created_at, updated_at, reset_password FROM users')
        users_data = cursor.fetchall()
        conn.close()
        
        users = []
        for user in users_data:
            users.append({
                'id': user[0],
                'username': user[1],
                'password': user[2],  # 添加密码哈希
                'class_id': user[3],
                'is_admin': bool(user[4]),
                'created_at': user[5],
                'updated_at': user[6],
                'reset_password': user[7] if len(user) > 7 else None
            })
        
        return jsonify({'status': 'ok', 'users': users})
    except Exception as e:
        logger.error(f"获取用户列表时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'获取用户列表失败: {str(e)}'}), 500

# 添加单个用户
@users_bp.route('/api/users', methods=['POST'])
@login_required
def add_user():
    """添加新用户"""
    # 只有管理员可以添加用户
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '只有管理员可以添加用户'}), 403
    
    data = request.json
    
    if not data:
        return jsonify({'status': 'error', 'message': '无效的请求数据'}), 400
    
    # 检查必填字段
    if 'username' not in data or 'password' not in data:
        return jsonify({'status': 'error', 'message': '缺少必要的字段：用户名或密码'}), 400
    
    username = data.get('username')
    password = data.get('password')
    class_name = data.get('class_id')  # 这里实际上是班级名称
    is_admin = data.get('is_admin', False)
    
    # 检查用户名是否已存在
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    
    if cursor.fetchone():
        conn.close()
        return jsonify({'status': 'error', 'message': f'用户名 {username} 已存在'}), 400
    
    # 如果是班主任，校验班级是否存在
    class_id = None
    if not is_admin and class_name:
        try:
            # 尝试从classes表验证班级
            cursor.execute('SELECT id FROM classes WHERE class_name = ?', (class_name,))
            class_row = cursor.fetchone()
            if class_row:
                class_id = class_row['id']
                logger.info(f"找到班级 '{class_name}' 的ID: {class_id}")
            else:
                # 尝试从classes表查找所有班级
                cursor.execute('SELECT id, class_name FROM classes')
                classes = [row['class_name'] for row in cursor.fetchall()]
                conn.close()
                return jsonify({
                    'status': 'error', 
                    'message': f'班级 "{class_name}" 不存在，请先创建该班级。现有班级: {", ".join(classes)}'
                }), 400
        except sqlite3.OperationalError:
            # classes表不存在，尝试从students表验证
            logger.warning("classes表不存在，从students表验证班级")
            cursor.execute('SELECT DISTINCT class FROM students WHERE class = ?', (class_name,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({'status': 'error', 'message': f'班级 "{class_name}" 不存在，请先创建该班级'}), 400
            class_id = class_name  # 如果使用students表验证，则直接使用班级名作为ID
    else:
        # 管理员或未指定班级的用户
        class_id = class_name
    
    try:
        # 创建用户
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        password_hash = generate_password_hash(password)
        
        # 获取新ID
        cursor.execute('SELECT MAX(CAST(id AS INTEGER)) FROM users')
        max_id = cursor.fetchone()[0]
        new_id = str(int(max_id) + 1) if max_id else '1'
        
        cursor.execute('''
        INSERT INTO users (id, username, password_hash, is_admin, class_id, reset_password, created_at, updated_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_id, username, password_hash, 1 if is_admin else 0, class_id, password, now, now))
        
        conn.commit()
        
        logger.info(f"成功创建用户: {username}, ID: {new_id}, 班级ID: {class_id}")
        
        return jsonify({
            'status': 'ok', 
            'message': f'成功创建用户: {username}',
            'user': {
                'id': new_id,
                'username': username,
                'class_id': class_id,
                'is_admin': is_admin,
                'created_at': now,
                'updated_at': now
            }
        })
    except Exception as e:
        conn.rollback()
        logger.error(f"创建用户时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'创建用户失败: {str(e)}'}), 500
    finally:
        conn.close()

# 批量添加用户
@users_bp.route('/api/users/batch', methods=['POST'])
@login_required
def batch_add_users():
    """批量添加用户，主要用于批量创建班主任"""
    # 只有管理员可以批量添加用户
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '没有权限批量添加用户'}), 403
    
    data = request.json
    
    if not data or 'users' not in data or not isinstance(data['users'], list):
        return jsonify({'status': 'error', 'message': '无效的请求数据，需要提供users数组'}), 400
    
    users_to_add = data['users']
    
    if not users_to_add:
        return jsonify({'status': 'error', 'message': '用户列表为空'}), 400
    
    # 验证每个用户数据
    for user_data in users_to_add:
        if 'username' not in user_data or 'password' not in user_data:
            return jsonify({'status': 'error', 'message': '每个用户都需要提供用户名和密码'}), 400
    
    # 开始事务
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        added_users = []
        skipped_users = []
        
        # 获取当前最大ID
        cursor.execute('SELECT MAX(CAST(id AS INTEGER)) FROM users')
        max_id = cursor.fetchone()[0]
        current_id = int(max_id) if max_id else 0
        
        # 获取现有用户名列表
        cursor.execute('SELECT username FROM users')
        existing_usernames = set(row[0] for row in cursor.fetchall())
        
        # 尝试从classes表获取所有班级
        try:
            cursor.execute('SELECT id, class_name FROM classes')
            existing_classes = {row['class_name']: row['id'] for row in cursor.fetchall()}
            use_classes_table = True
            logger.info(f"使用classes表进行班级验证，找到 {len(existing_classes)} 个班级")
        except sqlite3.OperationalError:
            # 如果classes表不存在，则从students表获取
            logger.warning("classes表不存在，从students表获取班级信息")
            cursor.execute('SELECT DISTINCT class FROM students WHERE class IS NOT NULL AND class != ""')
            existing_classes = {row['class']: row['class'] for row in cursor.fetchall()}
            use_classes_table = False
        
        for user_data in users_to_add:
            username = user_data.get('username')
            password = user_data.get('password')
            class_name = user_data.get('class_id')  # 这里实际上存的是班级名称
            is_admin = user_data.get('is_admin', False)
            
            # 验证数据
            if not username:
                skipped_users.append({
                    'username': username or '空用户名',
                    'class_id': class_name or '空班级',
                    'reason': '用户名为空'
                })
                continue
                
            # 检查用户名是否已存在
            if username in existing_usernames:
                skipped_users.append({
                    'username': username,
                    'class_id': class_name,
                    'reason': '用户名已存在'
                })
                continue
            
            # 只有当班级名称非空时才检查班级是否存在
            class_id = None
            if class_name:
                # 检查班级是否存在
                if class_name not in existing_classes:
                    skipped_users.append({
                        'username': username,
                        'class_id': class_name,
                        'reason': '班级不存在，请先创建班级'
                    })
                    continue
                # 获取班级ID
                class_id = existing_classes[class_name]
            
            # 添加到已存在用户名集合，避免同一批次的重复用户名
            existing_usernames.add(username)
            
            # 生成ID和密码哈希
            current_id += 1
            new_id = str(current_id)
            password_hash = generate_password_hash(password)
            
            # 插入数据
            cursor.execute('''
            INSERT INTO users (id, username, password_hash, is_admin, class_id, reset_password, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, username, password_hash, 1 if is_admin else 0, class_id, password, now, now))
            
            added_users.append({
                'id': new_id,
                'username': username,
                'class_id': class_id,
                'is_admin': is_admin,
                'created_at': now,
                'updated_at': now
            })
        
        conn.commit()
        logger.info(f"批量添加用户成功，添加: {len(added_users)}，跳过: {len(skipped_users)}")
        
        # 若有跳过的用户，在消息中添加详细信息
        skipped_message = ""
        if skipped_users:
            skipped_message = "。跳过的用户: "
            for i, user in enumerate(skipped_users):
                if i > 0:
                    skipped_message += "；"
                reason = user.get('reason', '未知原因')
                class_info = f"({user.get('class_id', '无班级')})" if 'class_id' in user else ""
                skipped_message += f"{user['username']}{class_info}，原因: {reason}"
        
        return jsonify({
            'status': 'ok',
            'message': f'成功添加 {len(added_users)} 个用户，跳过 {len(skipped_users)} 个用户{skipped_message}',
            'added': added_users,
            'skipped': skipped_users
        })
    except Exception as e:
        conn.rollback()
        logger.error(f"批量添加用户时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'批量添加用户失败: {str(e)}'}), 500
    finally:
        conn.close()

# 编辑用户
@users_bp.route('/api/users/<user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """更新用户信息"""
    # 只有管理员可以编辑用户
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '没有权限编辑用户'}), 403
    
    data = request.json
    
    if not data:
        return jsonify({'status': 'error', 'message': '无效的请求数据'}), 400
    
    # 检查用户是否存在
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, is_admin FROM users WHERE id = ?', (user_id,))
    
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({'status': 'error', 'message': f'用户ID {user_id} 不存在'}), 404
    
    # 获取用户当前是否是管理员
    user_is_admin = bool(user['is_admin'])
    
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_fields = []
        params = []
        
        # 用户名更新
        if 'username' in data:
            # 检查新用户名是否已被其他用户占用
            cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', 
                          (data['username'], user_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'status': 'error', 'message': f'用户名 {data["username"]} 已被占用'}), 400
            
            update_fields.append("username = ?")
            params.append(data['username'])
        
        # 密码更新（如果有提供）
        if 'password' in data and data['password']:
            update_fields.append("password_hash = ?")
            params.append(generate_password_hash(data['password']))
            
            # 同时更新reset_password字段
            update_fields.append("reset_password = ?")
            params.append(data['password'])
        
        # 班级更新
        if 'class_id' in data:
            class_id_value = data.get('class_id')
            
            # 如果用户将成为班主任（或仍是班主任）且指定了班级，需验证班级是否存在
            will_be_admin = data.get('is_admin', user_is_admin)
            if not will_be_admin and class_id_value:
                try:
                    # 首先检查是不是数字ID
                    is_numeric = isinstance(class_id_value, int) or (isinstance(class_id_value, str) and class_id_value.isdigit())
                    
                    if is_numeric:
                        # 如果是数字，作为ID查询
                        numeric_id = int(class_id_value)
                        cursor.execute('SELECT id, class_name FROM classes WHERE id = ?', (numeric_id,))
                        class_row = cursor.fetchone()
                        if class_row:
                            class_id = class_row['id']
                            logger.info(f"找到班级ID: {class_id}, 名称: {class_row['class_name']}")
                        else:
                            # 尝试从classes表查找所有班级
                            cursor.execute('SELECT id, class_name FROM classes')
                            classes = [f"{row['id']}({row['class_name']})" for row in cursor.fetchall()]
                            conn.close()
                            return jsonify({
                                'status': 'error', 
                                'message': f'班级ID "{class_id_value}" 不存在，请先创建该班级。现有班级: {", ".join(classes)}'
                            }), 400
                    else:
                        # 如果不是数字，作为名称查询
                        cursor.execute('SELECT id FROM classes WHERE class_name = ?', (class_id_value,))
                        class_row = cursor.fetchone()
                        if class_row:
                            class_id = class_row['id']
                            logger.info(f"找到班级 '{class_id_value}' 的ID: {class_id}")
                        else:
                            # 尝试从classes表查找所有班级
                            cursor.execute('SELECT id, class_name FROM classes')
                            classes = [f"{row['class_name']}" for row in cursor.fetchall()]
                            conn.close()
                            return jsonify({
                                'status': 'error', 
                                'message': f'班级 "{class_id_value}" 不存在，请先创建该班级。现有班级: {", ".join(classes)}'
                            }), 400
                except sqlite3.OperationalError as e:
                    # classes表不存在或其他SQL错误
                    logger.warning(f"验证班级时SQL错误: {str(e)}")
                    logger.warning("尝试从students表验证班级")
                    
                    # 尝试作为ID和名称两种方式验证
                    if isinstance(class_id_value, int) or (isinstance(class_id_value, str) and class_id_value.isdigit()):
                        # 作为班级ID验证
                        numeric_id = int(class_id_value)
                        cursor.execute('SELECT DISTINCT class_id FROM students WHERE class_id = ?', (numeric_id,))
                        if cursor.fetchone():
                            class_id = numeric_id
                        else:
                            conn.close()
                            return jsonify({'status': 'error', 'message': f'班级ID "{class_id_value}" 不存在，请先创建该班级'}), 400
                    else:
                        # 作为班级名称验证
                        cursor.execute('SELECT DISTINCT class FROM students WHERE class = ?', (class_id_value,))
                        if cursor.fetchone():
                            class_id = class_id_value
                        else:
                            conn.close()
                            return jsonify({'status': 'error', 'message': f'班级 "{class_id_value}" 不存在，请先创建该班级'}), 400
            else:
                # 管理员或未指定班级的用户
                class_id = class_id_value
                
            update_fields.append("class_id = ?")
            params.append(class_id)
        
        # 管理员状态更新
        if 'is_admin' in data:
            update_fields.append("is_admin = ?")
            params.append(1 if data['is_admin'] else 0)
        
        # 更新时间
        update_fields.append("updated_at = ?")
        params.append(now)
        
        # 如果没有要更新的字段
        if not update_fields:
            conn.close()
            return jsonify({'status': 'ok', 'message': '没有发现需要更新的字段'}), 200
        
        # 构造更新SQL
        params.append(user_id)  # WHERE 条件的参数
        cursor.execute(f'''
        UPDATE users SET {', '.join(update_fields)} WHERE id = ?
        ''', params)
        
        conn.commit()
        
        logger.info(f"成功更新用户 ID={user_id}")
        
        return jsonify({
            'status': 'ok',
            'message': '用户信息已成功更新'
        })
    except Exception as e:
        conn.rollback()
        logger.error(f"更新用户时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'更新用户失败: {str(e)}'}), 500
    finally:
        conn.close()

# 删除用户
@users_bp.route('/api/users/<user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """删除用户"""
    # 只有管理员可以删除用户
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '没有权限删除用户'}), 403
    
    # 不能删除自己
    if str(current_user.id) == str(user_id):
        return jsonify({'status': 'error', 'message': '不能删除当前登录的用户'}), 400
    
    # 检查用户是否存在
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'status': 'error', 'message': f'用户ID {user_id} 不存在'}), 404
    
    try:
        # 删除用户
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        
        logger.info(f"成功删除用户: ID={user_id}, 用户名={user[1]}")
        
        return jsonify({
            'status': 'ok',
            'message': f'成功删除用户: {user[1]}'
        })
    except Exception as e:
        conn.rollback()
        logger.error(f"删除用户时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'删除用户失败: {str(e)}'}), 500
    finally:
        conn.close()

# 生成随机密码
def generate_random_password(length=6):
    """生成指定长度的随机密码，包含字母和数字"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# 批量导入班主任 - Excel文件上传
@users_bp.route('/api/users/import-excel', methods=['POST'])
@login_required
def import_teachers_excel():
    """通过Excel文件批量导入班主任"""
    # 只有管理员可以批量添加用户
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '没有权限批量添加用户'}), 403
    
    # 检查是否有文件上传
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '没有选择文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择文件'}), 400
    
    # 检查文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'status': 'error', 'message': '请上传Excel文件（.xlsx或.xls）'}), 400
    
    try:
        # 读取Excel文件
        df = pd.read_excel(file)
        
        # 检查必要的列是否存在
        required_columns = ['用户名', '班级']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({
                'status': 'error', 
                'message': f'Excel文件缺少必要的列: {", ".join(missing_columns)}'
            }), 400
        
        # 准备导入数据
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取现有用户名列表
        cursor.execute('SELECT username FROM users')
        existing_usernames = set(row[0] for row in cursor.fetchall())
        
        # 尝试从classes表获取所有班级
        try:
            cursor.execute('SELECT id, class_name FROM classes')
            existing_classes = {row['class_name']: row['id'] for row in cursor.fetchall()}
            use_classes_table = True
            logger.info(f"使用classes表进行班级验证，找到 {len(existing_classes)} 个班级")
        except sqlite3.OperationalError:
            # 如果classes表不存在，则从students表获取
            logger.warning("classes表不存在，从students表获取班级信息")
            cursor.execute('SELECT DISTINCT class FROM students WHERE class IS NOT NULL AND class != ""')
            existing_classes = {row['class']: row['class'] for row in cursor.fetchall()}
            use_classes_table = False
        
        # 获取当前最大ID
        cursor.execute('SELECT MAX(CAST(id AS INTEGER)) FROM users')
        max_id = cursor.fetchone()[0]
        current_id = int(max_id) if max_id else 0
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        added_users = []
        skipped_users = []
        passwords = []  # 存储生成的密码，用于返回
        
        # 处理每一行数据
        for _, row in df.iterrows():
            username = str(row['用户名']).strip()
            class_name = str(row['班级']).strip()
            
            # 验证数据
            if not username:
                skipped_users.append({
                    'username': username or '空用户名',
                    'class_id': class_name or '空班级',
                    'reason': '用户名为空'
                })
                continue
                
            # 检查用户名是否已存在
            if username in existing_usernames:
                skipped_users.append({
                    'username': username,
                    'class_id': class_name,
                    'reason': '用户名已存在'
                })
                continue
            
            # 只有当班级名称非空时才检查班级是否存在
            class_id = None
            if class_name:
                # 检查班级是否存在
                if class_name not in existing_classes:
                    skipped_users.append({
                        'username': username,
                        'class_id': class_name,
                        'reason': '班级不存在，请先创建班级'
                    })
                    continue
                # 获取班级ID
                class_id = existing_classes[class_name]
            
            # 生成随机密码
            password = generate_random_password(6)
            password_hash = generate_password_hash(password)
            
            # 添加到已存在用户名集合
            existing_usernames.add(username)
            
            # 生成ID
            current_id += 1
            new_id = str(current_id)
            
            # 插入数据
            cursor.execute('''
            INSERT INTO users (id, username, password_hash, is_admin, class_id, reset_password, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, username, password_hash, 0, class_id, password, now, now))
            
            added_users.append({
                'id': new_id,
                'username': username,
                'class_id': class_id,
                'created_at': now
            })
            
            # 保存生成的密码
            passwords.append({
                'username': username,
                'class_id': class_name,  # 使用班级名称而不是ID，方便用户阅读
                'password': password
            })
        
        # 提交事务
        conn.commit()
        conn.close()
        
        logger.info(f"通过Excel批量导入班主任成功，添加: {len(added_users)}，跳过: {len(skipped_users)}")
        
        # 若有跳过的用户，在消息中添加详细信息
        skipped_message = ""
        if skipped_users:
            skipped_message = "。跳过的班主任: "
            for i, user in enumerate(skipped_users):
                if i > 0:
                    skipped_message += "；"
                skipped_message += f"{user['username']}({user['class_id']})，原因: {user['reason']}"
        
        return jsonify({
            'status': 'ok',
            'message': f'成功添加 {len(added_users)} 个班主任账户，跳过 {len(skipped_users)} 个{skipped_message}',
            'added_count': len(added_users),
            'skipped_count': len(skipped_users),
            'added': added_users,
            'skipped': skipped_users,
            'passwords': passwords
        })
        
    except Exception as e:
        logger.error(f"Excel导入班主任时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'导入失败: {str(e)}'}), 500

# 创建班主任Excel导入模板
def create_teacher_import_template():
    """创建班主任导入模板Excel文件"""
    try:
        template_path = os.path.join('templates', 'teacher_import_template.xlsx')
        
        # 创建示例数据
        data = {
            '用户名': ['teacher1', 'teacher2', 'teacher3', 'teacher4', '注意事项'],
        }
        
        # 创建DataFrame并保存为Excel
        df = pd.DataFrame(data)
        df.to_excel(template_path, index=False)
        
        logger.info(f"成功创建班主任导入模板: {template_path}")
        return template_path
    except Exception as e:
        logger.error(f"创建班主任导入模板失败: {str(e)}")
        return None

# 下载班主任导入模板
@users_bp.route('/api/users/template', methods=['GET'])
@login_required
def download_teacher_template():
    """提供班主任Excel导入模板下载"""
    # 只有管理员可以下载模板
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '没有权限下载模板'}), 403
    
    template_path = os.path.join('templates', 'teacher_import_template.xlsx')
    
    # 检查模板是否存在，不存在则创建
    if not os.path.exists(template_path):
        template_path = create_teacher_import_template()
        if not template_path:
            return jsonify({'status': 'error', 'message': '创建模板失败'}), 500
    
    try:
        return send_file(template_path, as_attachment=True, download_name='班主任导入模板.xlsx')
    except Exception as e:
        logger.error(f"下载班主任导入模板失败: {str(e)}")
        return jsonify({'status': 'error', 'message': f'下载模板失败: {str(e)}'}), 500

# 获取当前用户信息
@users_bp.route('/api/current-user', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户的信息"""
    try:
        return jsonify({
            'status': 'ok',
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'class_id': current_user.class_id,
                'is_admin': current_user.is_admin
            }
        })
    except Exception as e:
        logger.error(f"获取当前用户信息时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'获取用户信息失败: {str(e)}'}), 500

# 直接API路径：重置用户密码
@users_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def api_reset_user_password(user_id):
    """直接API版本：重置指定用户的密码并返回新密码"""
    # 只有管理员可以重置密码
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '只有管理员可以重置用户密码'}), 403
    
    try:
        # 生成随机密码
        import random
        import string
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        
        # 生成密码哈希
        password_hash = generate_password_hash(new_password)
        
        # 更新数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
        UPDATE users SET password_hash = ?, updated_at = ?, reset_password = ? WHERE id = ?
        ''', (password_hash, now, new_password, user_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        conn.commit()
        conn.close()
        
        # 返回新密码
        return jsonify({
            'status': 'ok', 
            'message': '密码已重置', 
            'new_password': new_password
        })
    except Exception as e:
        logger.error(f"重置用户密码时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'重置密码失败: {str(e)}'}), 500

# 短路径重置密码API (为了兼容性)
@users_bp.route('/<int:user_id>/reset-password', methods=['POST'])
@login_required
def short_reset_user_password(user_id):
    """重置指定用户的密码 (短路径版本)"""
    return api_reset_user_password(user_id)

# 导入班主任预览API
@users_bp.route('/api/users/preview-import', methods=['POST'])
@login_required
def preview_import_teachers():
    """预览Excel文件中的班主任数据，不执行真正的导入"""
    # 只有管理员可以批量添加用户
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '没有权限批量添加用户'}), 403
    
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': '没有选择文件'}), 400
        
        # 检查文件类型
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'status': 'error', 'message': '请上传Excel文件（.xlsx或.xls）'}), 400
        
        # 确保uploads目录存在
        os.makedirs('uploads', exist_ok=True)
        
        # 保存上传的文件到临时目录
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        saved_filename = f"{timestamp}_{filename}"
        upload_path = os.path.join('uploads', saved_filename)
        
        # 保存文件
        try:
            file.save(upload_path)
            logger.info(f"成功保存上传的Excel文件: {upload_path}")
        except Exception as save_error:
            logger.error(f"保存上传文件失败: {str(save_error)}")
            return jsonify({'status': 'error', 'message': f'保存文件失败: {str(save_error)}'}), 500
        
        # 读取Excel文件
        try:
            df = pd.read_excel(upload_path)
            logger.info(f"成功读取Excel文件，包含 {len(df)} 行数据")
        except Exception as excel_error:
            logger.error(f"无法读取Excel文件: {str(excel_error)}")
            # 尝试删除已保存的文件
            try:
                if os.path.exists(upload_path):
                    os.remove(upload_path)
            except:
                pass
            return jsonify({'status': 'error', 'message': f'无法读取Excel文件: {str(excel_error)}'}), 400
        
        # 检查必要的列是否存在
        required_columns = ['用户名']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Excel文件缺少必要列: {missing_columns}")
            return jsonify({
                'status': 'error', 
                'message': f'Excel文件缺少必要的列: {", ".join(missing_columns)}'
            }), 400
        
        # 获取数据库连接
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
        except Exception as db_error:
            logger.error(f"数据库连接失败: {str(db_error)}")
            return jsonify({'status': 'error', 'message': f'数据库连接失败: {str(db_error)}'}), 500
        
        try:
            # 获取现有用户名列表
            cursor.execute('SELECT username FROM users')
            existing_usernames = set(row[0] for row in cursor.fetchall())
            
            # 尝试从classes表获取所有班级
            try:
                cursor.execute('SELECT id, class_name FROM classes')
                existing_classes = {row['class_name']: row['id'] for row in cursor.fetchall()}
                use_classes_table = True
                logger.info(f"使用classes表进行班级验证，找到 {len(existing_classes)} 个班级")
            except sqlite3.OperationalError:
                # 如果classes表不存在，则从students表获取
                logger.warning("classes表不存在，从students表获取班级信息")
                cursor.execute('SELECT DISTINCT class FROM students WHERE class IS NOT NULL AND class != ""')
                existing_classes = {row['class']: row['class'] for row in cursor.fetchall()}
                use_classes_table = False
            
            # 准备预览数据和统计
            preview_data = []
            valid_count = 0
            invalid_count = 0
            
            # 处理每一行数据
            for idx, row in df.iterrows():
                username = str(row['用户名']).strip() if pd.notna(row['用户名']) else ""
                # 如果存在班级列则获取，否则设为空
                class_name = str(row['班级']).strip() if '班级' in row and pd.notna(row['班级']) else ""
                
                # 判断数据有效性
                is_valid = True
                status = "有效"
                reason = ""
                
                # 验证数据
                if not username:
                    is_valid = False
                    status = "无效"
                    reason = "用户名为空"
                # 检查用户名是否已存在
                elif username in existing_usernames:
                    is_valid = False
                    status = "无效"
                    reason = "用户名已存在"
                # 只有当班级字段存在且不为空时才检查班级是否存在
                elif class_name and class_name not in existing_classes:
                    is_valid = False
                    status = "无效"
                    reason = "班级不存在，请先创建班级"
                
                # 统计结果
                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
                
                # 添加到预览数据
                preview_data.append({
                    'row': idx + 2,  # Excel中的行号(从2开始，因为1是表头)
                    'username': username,
                    'class_name': class_name,
                    'status': status,
                    'reason': reason,
                    'is_valid': is_valid
                })
        except Exception as process_error:
            logger.error(f"处理Excel数据时出错: {str(process_error)}")
            return jsonify({'status': 'error', 'message': f'处理Excel数据时出错: {str(process_error)}'}), 500
        finally:
            # 确保关闭数据库连接
            if 'conn' in locals():
                conn.close()
        
        # 返回预览结果
        return jsonify({
            'status': 'ok',
            'message': f'找到 {len(preview_data)} 名班主任数据，其中 {valid_count} 名有效，{invalid_count} 名无效',
            'preview': preview_data,
            'stats': {
                'total': len(preview_data),
                'valid': valid_count,
                'invalid': invalid_count
            },
            'file_path': upload_path  # 返回保存的文件路径，用于后续导入
        })
        
    except Exception as e:
        logger.error(f"预览Excel导入班主任时出错: {str(e)}")
        logger.error(traceback.format_exc())
        # 确保返回一个有效的JSON响应
        return jsonify({'status': 'error', 'message': f'预览失败: {str(e)}'}), 500

# 确认导入班主任
@users_bp.route('/api/users/confirm-import', methods=['POST'])
@login_required
def confirm_import_teachers():
    """确认导入预览过的班主任数据"""
    # 只有管理员可以批量添加用户
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '没有权限批量添加用户'}), 403
    
    data = request.json
    
    if not data or 'file_path' not in data:
        return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400
    
    file_path = data.get('file_path')
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return jsonify({'status': 'error', 'message': '导入文件不存在，请重新上传'}), 400
    
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)
        
        # 准备导入数据
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取现有用户名列表
        cursor.execute('SELECT username FROM users')
        existing_usernames = set(row[0] for row in cursor.fetchall())
        
        # 尝试从classes表获取所有班级
        try:
            cursor.execute('SELECT id, class_name FROM classes')
            existing_classes = {row['class_name']: row['id'] for row in cursor.fetchall()}
            use_classes_table = True
            logger.info(f"使用classes表进行班级验证，找到 {len(existing_classes)} 个班级")
        except sqlite3.OperationalError:
            # 如果classes表不存在，则从students表获取
            logger.warning("classes表不存在，从students表获取班级信息")
            cursor.execute('SELECT DISTINCT class FROM students WHERE class IS NOT NULL AND class != ""')
            existing_classes = {row['class']: row['class'] for row in cursor.fetchall()}
            use_classes_table = False
        
        # 获取当前最大ID
        cursor.execute('SELECT MAX(CAST(id AS INTEGER)) FROM users')
        max_id = cursor.fetchone()[0]
        current_id = int(max_id) if max_id else 0
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        added_users = []
        skipped_users = []
        passwords = []  # 存储生成的密码，用于返回
        
        # 处理每一行数据
        for _, row in df.iterrows():
            username = str(row['用户名']).strip()
            # 如果存在班级列则获取，否则设为空
            class_name = str(row['班级']).strip() if '班级' in row and pd.notna(row['班级']) else ""
            
            # 验证数据
            if not username:
                skipped_users.append({
                    'username': username or '空用户名',
                    'class_id': class_name or '空班级',
                    'reason': '用户名为空'
                })
                continue
                
            # 检查用户名是否已存在
            if username in existing_usernames:
                skipped_users.append({
                    'username': username,
                    'class_id': class_name,
                    'reason': '用户名已存在'
                })
                continue
            
            # 只有当班级字段非空时才检查班级是否存在
            class_id = None
            if class_name:
                # 检查班级是否存在
                if class_name not in existing_classes:
                    skipped_users.append({
                        'username': username,
                        'class_id': class_name,
                        'reason': '班级不存在，请先创建班级'
                    })
                    continue
                # 获取班级ID
                class_id = existing_classes[class_name]
            
            # 生成随机密码
            password = generate_random_password(6)
            password_hash = generate_password_hash(password)
            
            # 添加到已存在用户名集合
            existing_usernames.add(username)
            
            # 生成ID
            current_id += 1
            new_id = str(current_id)
            
            # 插入数据
            cursor.execute('''
            INSERT INTO users (id, username, password_hash, is_admin, class_id, reset_password, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, username, password_hash, 0, class_id, password, now, now))
            
            added_users.append({
                'id': new_id,
                'username': username,
                'class_id': class_id,
                'created_at': now
            })
            
            # 保存生成的密码
            passwords.append({
                'username': username,
                'class_id': class_name,  # 使用班级名称而不是ID，方便用户阅读
                'password': password
            })
        
        # 提交事务
        conn.commit()
        conn.close()
        
        # 删除临时文件
        try:
            os.remove(file_path)
            logger.info(f"已删除临时文件: {file_path}")
        except Exception as e:
            logger.warning(f"删除临时文件失败: {str(e)}")
        
        logger.info(f"确认导入班主任成功，添加: {len(added_users)}，跳过: {len(skipped_users)}")
        
        # 若有跳过的用户，在消息中添加详细信息
        skipped_message = ""
        if skipped_users:
            skipped_message = "。跳过的班主任: "
            for i, user in enumerate(skipped_users):
                if i > 0:
                    skipped_message += "；"
                skipped_message += f"{user['username']}({user['class_id']})，原因: {user['reason']}"
        
        return jsonify({
            'status': 'ok',
            'message': f'成功添加 {len(added_users)} 个班主任账户，跳过 {len(skipped_users)} 个{skipped_message}',
            'added_count': len(added_users),
            'skipped_count': len(skipped_users),
            'added': added_users,
            'skipped': skipped_users,
            'passwords': passwords
        })
        
    except Exception as e:
        logger.error(f"确认导入班主任时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'导入失败: {str(e)}'}), 500

# 导出用户列表API
@users_bp.route('/api/users/export', methods=['GET'])
@login_required
def export_users():
    """导出用户列表，包含用户名和密码信息"""
    # 只有管理员可以导出用户列表
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '只有管理员可以导出用户信息'}), 403
    
    try:
        # 获取查询参数
        only_teachers = request.args.get('only_teachers', 'true').lower() == 'true'
        include_admin = request.args.get('include_admin', 'false').lower() == 'true'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        query = 'SELECT id, username, reset_password, class_id, is_admin FROM users'
        params = []
        
        if only_teachers and not include_admin:
            query += ' WHERE is_admin = 0'
        elif not include_admin:
            query += ' WHERE is_admin = 0'
        
        query += ' ORDER BY username'
        
        cursor.execute(query, params)
        users_data = cursor.fetchall()
        
        # 获取班级信息，用于显示班级名称
        cursor.execute('SELECT id, class_name FROM classes')
        classes = {row['id']: row['class_name'] for row in cursor.fetchall()}
        
        conn.close()
        
        # 准备导出数据
        export_data = []
        for user in users_data:
            user_id = user['id']
            username = user['username']
            password = user['reset_password'] or '******' # 使用重置密码或占位符
            is_admin = bool(user['is_admin'])
            class_id = user['class_id']
            class_name = classes.get(class_id, '') if class_id else ''
            
            export_data.append({
                'id': user_id,
                'username': username,
                'password': password,
                'is_admin': '管理员' if is_admin else '班主任',
                'class_id': class_id or '',
                'class_name': class_name
            })
        
        logger.info(f"成功导出 {len(export_data)} 个用户信息")
        return jsonify({
            'status': 'ok',
            'users': export_data,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'export_by': current_user.username
        })
    
    except Exception as e:
        logger.error(f"导出用户列表时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'导出用户列表失败: {str(e)}'}), 500

# 导出用户列表为Excel文件
@users_bp.route('/api/users/export-excel', methods=['GET'])
@login_required
def export_users_excel():
    """导出用户列表为Excel文件，包含用户名和密码信息"""
    # 只有管理员可以导出用户列表
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '只有管理员可以导出用户信息'}), 403
    
    try:
        # 获取查询参数
        only_teachers = request.args.get('only_teachers', 'true').lower() == 'true'
        include_admin = request.args.get('include_admin', 'false').lower() == 'true'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        query = 'SELECT id, username, reset_password, class_id, is_admin FROM users'
        params = []
        
        if only_teachers and not include_admin:
            query += ' WHERE is_admin = 0'
        elif not include_admin:
            query += ' WHERE is_admin = 0'
        
        query += ' ORDER BY username'
        
        cursor.execute(query, params)
        users_data = cursor.fetchall()
        
        # 获取班级信息，用于显示班级名称
        cursor.execute('SELECT id, class_name FROM classes')
        classes = {row['id']: row['class_name'] for row in cursor.fetchall()}
        
        conn.close()
        
        # 准备导出数据
        data = []
        for user in users_data:
            user_id = user['id']
            username = user['username']
            password = user['reset_password'] or '******'
            is_admin = bool(user['is_admin'])
            class_id = user['class_id']
            class_name = classes.get(class_id, '') if class_id else ''
            
            data.append({
                'ID': user_id,
                '用户名': username,
                '密码': password,
                '角色': '管理员' if is_admin else '班主任',
                '班级ID': class_id or '',
                '班级名称': class_name
            })
        
        # 若没有数据，返回错误信息
        if not data:
            return jsonify({'status': 'error', 'message': '没有找到符合条件的用户数据'}), 404
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 创建临时文件路径
        os.makedirs('temp', exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        excel_filename = f'用户列表_{timestamp}.xlsx'
        temp_path = os.path.join('temp', excel_filename)
        
        # 写入Excel文件
        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='用户列表')
            
            # 获取工作表对象并调整列宽
            worksheet = writer.sheets['用户列表']
            for idx, col in enumerate(df.columns):
                col_width = max(len(str(col)), df[col].astype(str).map(len).max())
                # 设置列宽，根据最长内容自适应
                worksheet.column_dimensions[chr(65 + idx)].width = col_width + 2
        
        logger.info(f"成功生成Excel文件: {temp_path}，包含 {len(data)} 个用户记录")
        
        # 以附件形式返回Excel文件
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=excel_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"导出用户Excel时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'导出Excel失败: {str(e)}'}), 500