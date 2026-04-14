# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, send_from_directory, current_app, make_response, send_file
from flask_login import current_user
import sqlite3
import os
import datetime
import traceback
import logging
import tempfile
import zipfile
import sys
import platform
import threading
import time
import re
from werkzeug.utils import secure_filename
import urllib.parse

# 尝试导入pythoncom，如果不可用则跳过
try:
    import pythoncom
    PYTHONCOM_AVAILABLE = True
except ImportError:
    PYTHONCOM_AVAILABLE = False
    print("警告: pythoncom模块不可用，Word文档转换功能将不可用")

# 导入评语相关的工具类
from utils.comment_processor import batch_update_comments, generate_comments_pdf, generate_preview_html
from utils.comment_generator import CommentGenerator
try:
    from utils.pdf_exporter_fixed import export_comments_to_pdf
except ImportError:
    # 创建一个简化版的PDF导出函数，返回格式与正常函数一致
    def export_comments_to_pdf(*args, **kwargs):
        return {
            'status': 'error',
            'message': 'PDF导出功能不可用，请安装reportlab模块'
        }
    print("! PDF导出功能不可用，请安装reportlab模块")

# 导入Excel相关库
import pandas as pd
import numpy as np
import json
from io import BytesIO

# 创建评语管理蓝图
comments_bp = Blueprint('comments', __name__)
logger = logging.getLogger(__name__)

# 添加导出进度全局变量 - 改为基于用户的进度跟踪
user_export_progress = {}
progress_lock = threading.Lock()

# 更新导出进度信息
def websocket_progress(message, percent=None, request_id=None):
    """
    更新导出进度信息
    
    参数:
    - message: 进度消息内容
    - percent: 百分比值(0-100)
    - request_id: 请求ID
    """
    global user_export_progress
    
    # 获取当前用户ID，如果没有request_id则使用用户ID
    user_id = None
    if hasattr(current_user, 'id') and current_user.is_authenticated:
        user_id = str(current_user.id)
    
    # 使用request_id作为主键，如果没有则使用user_id
    progress_key = request_id if request_id else user_id
    if not progress_key:
        progress_key = 'anonymous'
    
    # 线程安全地更新进度信息
    with progress_lock:
        current_time = time.time()
        if progress_key not in user_export_progress:
            user_export_progress[progress_key] = {}
        
        user_export_progress[progress_key].update({
            'message': message,
            'percent': percent if percent is not None else user_export_progress[progress_key].get('percent', 0),
            'timestamp': current_time,
            'request_id': request_id,
            'user_id': user_id
        })
    
    # 打印日志
    logger.info(f"导出进度更新 [用户:{user_id}, 请求:{request_id}]: {message} ({percent if percent is not None else ''}%)")
    
    return user_export_progress.get(progress_key, {})

# 获取数据库连接函数
def get_db_connection():
    DATABASE = 'students.db'
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

# 获取单个学生评语
@comments_bp.route('/api/comments/<student_id>', methods=['GET'], strict_slashes=False)
def get_student_comment(student_id):
    try:
        # 获取班级ID，优先使用请求参数中的class_id，如果没有则使用当前用户的class_id
        class_id = request.args.get('class_id')
        if not class_id:
            class_id = current_user.class_id
        
        # 移除类型转换，但增加参数类型日志
        logger.info(f"获取评语: 学生ID={student_id} (类型: {type(student_id)}), 班级ID={class_id} (类型: {type(class_id)})")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, name, comments FROM students WHERE id = ? AND class_id = ?', (student_id, class_id))
            student = cursor.fetchone()
            
            conn.close()
        except Exception as e:
            logger.error(f"获取评语数据库查询错误: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'数据库查询错误: {str(e)}'
            }), 500
        
        if not student:
            logger.error(f"未找到学生评语: 学生ID={student_id}, 班级ID={class_id}")
            return jsonify({
                'status': 'error',
                'message': f'未找到ID为 {student_id} 的学生，或学生不在班级 {class_id} 中'
            }), 404
        
        logger.info(f"成功获取评语: 学生ID={student_id}, 班级ID={class_id}, 学生名称={student['name']}")
        return jsonify({
            'status': 'ok',
            'comment': {
                'studentId': student['id'],
                'studentName': student['name'],
                'content': student['comments'] or ''
            }
        })
    except Exception as e:
        logger.error(f"获取评语时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'获取评语时出错: {str(e)}'
        }), 500

# 保存学生评语
@comments_bp.route('/api/comments', methods=['POST'], strict_slashes=False)
def save_student_comment():
    data = request.json
    
    # 详细记录请求信息以便调试
    logger.info(f"收到保存评语请求: {data}")
    
    if not data or 'studentId' not in data or 'content' not in data:
        logger.error(f"请求数据验证失败: {data}")
        return jsonify({
            'status': 'error',
            'message': '请提供学生ID和评语内容'
        }), 400
        
    student_id = data['studentId']
    content = data['content']
    append_mode = data.get('appendMode', False)
    
    # 获取班级ID，优先使用请求中的classId，如果没有则使用当前用户的class_id
    class_id = data.get('classId')
    if not class_id:
        class_id = current_user.class_id
    
    # 移除类型转换，但添加类型记录以便调试
    logger.info(f"保存学生评语, 学生ID: {student_id} (类型: {type(student_id)}), 班级ID: {class_id} (类型: {type(class_id)}), 追加模式: {append_mode}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 修改权限检查逻辑，允许任何用户使用AI生成评语
        # 检查是否是AI评语请求（通过判断请求来源或特定标志）
        is_ai_comment = data.get('isAIComment', False)
        
        # 检查当前用户是否有权限修改该班级的评语
        # 如果是AI评语，或用户是管理员，或这是用户自己班级的学生，则允许操作
        if not is_ai_comment and not current_user.is_admin and class_id != current_user.class_id:
            conn.close()
            logger.error(f"权限检查失败: 用户班级ID={current_user.class_id}, 请求班级ID={class_id}")
            return jsonify({
                'status': 'error',
                'message': '您没有权限修改其他班级学生的评语'
            }), 403
        
        # 先检查学生是否存在于指定班级
        try:
            cursor.execute('SELECT id, comments FROM students WHERE id = ? AND class_id = ?', (student_id, class_id))
            student = cursor.fetchone()
        except Exception as e:
            conn.close()
            logger.error(f"SQL查询错误: {str(e)}, SQL: 'SELECT id, comments FROM students WHERE id = ? AND class_id = ?', 参数: ({student_id}, {class_id})")
            return jsonify({
                'status': 'error',
                'message': f'数据库查询错误: {str(e)}'
            }), 500
        
        if not student:
            conn.close()
            logger.error(f"未找到学生: 学生ID={student_id}, 班级ID={class_id}")
            return jsonify({
                'status': 'error',
                'message': '未找到该班级中的学生'
            }), 404
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 如果是追加模式且已有评语，则在原有评语基础上添加新内容
            if append_mode and student['comments']:
                # 在原评语后添加新评语（添加时间戳和分隔符）
                updated_content = f"{student['comments']}\n\n--- {now} ---\n{content}"
            else:
                # 直接使用新评语
                updated_content = content
                
            # 更新学生评语，确保只更新指定班级的学生记录
            cursor.execute('UPDATE students SET comments = ?, updated_at = ? WHERE id = ? AND class_id = ?', 
                          (updated_content, now, student_id, class_id))
            conn.commit()
            
            logger.info(f"评语保存成功: 学生ID={student_id}, 班级ID={class_id}")
            return jsonify({
                'status': 'ok',
                'message': '评语保存成功',
                'updatedContent': updated_content,
                'updateDate': now
            })
        except Exception as e:
            conn.rollback()
            logger.error(f"更新评语SQL错误: {str(e)}, SQL: 'UPDATE students SET comments = ?, updated_at = ? WHERE id = ? AND class_id = ?', 参数: ({len(updated_content)}字节, {now}, {student_id}, {class_id})")
            return jsonify({
                'status': 'error',
                'message': f'保存评语时出错: {str(e)}'
            }), 500
    except Exception as e:
        logger.error(f"保存评语时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# 获取评语模板API
@comments_bp.route('/api/comment-templates', methods=['GET'])
def get_comment_templates():
    """
    获取预定义的评语模板列表
    """
    templates = [
        # 学习类评语模板
        {"id": 1, "title": "品德优良", "content": "品德优良，尊敬师长，团结同学。", "type": "study"},
        {"id": 2, "title": "学习优秀", "content": "学习刻苦认真，上课认真听讲，作业按时完成。", "type": "study"},
        {"id": 3, "title": "学习积极", "content": "学习态度积极，能够主动思考，乐于探索新知识。", "type": "study"},
        {"id": 4, "title": "学习进步", "content": "近期学习有明显进步，在班级表现积极。", "type": "study"},
        {"id": 5, "title": "成绩优异", "content": "各科成绩优异，是班级的学习标兵。", "type": "study"},
        
        # 体育类评语模板
        {"id": 6, "title": "身体健康", "content": "身体健康，积极参加体育活动。", "type": "physical"},
        {"id": 7, "title": "运动技能", "content": "运动能力强，在体育活动中表现出色。", "type": "physical"},
        {"id": 8, "title": "体育精神", "content": "在体育活动中展现了团队合作精神和拼搏精神。", "type": "physical"},
        
        # 行为类评语模板
        {"id": 9, "title": "全面发展", "content": "德智体美劳全面发展，综合素质优秀。", "type": "behavior"},
        {"id": 10, "title": "行为规范", "content": "行为规范，能够严格遵守校规校纪。", "type": "behavior"},
        {"id": 11, "title": "积极参与", "content": "积极参与班级和学校活动，热心为集体服务。", "type": "behavior"},
        {"id": 12, "title": "有进步空间", "content": "在学习上有进步空间，希望能更加努力。", "type": "behavior"}
    ]
    
    return jsonify({
        "status": "ok",
        "templates": templates
    })

# 批量更新评语
@comments_bp.route('/api/batch-update-comments', methods=['POST'])
def batch_update_comments_api():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '未接收到数据'})
        
        content = data.get('content', '').strip()
        append_mode = data.get('appendMode', True)
        student_ids = data.get('studentIds', [])  # 获取选中的学生ID列表
        
        if not content:
            return jsonify({'status': 'error', 'message': '评语内容不能为空'})
        
        if not student_ids:
            return jsonify({'status': 'error', 'message': '未选择学生'})
        
        # 确保class_id是整数
        try:
            class_id = int(current_user.class_id)
        except (TypeError, ValueError):
            logger.error(f"批量更新评语时班级ID类型转换失败: {current_user.class_id}")
            return jsonify({'status': 'error', 'message': '班级ID格式不正确'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 记录更新的学生数量
        updated_count = 0
        
        # 获取当前时间，但不再添加到评语中
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 对选中的每个学生更新评语
        for student_id in student_ids:
            # 查询学生当前评语，确保只查询当前班级的学生
            cursor.execute('SELECT comments FROM students WHERE id = ? AND class_id = ?', (student_id, class_id))
            student = cursor.fetchone()
            
            if not student:
                continue  # 跳过不存在的学生ID或不属于当前班级的学生
            
            current_comment = student[0] or ''
            
            # 根据模式设置新评语
            if append_mode and current_comment:
                # 简化追加模式，直接添加到末尾
                new_comment = f"{current_comment.strip()}\n\n{content}"
            else:
                # 如果是替换模式或无评语，则直接使用新内容
                new_comment = content
            
            # 更新学生评语和更新时间，确保只更新当前班级的学生
            cursor.execute('UPDATE students SET comments = ?, updated_at = ? WHERE id = ? AND class_id = ?', 
                          (new_comment, now, student_id, class_id))
            
            updated_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'ok', 
            'message': f'已成功更新 {updated_count} 名学生的评语'
        })
        
    except Exception as e:
        logger.error(f"批量更新评语时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'})

# 清除当前班级所有评语
@comments_bp.route('/api/clear-all-comments', methods=['POST'])
def clear_all_comments():
    try:
        data = request.get_json()
        if not data:
            logger.error("清除评语 - 未接收到数据")
            return jsonify({'status': 'error', 'message': '未接收到数据'})
        
        # 获取班级ID
        class_id = data.get('class_id')
        
        # 记录班级ID的类型和值，帮助调试
        logger.info(f"清除评语 - 接收到的班级ID: {class_id}, 类型: {type(class_id)}")
        
        # 确保class_id是整数
        try:
            class_id = int(class_id)
            logger.info(f"清除评语 - 转换后的班级ID: {class_id}")
        except (TypeError, ValueError):
            logger.error(f"清除评语时班级ID类型转换失败: {class_id}")
            return jsonify({'status': 'error', 'message': f'班级ID格式不正确: {class_id}'})
        
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取当前时间
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 先获取班级中有评语的学生数量
            cursor.execute('SELECT COUNT(*) FROM students WHERE class_id = ? AND (comments IS NOT NULL AND comments <> "")', (class_id,))
            affected_count = cursor.fetchone()[0]
            
            logger.info(f"清除评语 - 班级ID {class_id} 中有评语的学生数量: {affected_count}")
            
            # 调试：获取班级中的学生总数
            cursor.execute('SELECT COUNT(*) FROM students WHERE class_id = ?', (class_id,))
            total_students = cursor.fetchone()[0]
            logger.info(f"清除评语 - 班级ID {class_id} 中的学生总数: {total_students}")
            
            # 调试：获取所有班级ID和对应的学生数量
            cursor.execute('SELECT class_id, COUNT(*) as student_count FROM students GROUP BY class_id')
            all_classes = cursor.fetchall()
            logger.info(f"清除评语 - 数据库中的所有班级ID和学生数量: {all_classes}")
            
            # 如果没有找到任何学生，尝试查询这个班级是否存在
            if total_students == 0:
                cursor.execute('SELECT DISTINCT class_id FROM students')
                all_class_ids = [row[0] for row in cursor.fetchall()]
                logger.warning(f"清除评语 - 班级ID {class_id} 没有学生。数据库中存在的班级ID: {all_class_ids}")
                return jsonify({
                    'status': 'error', 
                    'message': f'班级ID {class_id} 不存在或没有学生',
                    'available_class_ids': all_class_ids
                })
            
            # 清除指定班级所有学生的评语 - 使用空字符串而不是NULL，确保兼容性
            update_sql = 'UPDATE students SET comments = "", updated_at = ? WHERE class_id = ?'
            logger.info(f"清除评语 - 执行SQL: {update_sql}, 参数: ({now}, {class_id})")
            
            cursor.execute(update_sql, (now, class_id))
            
            # 检查影响的行数
            rows_affected = cursor.rowcount
            logger.info(f"清除评语 - 实际影响的行数: {rows_affected}")
            
            # 验证是否真的清除了评语
            cursor.execute('SELECT COUNT(*) FROM students WHERE class_id = ? AND (comments IS NOT NULL AND comments <> "")', (class_id,))
            remaining_comments = cursor.fetchone()[0]
            logger.info(f"清除评语 - 操作后仍有评语的学生数量: {remaining_comments}")
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"清除评语 - 数据库操作失败: {str(e)}")
            raise
        finally:
            conn.close()
        
        # 如果没有影响任何行，但有学生有评语，可能是SQL执行问题
        if rows_affected == 0 and affected_count > 0:
            logger.warning(f"清除评语 - 有{affected_count}名学生有评语，但SQL影响了0行")
            return jsonify({
                'status': 'error', 
                'message': f'清除评语失败，请检查数据库权限',
                'affected_count': 0
            })
        
        return jsonify({
            'status': 'ok', 
            'message': f'已成功清除 {affected_count} 名学生的评语',
            'affected_count': affected_count
        })
        
    except Exception as e:
        logger.error(f"清除评语时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加堆栈跟踪以便更好地调试
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'})

# AI生成评语API
@comments_bp.route('/api/generate-comment', methods=['POST'])
def generate_comment():
    """生成AI评语"""
    try:
        # 获取请求数据
        data = request.get_json()
        logger.info(f"收到评语生成请求: {data}")
        
        # 获取全局变量
        deepseek_api = current_app.config.get('deepseek_api')
        
        # 验证请求数据
        comment_generator = CommentGenerator(deepseek_api.api_key if deepseek_api else None)
        is_valid, error_msg = comment_generator.validate_request(data)
        if not is_valid:
            logger.error(f"请求数据验证失败: {error_msg}")
            return jsonify({
                "status": "error",
                "message": error_msg
            })
        
        # 获取学生信息
        student_id = data.get('student_id') or data.get('studentId')
        if not student_id:
            logger.error("缺少学生ID")
            return jsonify({
                "status": "error",
                "message": "缺少学生ID"
            })
            
        # 获取班级ID，优先使用请求中的class_id，如果没有则使用当前用户的class_id
        class_id = data.get('class_id')
        if not class_id:
            class_id = current_user.class_id
            
        # 移除类型转换，但增加参数类型日志
        logger.info(f"生成评语参数: 学生ID={student_id} (类型: {type(student_id)}), 班级ID={class_id} (类型: {type(class_id)})")
        
        # 从数据库获取学生信息
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT name, gender FROM students WHERE id = ? AND class_id = ?', (student_id, class_id))
            student = cursor.fetchone()
            conn.close()
        except Exception as e:
            logger.error(f"数据库查询错误: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"数据库查询错误: {str(e)}"
            }), 500
        
        if not student:
            logger.error(f"未找到学生: 学生ID={student_id}, 班级ID={class_id}")
            return jsonify({
                "status": "error",
                "message": f"未找到ID为 {student_id} 的学生或该学生不在班级 {class_id} 中"
            })
            
        # 构建学生信息字典
        student_info = {
            "name": student[0],
            "gender": student[1],
            "personality": data.get('personality', ''),
            "study_performance": data.get('study_performance', ''),
            "hobbies": data.get('hobbies', ''),
            "improvement": data.get('improvement', '')
        }
        
        # 获取评语参数
        style = data.get('style', '鼓励性的')
        tone = data.get('tone', '正式的')
        # 强制设置最大字数为260，忽略前端传入的值
        max_length = 50000  # 无论前端传入什么值，都固定为260
        min_length = 200  # 最小字数固定为200
        additional_instructions = data.get('additional_instructions', '')
        
        # 如果有额外指令，添加到学生信息中
        if additional_instructions:
            student_info['additional_instructions'] = additional_instructions
        
        # 记录正在为哪个学生生成评语
        logger.info(f"正在为学生 {student_info['name']}(ID: {student_id}, 班级ID: {class_id}) 生成评语")
        
        # 生成评语
        try:
            result = comment_generator.generate_comment(
                student_info=student_info,
                style=style,
                tone=tone,
                max_length=max_length,
                min_length=min_length  # 添加最小字数参数
            )
        except Exception as e:
            logger.error(f"评语生成引擎错误: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"评语生成失败: {str(e)}"
            }), 500
        
        logger.info(f"评语生成结果(学生ID: {student_id}, 班级ID: {class_id}): {result.get('status')}")
        
        # 返回结果
        if result["status"] == "ok":
            return jsonify({
                "status": "ok",
                "comment": result["comment"],
                "student_id": student_id,
                "class_id": class_id,
                "reasoning_content": result.get("reasoning_content", ""),
                "content_field": result.get("content_field", "")
            })
        else:
            return jsonify({
                "status": "error",
                "message": result["message"],
                "student_id": student_id,
                "class_id": class_id
            })
                
    except Exception as e:
        logger.error(f"生成评语时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": f"生成评语时出错: {str(e)}"
        }), 500

# 导出评语为PDF
@comments_bp.route('/api/export-comments-pdf', methods=['GET'])
def api_export_comments_pdf():
    # 获取班级参数（可选）
    class_name = request.args.get('class')
    logger.info(f"收到导出评语PDF请求，班级: {class_name}")
    
    try:
        # 检查用户权限
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': '您需要登录后才能导出评语', 'code': 'login_required'}), 401
            
        # 如果是班主任，检查是否有权限导出指定班级
        if hasattr(current_user, 'is_admin') and not current_user.is_admin and hasattr(current_user, 'class_id') and current_user.class_id:
            # 如果未指定班级，则使用班主任自己的班级
            if not class_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT c.class_name as class FROM students s LEFT JOIN classes c ON s.class_id = c.id WHERE class_id = ? LIMIT 1', (current_user.class_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    class_name = result['class']
                    logger.info(f"未指定班级，使用班主任班级: {class_name}")
            # 指定了班级，检查是否有权限
            elif class_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT c.class_name as class FROM students s LEFT JOIN classes c ON s.class_id = c.id WHERE class_id = ? LIMIT 1', (current_user.class_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result and result['class'] != class_name:
                    return jsonify({
                        'status': 'error',
                        'message': '权限不足，只能导出本班级的评语'
                    }), 403
        
        # 确保exports目录存在且可写
        EXPORTS_FOLDER = 'exports'
        if not os.path.exists(EXPORTS_FOLDER):
            try:
                os.makedirs(EXPORTS_FOLDER, exist_ok=True)
                logger.info(f"创建导出目录: {EXPORTS_FOLDER}")
            except Exception as e:
                logger.error(f"创建导出目录失败: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f'创建导出目录失败: {str(e)}'
                }), 400
        
        # 测试导出目录写入权限
        try:
            test_file = os.path.join(EXPORTS_FOLDER, "test_write.txt")
            with open(test_file, 'w') as f:
                f.write("Test write permission")
            if os.path.exists(test_file):
                os.remove(test_file)
        except Exception as e:
            logger.error(f"导出目录写入权限测试失败: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'导出目录没有写入权限: {str(e)}'
            }), 400
            
        # 检查PDF导出功能是否可用
        try:
            from reportlab.lib import colors
            logger.info("ReportLab库成功导入")
        except ImportError as e:
            logger.error(f"ReportLab库导入失败: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'PDF导出功能不可用，服务器缺少ReportLab库'
            }), 400
        
        # 限制班级大小 - 如果未指定班级，检查学生总数
        if not class_name:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) as count FROM students')
                result = cursor.fetchone()
                total_students = result['count'] if result else 0
                conn.close()
                
                # 如果学生总数过多，要求用户选择特定班级
                if total_students > 200:
                    return jsonify({
                        'status': 'error',
                        'message': f'学生总数过多 ({total_students}人)，请选择特定班级后再导出'
                    }), 400
            except Exception as e:
                logger.error(f"检查学生总数时出错: {str(e)}")
                # 继续执行，不中断流程
        
        # 调用PDF导出函数
        logger.info("调用PDF导出函数")
        result = export_comments_to_pdf(class_name)
        logger.info(f"PDF导出结果: {result}")
        
        # 检查result类型，处理可能的返回值为None或元组的情况
        if result is None:
            logger.error("导出函数返回None")
            return jsonify({
                'status': 'error',
                'message': 'PDF导出功能返回None，请检查服务器日志'
            }), 400
        elif isinstance(result, tuple) and len(result) == 2 and result[0] is None:
            logger.error(f"导出函数返回错误元组: {result}")
            return jsonify({
                'status': 'error',
                'message': result[1]
            }), 400
        
        # 正常处理字典类型的结果
        if result.get('status') == 'ok':
            logger.info(f"PDF导出成功: {result.get('file_path')}")
            # 确保下载URL可用
            if 'download_url' in result:
                download_url = result['download_url']
                # 如果URL不是以http开头，添加前缀
                if not download_url.startswith('http'):
                    # 获取服务器的URL前缀
                    if request.host_url:
                        base_url = request.host_url.rstrip('/')
                        download_url = download_url.lstrip('/')
                        result['download_url'] = f"{base_url}/{download_url}"
            return jsonify(result)
        else:
            logger.error(f"PDF导出失败: {result.get('message')}")
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"导出评语PDF时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'导出评语PDF时发生错误: {str(e)}'
        }), 400

# 生成打印预览HTML
@comments_bp.route('/api/preview-comments', methods=['GET'])
def api_preview_comments():
    # 获取班级参数（可选）
    class_name = request.args.get('class')
    
    try:
        # 检查用户权限
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': '未登录', 'code': 'login_required'}), 401
            
        # 如果是班主任，检查是否有权限预览指定班级
        if hasattr(current_user, 'is_admin') and not current_user.is_admin and hasattr(current_user, 'class_id') and current_user.class_id:
            # 如果未指定班级，则使用班主任自己的班级
            if not class_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT c.class_name as class FROM students s LEFT JOIN classes c ON s.class_id = c.id WHERE class_id = ? LIMIT 1', (current_user.class_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    class_name = result['class']
                    logger.info(f"未指定班级，使用班主任班级: {class_name}")
            # 指定了班级，检查是否有权限
            elif class_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT c.class_name as class FROM students s LEFT JOIN classes c ON s.class_id = c.id WHERE class_id = ? LIMIT 1', (current_user.class_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result and result['class'] != class_name:
                    return jsonify({
                        'status': 'error',
                        'message': '权限不足，只能预览本班级的评语'
                    }), 403
    
        # 调用预览函数，传递当前用户信息
        result = generate_preview_html(class_name, current_user)
        
        if result['status'] == 'ok':
            # 返回HTML内容
            response = make_response(result['html'])
            response.headers['Content-Type'] = 'text/html'
            return response
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"生成打印预览时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'生成打印预览时出错: {str(e)}'
        }), 500

# 添加取消导出功能
import threading

# 用于存储活动导出请求的字典和锁
active_export_requests = {}
export_requests_lock = threading.Lock()

# 检查导出请求是否被取消
def is_export_cancelled(request_id):
    """检查指定的导出请求是否已被取消"""
    if not request_id:
        return False
        
    with export_requests_lock:
        request_info = active_export_requests.get(request_id)
        if request_info and request_info.get('cancelled', False):
            logger.info(f"导出请求 {request_id} 已被取消")
            return True
    return False

# 清理过期的导出请求
def cleanup_export_requests():
    """清理超过30分钟的导出请求"""
    now = datetime.datetime.now()
    with export_requests_lock:
        expired_requests = []
        for req_id, info in active_export_requests.items():
            if (now - info['started_at']).total_seconds() > 1800:  # 30分钟
                expired_requests.append(req_id)
                
        for req_id in expired_requests:
            logger.info(f"清理过期的导出请求: {req_id}")
            del active_export_requests[req_id]

# 取消导出API
@comments_bp.route('/api/cancel-export', methods=['POST'])
def cancel_export():
    try:
        data = request.get_json()
        request_id = data.get('requestId')
        
        if not request_id:
            return jsonify({'status': 'error', 'message': '未提供请求ID'})
            
        logger.info(f"收到取消导出请求: {request_id}")
        
        # 清理过期请求
        cleanup_export_requests()
        
        # 标记请求为已取消
        found = False
        with export_requests_lock:
            if request_id in active_export_requests:
                active_export_requests[request_id]['cancelled'] = True
                active_export_requests[request_id]['status'] = 'cancelled'
                found = True
                logger.info(f"已标记导出请求 {request_id} 为已取消")
            
        if found:
            return jsonify({
                'status': 'success',
                'message': '导出操作已取消'
            })
        else:
            logger.warning(f"未找到要取消的导出请求: {request_id}")
            return jsonify({
                'status': 'warning',
                'message': '未找到指定的导出请求，可能已完成或不存在'
            })
    except Exception as e:
        logger.error(f"取消导出请求处理出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'取消导出失败: {str(e)}'})

# 在文件转换过程中定期检查取消状态
def convert_docx_to_pdf(input_file, output_file, request_id=None):
    """转换单个Word文档为PDF，确保COM环境正确初始化，并支持取消操作"""
    
    # 检测操作系统
    system = platform.system()
    logger.info(f"当前操作系统: {system}")
    
    # Linux系统使用LibreOffice或unoconv转换
    if system == "Linux":
        try:
            logger.info(f"Linux系统，尝试转换文件：{input_file} -> {output_file}")
            
            # 确保输入文件路径是绝对路径
            input_file_abs = os.path.abspath(input_file)
            output_file_abs = os.path.abspath(output_file)
            output_dir = os.path.dirname(output_file_abs)
            
            # 确保输出目录存在
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 先尝试使用unoconv转换
            import subprocess
            check_cmd = ["which", "unoconv"]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("检测到unoconv，使用unoconv进行转换")
                # 使用unoconv转换
                cmd = [
                    "unoconv", 
                    "-f", "pdf",
                    "-o", output_file_abs,
                    input_file_abs
                ]
                
                # 执行命令
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                # 检查命令输出
                if result.returncode != 0:
                    logger.error(f"unoconv转换失败，退出码: {result.returncode}")
                    logger.error(f"错误输出: {result.stderr}")
                    logger.warning("unoconv失败，尝试使用LibreOffice")
                else:
                    # 验证文件是否生成
                    if os.path.exists(output_file_abs) and os.path.getsize(output_file_abs) > 0:
                        logger.info(f"unoconv成功转换文件: {output_file_abs}")
                        return True
                    else:
                        logger.error(f"未找到unoconv转换后的PDF文件: {output_file_abs}")
            else:
                logger.info("未检测到unoconv，尝试使用LibreOffice")
                
            # 如果unoconv不可用或失败，尝试使用LibreOffice
            check_cmd = ["which", "libreoffice"]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning("在Linux上未找到LibreOffice，尝试使用soffice命令")
                check_cmd = ["which", "soffice"]
                result = subprocess.run(check_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error("未找到LibreOffice或soffice命令，无法转换PDF")
                    return False
                libreoffice_cmd = "soffice"
            else:
                libreoffice_cmd = "libreoffice"
            
            # 使用LibreOffice转换
            logger.info(f"使用 {libreoffice_cmd} 转换文档")
            cmd = [
                libreoffice_cmd, 
                "--headless", 
                "--convert-to", 
                "pdf", 
                "--outdir", 
                output_dir,
                input_file_abs
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # 检查命令输出
            if result.returncode != 0:
                logger.error(f"LibreOffice转换失败，退出码: {result.returncode}")
                logger.error(f"错误输出: {result.stderr}")
                return False
                
            # 检查目标文件是否存在
            converted_file = os.path.join(output_dir, os.path.basename(input_file_abs).replace('.docx', '.pdf'))
            
            # 如果输出文件名与默认名不同，需要重命名
            if converted_file != output_file_abs and os.path.exists(converted_file):
                os.rename(converted_file, output_file_abs)
                logger.info(f"重命名转换文件: {converted_file} -> {output_file_abs}")
            
            # 验证文件是否生成
            if os.path.exists(output_file_abs) and os.path.getsize(output_file_abs) > 0:
                logger.info(f"LibreOffice成功转换文件: {output_file_abs}")
                return True
            else:
                logger.error(f"未找到转换后的PDF文件: {output_file_abs}")
                return False
                
        except Exception as e:
            logger.error(f"Linux下文档转换失败: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    # Windows系统使用原有代码
    elif system == "Windows":
        # 如果pythoncom不可用，直接返回错误
        if not PYTHONCOM_AVAILABLE:
            logger.error("无法转换Word文档：pythoncom模块不可用，请安装pywin32包")
            return False
            
        try:
            # 检查是否已取消
            if request_id and is_export_cancelled(request_id):
                logger.info(f"文件 {os.path.basename(input_file)} 的转换已被取消")
                return False
                
            # 初始化COM环境
            logger.info(f"为文件 {os.path.basename(input_file)} 初始化COM环境")
            pythoncom.CoInitialize()
            
            # 直接使用win32com进行更可靠的转换，而不是依赖docx2pdf
            try:
                from win32com.client import Dispatch, constants
                
                # 确保输入文件路径是绝对路径
                input_file_abs = os.path.abspath(input_file)
                output_file_abs = os.path.abspath(output_file)
                
                logger.info(f"使用win32com直接转换: {input_file_abs} -> {output_file_abs}")
                
                # 创建Word应用实例
                word = Dispatch('Word.Application')
                word.Visible = False  # 不显示Word界面
                
                # 检查Word是否成功启动
                if word is None:
                    logger.error("无法创建Word应用程序实例")
                    return False
                    
                logger.info("Word应用程序实例创建成功")
                
                # 打开文档
                try:
                    doc = word.Documents.Open(input_file_abs)
                    logger.info(f"成功打开文档: {input_file_abs}")
                except Exception as e:
                    logger.error(f"打开文档失败: {str(e)}")
                    word.Quit()
                    return False
                
                # 另存为PDF
                try:
                    # 检查目录是否存在
                    output_dir = os.path.dirname(output_file_abs)
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir, exist_ok=True)
                    
                    # 使用不同的常量格式另存为PDF
                    try:
                        # PDF格式常量(17)
                        doc.SaveAs(output_file_abs, FileFormat=17)
                        logger.info(f"使用FileFormat=17成功保存PDF: {output_file_abs}")
                    except Exception as save_error:
                        logger.warning(f"使用FileFormat=17保存失败: {str(save_error)}，尝试使用wdFormatPDF")
                        try:
                            # 尝试使用常量名
                            doc.SaveAs(output_file_abs, FileFormat=constants.wdFormatPDF)
                            logger.info(f"使用wdFormatPDF成功保存PDF: {output_file_abs}")
                        except Exception as e:
                            logger.error(f"所有保存方法都失败: {str(e)}")
                            raise
                except Exception as e:
                    logger.error(f"保存PDF时出错: {str(e)}")
                    doc.Close(False)  # 不保存更改
                    word.Quit()
                    return False
                finally:
                    # 关闭文档
                    try:
                        doc.Close()
                        logger.info("文档已关闭")
                    except:
                        logger.warning("关闭文档时出错")
                
                # 退出Word
                try:
                    word.Quit()
                    logger.info("Word应用已退出")
                except:
                    logger.warning("退出Word时出错")
                
            except ImportError:
                # 如果win32com不可用，尝试使用docx2pdf
                logger.warning("win32com不可用，回退到docx2pdf")
                from docx2pdf import convert
                logger.info(f"使用docx2pdf转换Word文件: {input_file} -> {output_file}")
                convert(input_file, output_file)
            
            # 再次检查是否在转换过程中被取消
            if request_id and is_export_cancelled(request_id):
                logger.info(f"文件 {os.path.basename(input_file)} 转换完成，但请求已被取消")
                # 如果已取消，尝试删除生成的文件
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        logger.info(f"已删除已取消请求生成的文件: {output_file}")
                    except Exception as e:
                        logger.warning(f"无法删除已取消请求生成的文件: {output_file}, 错误: {str(e)}")
                return False
            
            # 验证文件是否成功创建
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                if file_size > 0:
                    logger.info(f"成功转换文件为PDF: {output_file}, 文件大小: {file_size} 字节")
                    return True
                else:
                    logger.error(f"转换后的PDF文件大小为0: {output_file}")
                    return False
            else:
                logger.error(f"转换后的PDF文件不存在: {output_file}")
                return False
        except Exception as e:
            logger.error(f"转换文件 {os.path.basename(input_file)} 失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
        finally:
            # 释放COM资源
            try:
                if PYTHONCOM_AVAILABLE:
                    logger.info(f"释放文件 {os.path.basename(input_file)} 的COM资源")
                    pythoncom.CoUninitialize()
            except:
                logger.warning("CoUninitialize失败，可能COM资源未正确初始化")
    
    # 其他操作系统（如macOS）
    else:
        logger.error(f"不支持的操作系统: {system}, 无法转换PDF")
        return False

# 导出报告API
@comments_bp.route('/api/export-reports', methods=['POST'])
def api_export_reports():
    try:
        # 检查用户是否已登录
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            logger.warning("未登录用户或会话过期，尝试导出报告")
            return jsonify({'status': 'error', 'message': '您需要登录后才能导出报告', 'code': 'login_required'}), 401
            
        # 获取请求数据
        data = request.get_json()
        
        # 记录请求ID，用于支持取消功能
        request_id = request.headers.get('X-Export-Request-ID')
        if request_id:
            logger.info(f"收到导出报告请求 [请求ID: {request_id}]: {data}")
            # 将请求ID存储到活动请求字典中
            with export_requests_lock:
                active_export_requests[request_id] = {
                    'status': 'processing',
                    'started_at': datetime.datetime.now(),
                    'cancelled': False
                }
        else:
            logger.info(f"收到导出报告请求 (无请求ID): {data}")
        
        # 验证请求数据
        student_ids = data.get('studentIds', [])
        template_id = data.get('templateId', '泉州东海湾实验学校综合素质发展报告单')
        use_default_template = data.get('useDefaultTemplate', False)
        settings = data.get('settings', {})
        
        # 获取导出类型（默认为word）
        export_type = settings.get('exportType', 'word')
        logger.info(f"导出类型: {export_type}")
        
        if not student_ids:
            return jsonify({'status': 'error', 'message': '未选择任何学生'})
            
        if not template_id:
            template_id = '泉州东海湾实验学校综合素质发展报告单'
            logger.info(f"未指定模板ID，将使用默认模板: {template_id}")
            
        logger.info(f"导出学生: {student_ids}, 模板ID: {template_id}, 使用内置默认模板: {use_default_template}, 设置: {settings}")
            
        # 使用默认设置补充缺失的设置
        default_settings = {
            'schoolYear': '2023-2024',
            'semester': '1',  # 1表示第一学期，2表示第二学期
            'fileNameFormat': 'id_name'  # id_name, name_id, id, name
        }
        
        for key, value in default_settings.items():
            if key not in settings or not settings[key]:
                settings[key] = value
                
        # 初始化报告导出器
        try:
            from utils.report_exporter import ReportExporter
            exporter = ReportExporter()
            logger.info("初始化ReportExporter成功")
        except Exception as e:
            logger.error(f"初始化报告导出器失败: {str(e)}")
            return jsonify({'status': 'error', 'message': f'导出报告失败: {str(e)}'})
        
        # 检查模板是否存在
        template_id = data.get('templateId', '泉州东海湾实验学校综合素质发展报告单')
        template_path = exporter.get_template_path(template_id)
        logger.info(f"使用模板: {template_id}, 路径: {template_path}")
        
        if not os.path.exists(template_path):
            logger.warning(f"模板文件不存在: {template_path}")
            if not exporter.has_default_backup:
                return jsonify({'status': 'error', 'message': f'模板不存在: {template_id}'})
                
        # 创建临时目录存放所有导出文件
        import tempfile
        import zipfile
        
        with tempfile.TemporaryDirectory() as temp_base_dir:
            # 为每个班级导出报告
            all_class_results = {}
            
            # 获取数据库连接
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            
            for class_info in selected_classes:
                class_id = class_info['id']
                class_name = class_info['name']
                
                logger.info(f"开始处理班级: {class_name} (ID: {class_id})")
                
                try:
                    # 查询班级学生数据
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM students WHERE class_id = ? ORDER BY CAST(id AS INTEGER)', (class_id,))
                    students = [dict(row) for row in cursor.fetchall()]
                    
                    if not students:
                        logger.warning(f"班级 {class_name} 没有学生数据，跳过")
                        continue
                        
                    logger.info(f"班级 {class_name} 找到 {len(students)} 名学生")
                    
                    # 查询学生评语
                    comments_dict = {}
                    for student in students:
                        student_id = student['id']
                        student_name = student['name']
                        comments = student.get('comments', '')
                        
                        comments_dict[student_id] = {
                            'studentId': student_id,
                            'studentName': student_name,
                            'content': comments
                        }
                    
                    # 查询学生成绩
                    grades_dict = {}
                    for student in students:
                        student_id = student['id']
                        try:
                            grade_fields = ['daof', 'yuwen', 'shuxue', 'yingyu', 'laodong', 'tiyu', 
                                          'yinyue', 'meishu', 'kexue', 'zonghe', 'xinxi', 'shufa']
                            grade_data = {}
                            for field in grade_fields:
                                if field in student:
                                    grade_data[field] = student[field]
                            
                            grades_dict[student_id] = {'grades': grade_data}
                        except Exception as e:
                            logger.warning(f"获取学生 {student_id} 成绩时出错: {str(e)}")
                            grades_dict[student_id] = {'grades': {}}
                    
                    # 添加班级名称到设置中，用于模板替换
                    class_settings = settings.copy()
                    class_settings['className'] = class_name
                    
                    # 导出班级报告
                    success, result = exporter.export_reports(
                        students=students,
                        comments=comments_dict,
                        grades=grades_dict,
                        template_id=template_id,
                        settings=class_settings
                    )
                    
                    if success:
                        # 创建班级目录
                        class_dir = os.path.join(temp_base_dir, class_name)
                        os.makedirs(class_dir, exist_ok=True)
                        
                        if export_type == 'word':
                            # Word格式直接保存ZIP文件
                            zip_path = os.path.join(class_dir, f"{class_name}_Word报告.zip")
                            with open(zip_path, 'wb') as f:
                                f.write(result)
                            all_class_results[class_name] = {'word_zip': zip_path}
                            
                        elif export_type == 'pdf':
                            # PDF格式需要转换
                            word_zip_path = os.path.join(class_dir, f"{class_name}_临时Word.zip")
                            with open(word_zip_path, 'wb') as f:
                                f.write(result)
                            
                            # 解压Word文件并转换为PDF
                            word_extract_dir = os.path.join(class_dir, "word_files")
                            os.makedirs(word_extract_dir, exist_ok=True)
                            
                            with zipfile.ZipFile(word_zip_path, 'r') as zipf:
                                zipf.extractall(word_extract_dir)
                            
                            # 转换DOCX为PDF
                            pdf_files = []
                            docx_files = [f for f in os.listdir(word_extract_dir) if f.endswith('.docx')]
                            
                            if pdf_organization == 'separate':
                                # 按班级分别创建文件夹
                                individual_pdf_dir = os.path.join(class_dir, "单独PDF")
                                os.makedirs(individual_pdf_dir, exist_ok=True)
                                
                                for docx_file in docx_files:
                                    docx_path = os.path.join(word_extract_dir, docx_file)
                                    pdf_file = docx_file.replace('.docx', '.pdf')
                                    pdf_path = os.path.join(individual_pdf_dir, pdf_file)
                                    
                                    if convert_docx_to_pdf(docx_path, pdf_path):
                                        pdf_files.append(pdf_path)
                                
                                # 合并PDF
                                if pdf_files:
                                    merged_pdf_path = os.path.join(class_dir, f"{class_name}_合并报告.pdf")
                                    if merge_pdfs(pdf_files, merged_pdf_path):
                                        all_class_results[class_name] = {
                                            'merged_pdf': merged_pdf_path,
                                            'individual_pdfs': pdf_files
                                        }
                                    else:
                                        logger.warning(f"班级 {class_name} PDF合并失败")
                                        all_class_results[class_name] = {'individual_pdfs': pdf_files}
                                else:
                                    logger.warning(f"班级 {class_name} 没有可合并的PDF文件")
                            else:
                                # 所有PDF放在同一文件夹
                                for docx_file in docx_files:
                                    docx_path = os.path.join(word_extract_dir, docx_file)
                                    pdf_file = f"{class_name}_{docx_file.replace('.docx', '.pdf')}"
                                    pdf_path = os.path.join(class_dir, pdf_file)
                                    
                                    if convert_docx_to_pdf(docx_path, pdf_path):
                                        pdf_files.append(pdf_path)
                                
                                all_class_results[class_name] = {'individual_pdfs': pdf_files}
                            
                            # 清理临时文件
                            os.remove(word_zip_path)
                            import shutil
                            shutil.rmtree(word_extract_dir)
                        
                        logger.info(f"班级 {class_name} 导出成功")
                    else:
                        logger.error(f"班级 {class_name} 导出失败: {result}")
                        
                except Exception as e:
                    logger.error(f"处理班级 {class_name} 时出错: {str(e)}")
                    continue
            
            conn.close()
            
            # 创建最终的ZIP包
            final_zip_path = os.path.join(temp_base_dir, f"班级报告_{export_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
            
            with zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_DEFLATED) as final_zip:
                for root, dirs, files in os.walk(temp_base_dir):
                    for file in files:
                        if file.endswith(('.zip', '.pdf', '.docx')):
                            file_path = os.path.join(root, file)
                            # 计算相对路径
                            arcname = os.path.relpath(file_path, temp_base_dir)
                            # 排除最终ZIP文件本身
                            if not arcname.endswith(f"班级报告_{export_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"):
                                final_zip.write(file_path, arcname)
            
            # 读取最终ZIP文件并返回
            with open(final_zip_path, 'rb') as f:
                zip_data = f.read()
            
            # 设置响应头
            response = make_response(zip_data)
            response.headers['Content-Type'] = 'application/zip'
            response.headers['Content-Disposition'] = f'attachment; filename="班级报告_{export_type}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.zip"'
            
            logger.info(f"班级导出完成，共处理 {len(all_class_results)} 个班级")
            return response
            
    except Exception as e:
        logger.error(f"按班级导出报告时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'导出失败: {str(e)}'}), 500

def merge_pdfs(pdf_files, output_path):
    """合并多个PDF文件为一个"""
    try:
        return jsonify({
            'status': 'error',
            'message': f'导出评语Excel时出错: {str(e)}'
        }), 500

# 按班级导出报告API
@comments_bp.route('/api/export-class-reports', methods=['POST'])
def api_export_class_reports():
    """管理员按班级批量导出报告"""
    try:
        # 检查用户是否已登录且为管理员
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            logger.warning("未登录用户尝试按班级导出报告")
            return jsonify({'status': 'error', 'message': '您需要登录后才能导出报告', 'code': 'login_required'}), 401
            
        if not current_user.is_admin:
            logger.warning(f"非管理员用户 {current_user.username} 尝试按班级导出报告")
            return jsonify({'status': 'error', 'message': '只有管理员可以按班级导出报告'}), 403
            
        # 获取请求数据
        data = request.get_json()
        
        # 验证请求数据
        selected_classes = data.get('classes', [])
        settings = data.get('settings', {})
        
        if not selected_classes:
            return jsonify({'status': 'error', 'message': '未选择任何班级'})
            
        logger.info(f"管理员 {current_user.username} 开始按班级导出报告，选择了 {len(selected_classes)} 个班级")
        
        # 获取导出类型和PDF组织方式
        export_type = settings.get('exportType', 'word')
        pdf_organization = settings.get('pdfOrganization', 'separate')
        
        # 使用默认设置补充缺失的设置
        default_settings = {
            'schoolYear': '2023-2024',
            'semester': '1',
            'fileNameFormat': 'id_name'
        }
        
        for key, value in default_settings.items():
            if key not in settings or not settings[key]:
                settings[key] = value
                
        # 初始化报告导出器
        try:
            from utils.report_exporter import ReportExporter
            exporter = ReportExporter()
            logger.info("初始化ReportExporter成功")
        except Exception as e:
            logger.error(f"初始化报告导出器失败: {str(e)}")
            return jsonify({'status': 'error', 'message': f'导出报告失败: {str(e)}'})
        
        # 检查模板是否存在