# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, send_from_directory, current_app, make_response
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

# 创建评语管理蓝图
comments_bp = Blueprint('comments', __name__)
logger = logging.getLogger(__name__)

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
        max_length = int(data.get('max_length', 260))
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
                max_length=max_length
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
                "class_id": class_id
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
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': '未登录'}), 401
            
        # 如果是班主任，检查是否有权限导出指定班级
        if not current_user.is_admin and current_user.class_id:
            # 如果未指定班级，则使用班主任自己的班级
            if not class_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT class FROM students WHERE class_id = ? LIMIT 1', (current_user.class_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    class_name = result['class']
                    logger.info(f"未指定班级，使用班主任班级: {class_name}")
            # 指定了班级，检查是否有权限
            elif class_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT class FROM students WHERE class_id = ? LIMIT 1', (current_user.class_id,))
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
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': '未登录'}), 401
            
        # 如果是班主任，检查是否有权限预览指定班级
        if not current_user.is_admin and current_user.class_id:
            # 如果未指定班级，则使用班主任自己的班级
            if not class_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT class FROM students WHERE class_id = ? LIMIT 1', (current_user.class_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    class_name = result['class']
                    logger.info(f"未指定班级，使用班主任班级: {class_name}")
            # 指定了班级，检查是否有权限
            elif class_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT class FROM students WHERE class_id = ? LIMIT 1', (current_user.class_id,))
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

# 导出报告API
@comments_bp.route('/api/export-reports', methods=['POST'])
def api_export_reports():
    try:
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
        template_path = exporter.get_template_path(template_id)
        logger.info(f"模板路径: {template_path}, 模板是否存在: {os.path.exists(template_path)}")
        if not os.path.exists(template_path):
            return jsonify({'status': 'error', 'message': f'模板不存在: {template_id}'})
                
        # 查询学生数据
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 准备SQL查询
        placeholders = ','.join(['?' for _ in student_ids])
        
        # 添加班级ID筛选，确保班主任只能导出本班级的学生
        if current_user.is_admin:
            # 管理员可以导出所有学生
            query = f'SELECT * FROM students WHERE id IN ({placeholders})'
            params = student_ids
        else:
            # 班主任只能导出本班级学生
            query = f'SELECT * FROM students WHERE id IN ({placeholders}) AND class_id = ?'
            params = student_ids + [current_user.class_id]
            logger.info(f"班主任模式：只导出班级ID为 {current_user.class_id} 的学生")
        
        # 执行查询
        cursor.execute(query, params)
        students_rows = cursor.fetchall()
        
        # 转换成字典列表，确保字段非空
        students = []
        for row in students_rows:
            student_dict = dict(row)
            # 确保关键字段非空 - 这里补充空字符串而不是None
            for key in ['id', 'name', 'gender', 'class']:
                if key not in student_dict or student_dict[key] is None:
                    student_dict[key] = ''
            students.append(student_dict)
            
        # 如果没有找到任何学生，返回错误
        if not students:
            logger.error(f"未找到任何符合条件的学生: {student_ids}")
            return jsonify({'status': 'error', 'message': '未找到所选学生数据，或者您没有权限导出这些学生的报告'})
            
        # 获取评语数据
        comments_dict = {}
        for student in students:
            student_id = str(student['id'])  # 确保是字符串
            # 评语直接从学生表中获取
            cursor.execute('SELECT comments FROM students WHERE id = ? AND class_id = ?', 
                          (student_id, student.get('class_id')))
            row = cursor.fetchone()
            if row and row['comments']:
                comments_dict[student_id] = {'content': row['comments']}
            else:
                comments_dict[student_id] = {'content': ''}
        
        # 获取成绩数据
        grades_dict = {}
        for student in students:
            student_id = str(student['id'])  # 确保是字符串
            
            try:
                # 尝试从grades表获取成绩
                cursor.execute('SELECT * FROM grades WHERE student_id = ?', (student_id,))
                grades_row = cursor.fetchone()
                
                if grades_row:
                    grades = dict(grades_row)
                    # 移除不需要的字段
                    if 'id' in grades: del grades['id']
                    if 'student_id' in grades: del grades['student_id']
                    grades_dict[student_id] = {'grades': grades}
                else:
                    # 尝试从students表获取成绩字段
                    cursor.execute('SELECT yuwen, shuxue, yingyu, daof, kexue, tiyu, yinyue, meishu, laodong, xinxi, zonghe, shufa FROM students WHERE id = ? AND class_id = ?', (student_id, student.get('class_id')))
                    grades_row = cursor.fetchone()
                    
                    if grades_row:
                        grades = dict(grades_row)
                        grades_dict[student_id] = {'grades': grades}
                    else:
                        # 都没有成绩数据，使用空成绩
                        grades_dict[student_id] = {'grades': {}}
            except sqlite3.OperationalError as e:
                # 处理表不存在或列不存在的情况
                logger.warning(f"获取成绩时出错: {str(e)}, 将使用空成绩数据")
                grades_dict[student_id] = {'grades': {}}
        
        # 关闭数据库连接
        conn.close()
        
        # 生成报告
        try:
            from utils.report_exporter import ReportExporter
            
            # 检查必要依赖
            try:
                import docxtpl
                import docx
                logger.info("依赖检查: docxtpl和docx库已安装")
                
                # 如果是PDF导出，检查PDF相关依赖
                if export_type == 'pdf':
                    try:
                        from docx2pdf import convert
                        logger.info("依赖检查: docx2pdf库已安装")
                    except ImportError as e:
                        logger.error(f"缺少PDF导出依赖: {str(e)}")
                        return jsonify({
                            'status': 'error', 
                            'message': f'PDF报告导出失败: 缺少必要依赖，请安装 docx2pdf 库'
                        })
            except ImportError as e:
                logger.error(f"缺少必要依赖: {str(e)}")
                return jsonify({
                    'status': 'error', 
                    'message': f'报告导出失败: 缺少必要依赖，请安装 python-docx 和 docxtpl 库'
                })
            
            logger.info(f"开始生成报告，学生数量: {len(students)}")
            logger.info(f"学生数据示例: {students[0] if students else '无'}")
            logger.info(f"评语数据: {comments_dict}")
            logger.info(f"成绩数据: {grades_dict}")
            
            exporter = ReportExporter()
            success, result = exporter.export_reports(
                students=students,
                comments=comments_dict,
                grades=grades_dict,
                template_id=template_id,
                settings=settings
            )
            
            if not success:
                logger.error(f"导出报告失败: {result}")
                return jsonify({'status': 'error', 'message': f'导出报告失败: {result}'})
            
            # 检查系统是否安装了Microsoft Word
            def check_word_installed():
                """检查系统是否安装了Microsoft Word"""
                logger.info("开始检查Microsoft Word是否安装")
                try:
                    # 根据操作系统类型采用不同的检测方法
                    system = platform.system()
                    logger.info(f"当前操作系统: {system}")
                    
                    if system == "Windows":
                        # Windows系统：尝试通过注册表检查
                        try:
                            import winreg
                            # 尝试打开Word注册表键
                            word_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Office\Word")
                            winreg.CloseKey(word_key)
                            logger.info("通过注册表确认Microsoft Word已安装")
                            return True
                        except ImportError:
                            logger.warning("无法导入winreg模块，将尝试通过COM接口检测Word")
                        except Exception as e:
                            logger.warning(f"无法通过注册表检测Word: {str(e)}")
                        
                        # 尝试通过COM接口创建Word实例
                        if PYTHONCOM_AVAILABLE:
                            try:
                                from win32com.client import Dispatch
                                pythoncom.CoInitialize()
                                word = Dispatch("Word.Application")
                                word.Quit()
                                pythoncom.CoUninitialize()
                                logger.info("通过COM接口确认Microsoft Word已安装")
                                return True
                            except Exception as e:
                                logger.error(f"通过COM接口检测Word失败: {str(e)}")
                                return False
                        else:
                            logger.warning("pythoncom模块不可用，无法通过COM接口检测Word")
                            return False
                    elif system == "Darwin":  # macOS
                        # 检查macOS上的Word应用位置
                        common_paths = [
                            "/Applications/Microsoft Word.app",
                            "/Applications/Microsoft Office/Microsoft Word.app"
                        ]
                        for path in common_paths:
                            if os.path.exists(path):
                                logger.info(f"在路径 {path} 找到Microsoft Word")
                                return True
                        logger.warning("在macOS上未找到Microsoft Word")
                        return False
                        
                    elif system == "Linux":
                        # Linux上可能使用LibreOffice
                        try:
                            import subprocess
                            result = subprocess.run(["which", "libreoffice"], capture_output=True, text=True)
                            if result.returncode == 0:
                                logger.info("在Linux上找到LibreOffice，可用于文档转换")
                                return True
                            else:
                                logger.warning("在Linux上未找到LibreOffice")
                                return False
                        except Exception as e:
                            logger.error(f"检查LibreOffice时出错: {str(e)}")
                            return False
                    else:
                        logger.warning(f"未知操作系统类型: {system}，无法确定Word安装状态")
                        return False
                except Exception as e:
                    logger.error(f"检查Word安装状态时出错: {str(e)}")
                    logger.error(traceback.format_exc())
                    return False

            # 如果是PDF导出，需要将Word文档转换为PDF
            if export_type == 'pdf':
                logging.info("开始PDF导出流程")
                try:
                    # 检查是否安装了Word
                    word_installed = check_word_installed()
                    if not word_installed:
                        logger.warning("系统中未检测到Microsoft Word，PDF转换可能失败")
                        # 继续尝试，因为可能有其他方式转换
                    else:
                        logger.info("检测到Microsoft Word，将继续PDF转换")
                    
                    # 保存原始Word文档结果作为回退
                    original_word_result = result
                    
                    # 创建临时目录解压ZIP文件
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # 检查请求是否已取消
                        if request_id and is_export_cancelled(request_id):
                            logger.info(f"PDF转换前检测到请求已取消: {request_id}")
                            return jsonify({
                                'status': 'warning',
                                'message': '导出操作已被用户取消'
                            })
                            
                        # 保存ZIP文件
                        zip_path = os.path.join(temp_dir, "word_reports.zip")
                        logger.info(f"保存ZIP文件到临时目录: {zip_path}")
                        with open(zip_path, 'wb') as f:
                            f.write(result)
                        
                        # 解压ZIP文件
                        extract_dir = os.path.join(temp_dir, "extracted")
                        os.makedirs(extract_dir, exist_ok=True)
                        logger.info(f"解压ZIP文件到: {extract_dir}")
                        
                        # 解压ZIP文件
                        with zipfile.ZipFile(zip_path, 'r') as zipf:
                            file_list = zipf.namelist()
                            logger.info(f"ZIP文件中包含的文件: {file_list}")
                            zipf.extractall(extract_dir)
                        
                        # 检查是否有docx文件
                        extracted_files = os.listdir(extract_dir)
                        logger.info(f"解压后的文件列表: {extracted_files}")
                        docx_files = [f for f in extracted_files if f.endswith('.docx')]
                        
                        if not docx_files:
                            logger.error("未找到任何.docx文件需要转换")
                            raise Exception("解压后未找到任何Word文档文件")
                            
                        # 再次检查请求是否已取消
                        if request_id and is_export_cancelled(request_id):
                            logger.info(f"解压后检测到请求已取消: {request_id}")
                            return jsonify({
                                'status': 'warning',
                                'message': '导出操作已被用户取消'
                            })
                            
                        # 创建PDF输出目录
                        pdf_dir = os.path.join(temp_dir, "pdf")
                        os.makedirs(pdf_dir, exist_ok=True)
                        logger.info(f"创建PDF输出目录: {pdf_dir}")
                        
                        # 设置转换计数器
                        total_files = len(docx_files)
                        successful_conversions = 0
                        
                        # 转换DOCX文件为PDF
                        pdf_files = []
                        for i, docx_file in enumerate(docx_files):
                            # 检查请求是否已取消
                            if request_id and is_export_cancelled(request_id):
                                logger.info(f"转换过程中检测到请求已取消: {request_id}")
                                return jsonify({
                                    'status': 'warning',
                                    'message': '导出操作已被用户取消'
                                })
                                
                            # 准备转换路径
                            docx_path = os.path.join(extract_dir, docx_file)
                            pdf_file = docx_file.replace('.docx', '.pdf')
                            pdf_path = os.path.join(pdf_dir, pdf_file)
                            
                            # 执行转换，添加重试逻辑
                            logger.info(f"开始转换 [{i+1}/{total_files}]: {docx_path} -> {pdf_path}")
                            
                            # 尝试最多3次转换
                            success = False
                            for attempt in range(3):
                                try:
                                    if attempt > 0:
                                        logger.info(f"重试第{attempt+1}次转换: {docx_file}")
                                    
                                    # 执行转换
                                    success = convert_docx_to_pdf(docx_path, pdf_path, request_id)
                                    
                                    if success:
                                        logger.info(f"转换成功 (尝试 {attempt+1}): {docx_file}")
                                        break
                                    else:
                                        logger.warning(f"转换失败 (尝试 {attempt+1}): {docx_file}")
                                except Exception as e:
                                    logger.error(f"转换异常 (尝试 {attempt+1}): {str(e)}")
                                    if attempt == 2:  # 最后一次尝试
                                        logger.error(f"转换 {docx_file} 的所有尝试均失败")
                            
                            if success and os.path.exists(pdf_path):
                                pdf_size = os.path.getsize(pdf_path)
                                if pdf_size > 0:
                                    logger.info(f"转换成功: {pdf_file} (大小: {pdf_size} 字节)")
                                    pdf_files.append(pdf_file)
                                    successful_conversions += 1
                                else:
                                    logger.warning(f"PDF文件大小为0: {pdf_file}")
                            else:
                                logger.warning(f"转换失败: {docx_file}")
                        
                        # 检查转换成功率
                        if len(pdf_files) == 0:
                            logger.error("没有成功转换的PDF文件")
                            raise Exception("未能成功转换任何PDF文件")
                        elif len(pdf_files) < total_files:
                            success_rate = (successful_conversions / total_files) * 100
                            logger.warning(f"部分文件转换失败: {successful_conversions}/{total_files} 成功 (成功率: {success_rate:.1f}%)")
                            # 如果成功率太低，可以考虑回退到Word格式
                            if success_rate < 50:
                                logger.error(f"成功率低于50%，回退到Word格式")
                                raise Exception(f"PDF转换成功率太低 ({success_rate:.1f}%)，回退到Word格式")
                        else:
                            logger.info(f"所有文件均成功转换: {successful_conversions}/{total_files}")
                            
                        # 再次检查请求是否已取消
                        if request_id and is_export_cancelled(request_id):
                            logger.info(f"转换完成后检测到请求已取消: {request_id}")
                            return jsonify({
                                'status': 'warning',
                                'message': '导出操作已被用户取消'
                            })
                            
                        # 创建PDF文件的ZIP
                        pdf_zip_path = os.path.join(temp_dir, "pdf_reports.zip")
                        logger.info(f"创建PDF ZIP文件: {pdf_zip_path}")
                        
                        with zipfile.ZipFile(pdf_zip_path, 'w') as zipf:
                            for pdf_file in pdf_files:
                                file_path = os.path.join(pdf_dir, pdf_file)
                                logger.info(f"添加PDF到ZIP: {file_path} -> {pdf_file}")
                                zipf.write(file_path, pdf_file)
                        
                        # 读取最终的ZIP文件
                        with open(pdf_zip_path, 'rb') as f:
                            result = f.read()
                            
                        logger.info(f"PDF转换成功，ZIP文件大小: {len(result)} 字节")
                        export_type = 'pdf'
                        
                except Exception as pdf_error:
                    # 检查是否是用户取消导致的错误
                    if isinstance(pdf_error, Exception) and "用户取消" in str(pdf_error):
                        logger.info("用户取消了PDF转换")
                        return jsonify({
                            'status': 'warning',
                            'message': '导出操作已被用户取消'
                        })
                        
                    # 记录转换失败详情
                    logger.error(f"PDF转换失败: {str(pdf_error)}")
                    logger.error(traceback.format_exc())
                    logger.info("将使用原始Word文档作为后备方案")
                    
                    # 回退到Word格式
                    export_type = 'word'
                    result = original_word_result
                    
                    # 如果这是直接下载模式，添加特殊头部
                    if os.environ.get('EXPORT_DIRECT_DOWNLOAD', '1') == '1':
                        response = make_response(result)
                        response.headers['Content-Type'] = 'application/zip'
                        response.headers['Content-Disposition'] = f'attachment; filename=student_reports_word_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
                        response.headers['X-PDF-Conversion-Failed'] = 'true'
                        response.headers['X-PDF-Conversion-Error'] = str(pdf_error)[:200]  # 限制错误消息长度
                        logger.info("返回带有PDF转换失败标记的Word文档")
                        return response
            
            # 直接返回文件
            if os.environ.get('EXPORT_DIRECT_DOWNLOAD', '1') == '1':
                logger.info("使用直接下载模式")
                response = make_response(result)
                response.headers['Content-Type'] = 'application/zip'
                file_ext = 'pdf' if export_type == 'pdf' else 'docx'
                response.headers['Content-Disposition'] = f'attachment; filename=student_reports_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
                return response
            
            # 保存导出文件
            file_ext = 'pdf' if export_type == 'pdf' else 'docx'
            export_filename = f"student_reports_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            export_path = os.path.join('exports', export_filename)
            
            # 确保exports目录存在
            os.makedirs('exports', exist_ok=True)
            
            # 写入文件
            with open(export_path, 'wb') as f:
                f.write(result)
            
            logger.info(f"报告生成成功，保存为: {export_path}")
            
            return jsonify({
                'status': 'ok',
                'filename': export_filename,
                'message': f'成功导出 {len(students)} 个学生的{export_type}报告'
            })
            
        except Exception as e:
            logger.error(f"导出报告时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'status': 'error', 'message': f'导出报告失败: {str(e)}'})
    except Exception as e:
        logger.error(f"导出报告请求处理出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'导出报告失败: {str(e)}'})

# 初始化评语模块
def init_comments(app):
    # 只注册下载评语导出文件的路由，不创建表
    @app.route('/download/exports/<path:filename>', methods=['GET'])
    def download_export(filename):
        EXPORTS_FOLDER = 'exports'
        app.logger.info(f"请求下载文件: {filename}, 从目录: {EXPORTS_FOLDER}")
        
        # 检查文件是否存在
        file_path = os.path.join(EXPORTS_FOLDER, filename)
        if not os.path.exists(file_path):
            app.logger.error(f"请求的文件不存在: {file_path}")
            return jsonify({
                'status': 'error',
                'message': '请求的文件不存在'
            }), 404
            
        # 发送文件
        try:
            return send_from_directory(EXPORTS_FOLDER, filename, as_attachment=True)
        except Exception as e:
            app.logger.error(f"发送文件时出错: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'发送文件时出错: {str(e)}'
            }), 500

@comments_bp.route('/api/students', methods=['GET'])
def get_students():
    """
    获取学生列表，如果是班主任则只返回其班级的学生
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取当前用户信息
        if not current_user.is_authenticated:
            return jsonify({'error': '未登录'}), 401
            
        # 如果是管理员，返回所有学生
        if current_user.is_admin:
            cursor.execute('SELECT * FROM students ORDER BY class, CAST(id AS INTEGER)')
        else:
            # 如果是班主任，只返回其班级的学生
            cursor.execute('SELECT * FROM students WHERE class_id = ? ORDER BY CAST(id AS INTEGER)', (current_user.class_id,))
            
        students = cursor.fetchall()
        conn.close()
        
        # 转换为字典列表
        students_list = []
        for student in students:
            student_dict = dict(student)
            students_list.append(student_dict)
            
        return jsonify({
            'status': 'ok',
            'students': students_list
        })
    except Exception as e:
        logger.error(f"获取学生列表时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'获取学生列表时出错: {str(e)}'}), 500
