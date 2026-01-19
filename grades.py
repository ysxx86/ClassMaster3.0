#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
成绩管理模块，包含成绩相关的API路由和功能
"""

import os
import json
import sqlite3
import traceback
import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app as app, session, send_file, send_from_directory
import openpyxl
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from utils.class_filter import class_filter, user_can_access
from utils.grades_manager import GradesManager
from utils.permission_checker import can_edit_grade, get_editable_subjects, can_access_students
import logging
import pandas as pd
import numpy as np
import glob
import io
import time
from markupsafe import escape

# 配置日志
logger = logging.getLogger(__name__)

# 成绩蓝图
grades_bp = Blueprint('grades', __name__)

# 配置
UPLOAD_FOLDER = 'uploads'
DATABASE = 'students.db'
TEMPLATE_FOLDER = 'templates'  # 模板文件夹

# 初始化成绩模块
def init_grades(app):
    """初始化成绩模块"""
    logger.info("初始化成绩模块")
    # 不创建额外的grades表，成绩数据直接存储在students表中
    logger.info("成绩模块初始化完成")

# 创建成绩管理器实例
grades_manager = GradesManager()

# 创建成绩导入模板
try:
    grades_manager.create_empty_template()
    print("成绩Excel模板创建完成")
except Exception as e:
    print(f"创建成绩模板时出错: {str(e)}")

# 提供模板下载
@grades_bp.route('/download/template/<filename>', methods=['GET'])
@login_required
def serve_template(filename):
    return send_from_directory(TEMPLATE_FOLDER, filename)

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

# 获取所有学生成绩
@grades_bp.route('/api/grades', methods=['GET'])
@login_required
def get_all_grades():
    try:
        semester = request.args.get('semester', '')
        class_id = request.args.get('class_id', '')
        
        if not semester:
            return jsonify({'status': 'error', 'message': '请提供学期'})
        
        # 权限控制：
        # - 超级管理员：可以查看所有班级
        # - 正班主任：只能查看自己的班级
        # - 科任老师/副班主任/行政/校级领导：只能查看自己任教的班级
        from utils.permission_checker import get_accessible_classes, get_user_permissions
        
        # 获取用户权限信息（包含任教学科）
        user_permissions = get_user_permissions(current_user)
        
        if not current_user.is_admin:
            # 获取用户有权限访问的班级列表
            accessible_classes = get_accessible_classes(current_user)
            
            if not accessible_classes:
                return jsonify({
                    'status': 'ok',
                    'grades': [],
                    'allowed_subjects': [],
                    'message': '您尚未被分配任教班级，无法查看学生成绩'
                })
            
            # 如果只有一个班级，直接使用
            if len(accessible_classes) == 1:
                class_id = accessible_classes[0]
            else:
                # 多个班级，需要查询所有班级的成绩
                logger.info(f"用户 {current_user.username} 有权访问的班级: {accessible_classes}")
                all_grades = []
                empty_classes = []  # 记录没有学生的班级
                
                for cid in accessible_classes:
                    logger.info(f"正在获取班级 {cid} 的成绩")
                    grades = grades_manager.get_all_grades(semester, cid)
                    logger.info(f"班级 {cid} 返回 {len(grades)} 条成绩记录")
                    
                    if len(grades) == 0:
                        # 班级没有学生，添加一个占位记录
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute('SELECT class_name FROM classes WHERE id = ?', (cid,))
                            class_info = cursor.fetchone()
                            conn.close()
                            
                            if class_info:
                                empty_classes.append({
                                    'class_id': cid,
                                    'class_name': class_info['class_name'],
                                    'student_count': 0
                                })
                        except Exception as e:
                            logger.error(f"获取班级信息失败: {str(e)}")
                    else:
                        all_grades.extend(grades)
                
                logger.info(f"总共合并了 {len(all_grades)} 条成绩记录")
                logger.info(f"空班级: {empty_classes}")
                
                # 获取用户可以查看的学科列表（所有任教班级的学科合集）
                allowed_subjects = set()
                for cid in accessible_classes:
                    class_subjects = user_permissions['teaching_map'].get(str(cid), [])
                    allowed_subjects.update(class_subjects)
                
                return jsonify({
                    'status': 'ok', 
                    'grades': all_grades,
                    'empty_classes': empty_classes,
                    'allowed_subjects': list(allowed_subjects),  # 返回允许查看的学科列表
                    'user_permissions': user_permissions  # 返回完整权限信息
                })
            
        grades = grades_manager.get_all_grades(semester, class_id)
        
        # 返回数据时包含用户权限信息
        return jsonify({
            'status': 'ok', 
            'grades': grades,
            'user_permissions': user_permissions  # 返回完整权限信息
        })
    except Exception as e:
        logger.error(f'获取学生成绩时出错: {str(e)}')
        return jsonify({'status': 'error', 'message': f'获取学生成绩失败: {str(e)}'})

# 获取单个学生成绩
@grades_bp.route('/api/student-grade/<student_id>', methods=['GET'])
def get_student_grade(student_id):
    try:
        # 获取班级ID，优先使用请求参数中的class_id
        class_id = request.args.get('class_id')
        if not class_id and hasattr(current_user, 'class_id'):
            class_id = current_user.class_id
            
        # 获取学期参数
        semester = request.args.get('semester', '')
        
        # 查询学生信息和成绩
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询学生基本信息
        cursor.execute('SELECT s.id, s.name, s.gender, c.c.class_name as class_name as c.class_name as class FROM students s LEFT JOIN classes c ON s.class_id = c.id s LEFT JOIN classes c ON s.class_id = c.id WHERE s.id = ? AND s.class_id = ?', 
                      (student_id, class_id))
        
        student = cursor.fetchone()
        
        if not student:
            return jsonify({
                'status': 'error',
                'message': '未找到学生'
            }), 404
        
        # 查询成绩，尝试从students表直接读取成绩字段
        cursor.execute('''
            SELECT 
                yuwen, shuxue, yingyu, daof, kexue, zonghe, 
                tiyu, yinyue, meishu, laodong, xinxi, shufa, xinli
            FROM students 
            WHERE id = ? AND class_id = ?
        ''', (student_id, class_id))
        
        grades_row = cursor.fetchone()
        
        # 如果没有成绩数据，使用空字典
        grades = {}
        
        if grades_row:
            # 构建成绩数据字典
            for key in ['yuwen', 'shuxue', 'yingyu', 'daof', 'kexue', 'zonghe', 
                        'tiyu', 'yinyue', 'meishu', 'laodong', 'xinxi', 'shufa', 'xinli']:
                if key in grades_row.keys():
                    grades[key] = grades_row[key] or ''
                else:
                    grades[key] = ''
        
        # 构建返回的数据结构
        student_data = {
            'id': student['id'],
            'name': student['name'],
            'gender': student['gender'],
            'class': student['class'],
            'grades': grades,
            'semester': semester
        }
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'student': student_data
        })
    except Exception as e:
        print(f"获取学生成绩时出错: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'获取学生成绩时出错: {str(e)}'
        }), 500

# 保存学生成绩
@grades_bp.route('/api/grades/<student_id>', methods=['POST'])
@login_required
def save_student_grade(student_id):
    try:
        data = request.get_json()
        logger.info(f"收到保存成绩请求，学生ID: {student_id}")
        logger.info(f"请求数据: {data}")
        
        semester = data.get('semester', '上学期')
        class_id = data.get('class_id')
        
        # 权限控制：
        # - 超级管理员：需要提供班级ID
        # - 正班主任：自动使用自己的班级ID
        # - 其他角色：需要提供班级ID（前端会传递）
        from utils.permission_checker import is_head_teacher
        
        if not current_user.is_admin:
            if is_head_teacher(current_user):
                # 正班主任自动使用自己的班级ID
                if not current_user.class_id:
                    return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法保存学生成绩'}), 403
                class_id = current_user.class_id
            elif not class_id:
                # 其他角色需要提供班级ID
                return jsonify({'status': 'error', 'message': '缺少班级ID参数'}), 400
        elif not class_id:
            return jsonify({'status': 'error', 'message': '管理员需提供班级ID参数'}), 400
        
        if not semester:
            logger.error("缺少必要参数: semester")
            return jsonify({'status': 'error', 'message': '缺少必要参数: semester'})
        
        # 学科名称映射（数据库字段名 -> 显示名称）
        subject_display_names = {
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
        
        # 检查每个学科的编辑权限
        grade_data = {}
        for field in data:
            if field not in ['semester', 'class_id'] and field in subject_display_names:
                subject_name = subject_display_names[field]
                # 检查是否有权限编辑该学科
                if not can_edit_grade(current_user, class_id, subject_name):
                    logger.warning(f"用户 {current_user.username} 尝试编辑无权限的学科: {subject_name}")
                    return jsonify({
                        'status': 'error', 
                        'message': f'您没有权限编辑{subject_name}成绩'
                    }), 403
                grade_data[field] = data.get(field, '')
        
        logger.info(f"提取的成绩数据: {grade_data}")
        success = grades_manager.save_grade(student_id, class_id, grade_data, semester)
        
        if success:
            logger.info(f"成功保存学生 {student_id} 的成绩")
            return jsonify({'status': 'ok', 'message': '成功保存学生成绩'})
        else:
            logger.error(f"保存学生 {student_id} 的成绩失败")
            return jsonify({'status': 'error', 'message': '保存学生成绩失败'})
    except Exception as e:
        logger.error(f"出错: {str(e)}")
        return jsonify({"status": "error", "message": f"操作失败: {str(e)}"}), 500

@grades_bp.route('/api/grades/<student_id>', methods=['DELETE'])
@login_required
def delete_student_grade(student_id):
    try:
        semester = request.args.get('semester', '上学期')
        class_id = request.args.get('class_id')
        
        # 权限控制：
        # - 超级管理员：需要提供班级ID
        # - 正班主任：自动使用自己的班级ID
        # - 其他角色：需要提供班级ID
        from utils.permission_checker import is_head_teacher
        
        if not current_user.is_admin:
            if is_head_teacher(current_user):
                # 正班主任自动使用自己的班级ID
                if not current_user.class_id:
                    return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法删除学生成绩'}), 403
                class_id = current_user.class_id
            elif not class_id:
                # 其他角色需要提供班级ID
                return jsonify({'status': 'error', 'message': '缺少班级ID参数'}), 400
        elif not class_id:
            return jsonify({'status': 'error', 'message': '管理员需提供班级ID参数'}), 400
            
        logger.info(f"收到删除成绩请求，学生ID: {student_id}, 班级ID: {class_id}, 学期: {semester}")
        
        success = grades_manager.delete_grade(student_id, class_id, semester)
        
        if success:
            logger.info(f"成功删除学生 {student_id} 的成绩")
            return jsonify({'status': 'ok', 'message': '成功删除学生成绩'})
        else:
            logger.error(f"删除学生 {student_id} 的成绩失败")
            return jsonify({'status': 'error', 'message': '删除学生成绩失败'})
    except Exception as e:
        logger.error(f'删除学生成绩时出错: {str(e)}')
        return jsonify({'status': 'error', 'message': f'删除学生成绩失败: {str(e)}'})

# 预览成绩导入
@grades_bp.route('/api/grades/preview-import', methods=['POST'])
@login_required
def preview_grades_import():
    try:
        semester = request.form.get('semester', '上学期')
        class_id = request.form.get('class_id')
        
        # 权限控制：
        # - 超级管理员：需要提供班级ID
        # - 正班主任：自动使用自己的班级ID
        # - 其他角色：需要提供班级ID
        from utils.permission_checker import is_head_teacher
        
        if not current_user.is_admin:
            if is_head_teacher(current_user):
                # 正班主任自动使用自己的班级ID
                if not current_user.class_id:
                    return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法导入成绩'}), 403
                class_id = current_user.class_id
            elif not class_id:
                # 其他角色需要提供班级ID
                return jsonify({'status': 'error', 'message': '缺少班级ID参数'}), 400
        elif not class_id:
            return jsonify({'status': 'error', 'message': '管理员需提供班级ID参数'}), 400
            
        logger.info(f"收到预览成绩导入请求，学期: {semester}, 班级: {class_id}")
        
        if 'file' not in request.files:
            logger.error("未提供文件")
            return jsonify({'status': 'error', 'message': '没有上传文件'}), 400
        
        file = request.files['file']
        logger.info(f"上传的文件名: {file.filename}")
        
        if file.filename == '':
            logger.error("未选择文件")
            return jsonify({'status': 'error', 'message': '未选择文件'}), 400
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            logger.error("文件格式不正确")
            return jsonify({'status': 'error', 'message': '只能上传Excel (.xlsx/.xls) 文件'}), 400
        
        # 创建上传目录
        if not os.path.exists(UPLOAD_FOLDER):
            logger.info(f"创建上传目录: {UPLOAD_FOLDER}")
            os.makedirs(UPLOAD_FOLDER)
        
        # 保存文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        saved_filename = f"{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(file_path)
        logger.info(f"保存文件到: {file_path}")
        
        # 确认文件是否成功保存
        if not os.path.exists(file_path):
            logger.error(f"文件保存失败: {file_path}")
            return jsonify({'status': 'error', 'message': '文件保存失败'}), 500
        
        logger.info(f"文件大小: {os.path.getsize(file_path)} 字节")
        
        # 调用预览功能
        logger.info("开始预览成绩导入")
        result = grades_manager.preview_grades_from_excel(file_path, semester, class_id)
        
        if result['status'] == 'ok':
            logger.info(f"成功预览成绩: {result['message']}")
            return jsonify(result)
        else:
            logger.error(f"预览成绩失败: {result['message']}")
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"出错: {str(e)}")
        return jsonify({"status": "error", "message": f"操作失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f'预览成绩导入时出错: {str(e)}')
        logger.error(traceback.format_exc())
    return jsonify({
                    'status': 'error', 
            'message': f'预览成绩导入失败: {str(e)}'
        }), 500

# 确认导入成绩
@grades_bp.route('/api/grades/confirm-import', methods=['POST'])
@login_required
def confirm_grades_import():
    try:
        data = request.json
        logger.info(f"收到确认导入成绩请求")
        
        if not data or 'file_path' not in data:
            logger.error("请求缺少文件路径")
            return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400
        
        file_path = data.get('file_path')
        semester = data.get('semester', '上学期')
        class_id = data.get('class_id')
        
        # 权限控制：
        # - 超级管理员：需要提供班级ID
        # - 正班主任：自动使用自己的班级ID
        # - 其他角色：需要提供班级ID
        from utils.permission_checker import is_head_teacher
        
        if not current_user.is_admin:
            if is_head_teacher(current_user):
                # 正班主任自动使用自己的班级ID
                if not current_user.class_id:
                    return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法导入成绩'}), 403
                class_id = current_user.class_id
            elif not class_id:
                # 其他角色需要提供班级ID
                return jsonify({'status': 'error', 'message': '缺少班级ID参数'}), 400
        elif not class_id:
            return jsonify({'status': 'error', 'message': '管理员需提供班级ID参数'}), 400
        
        if not file_path:
            return jsonify({'status': 'error', 'message': '文件路径不能为空'}), 400
            
        if not os.path.exists(file_path):
            return jsonify({'status': 'error', 'message': '文件不存在，可能已被删除'}), 400
        
        # 导入成绩
        logger.info(f"开始导入成绩，文件路径: {file_path}, 学期: {semester}, 班级: {class_id}")
        success, message = grades_manager.import_grades_from_excel(file_path, semester, class_id)
        
        if success:
            logger.info(f"成功导入成绩: {message}")
            return jsonify({'status': 'ok', 'message': message})
        else:
            logger.error(f"导入成绩失败: {message}")
            return jsonify({'status': 'error', 'message': message}), 400
    except Exception as e:
        logger.error(f"出错: {str(e)}")
        return jsonify({"status": "error", "message": f"操作失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f'确认导入成绩时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error', 
            'message': f'确认导入成绩失败: {str(e)}'
        }), 500

# 导入学生成绩
@grades_bp.route('/api/grades/import', methods=['POST'])
@login_required
def import_grades():
    try:
        semester = request.form.get('semester', '上学期')
        class_id = request.form.get('class_id')
        
        # 权限控制：
        # - 超级管理员：需要提供班级ID
        # - 正班主任：自动使用自己的班级ID
        # - 其他角色：需要提供班级ID
        from utils.permission_checker import is_head_teacher
        
        if not current_user.is_admin:
            if is_head_teacher(current_user):
                # 正班主任自动使用自己的班级ID
                if not current_user.class_id:
                    return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法导入成绩'}), 403
                class_id = current_user.class_id
            elif not class_id:
                # 其他角色需要提供班级ID
                return jsonify({'status': 'error', 'message': '缺少班级ID参数'}), 400
        elif not class_id:
            return jsonify({'status': 'error', 'message': '管理员需提供班级ID参数'}), 400
            
        logger.info(f"收到导入成绩请求，学期: {semester}, 班级: {class_id}")
        
        if 'file' not in request.files:
            logger.error("未提供文件")
            return jsonify({'status': 'error', 'message': '没有上传文件'})
        
        file = request.files['file']
        logger.info(f"上传的文件名: {file.filename}")
        
        if file.filename == '':
            logger.error("未选择文件")
            return jsonify({'status': 'error', 'message': '未选择文件'})
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            logger.error("文件格式不正确")
            return jsonify({'status': 'error', 'message': '只能上传Excel (.xlsx/.xls) 文件'})
        
        # 创建上传目录
        if not os.path.exists(UPLOAD_FOLDER):
            logger.info(f"创建上传目录: {UPLOAD_FOLDER}")
            os.makedirs(UPLOAD_FOLDER)
        
        # 保存文件
        saved_filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(file_path)
        logger.info(f"保存文件到: {file_path}")
        
        # 确认文件是否成功保存
        if not os.path.exists(file_path):
            logger.error(f"文件保存失败: {file_path}")
            return jsonify({'status': 'error', 'message': '文件保存失败'})
        
        logger.info(f"文件大小: {os.path.getsize(file_path)} 字节")
        
        # 调用预览功能而不是直接导入
        logger.info("改为使用预览功能")
        result = grades_manager.preview_grades_from_excel(file_path, semester, class_id)
        
        if result['status'] == 'ok':
            logger.info(f"成功预览成绩: {result['message']}")
            return jsonify(result)
        else:
            logger.error(f"预览成绩失败: {result['message']}")
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"出错: {str(e)}")
        return jsonify({"status": "error", "message": f"操作失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f'导入成绩时出错: {str(e)}')
        logger.error(traceback.format_exc())
        
        # 提供更明确的错误信息
        error_message = str(e)
        if "No such file or directory" in error_message:
            error_message = f"找不到文件或目录: {error_message}"
        elif "Permission denied" in error_message:
            error_message = f"权限被拒绝: {error_message}"
        
        return jsonify({'status': 'error', 'message': f'导入成绩失败: {error_message}'})

# 下载成绩导入模板
@grades_bp.route('/api/grades/template', methods=['GET'])
@login_required
def download_grades_template():
    try:
        logger.info("收到下载成绩导入模板请求")
        class_id = request.args.get('class_id')
        
        # 权限控制：
        # - 超级管理员：可以指定班级ID或不指定
        # - 正班主任：自动使用自己的班级ID
        # - 其他角色：可以指定班级ID或不指定
        from utils.permission_checker import is_head_teacher
        
        if not current_user.is_admin:
            if is_head_teacher(current_user):
                # 正班主任自动使用自己的班级ID
                if not current_user.class_id:
                    return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法下载成绩模板'}), 403
                class_id = current_user.class_id
        elif not class_id and current_user.is_admin:
            logger.warning("管理员未指定班级ID")
            
        logger.info(f"准备下载成绩模板，班级ID: {class_id}")
        
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'grades_import_template.xlsx')
        logger.info(f"查找模板文件: {template_path}")
        
        # 生成文件名 - 如果指定了班级ID则包含在文件名中
        filename = '成绩导入模板'
        if class_id:
            filename += f'_{class_id}'
        filename += '.xlsx'
        
        # 根据班级生成对应的模板
        template_path = grades_manager.create_empty_template(output_path=None, class_id=class_id)
        logger.info(f"创建的模板路径: {template_path}")
        
        if not template_path or not os.path.exists(template_path):
            logger.error("创建模板失败或模板路径无效")
            return jsonify({'status': 'error', 'message': '创建成绩导入模板失败'})
        
        logger.info(f"准备发送模板文件: {template_path}")
        return send_file(template_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"出错: {str(e)}")
        return jsonify({"status": "error", "message": f"操作失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f'下载成绩导入模板时出错: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'下载成绩导入模板失败: {str(e)}'})