# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, send_from_directory, current_app
import sqlite3
import os
import datetime
import traceback
import logging

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
    return conn

# 获取单个学生评语
@comments_bp.route('/api/comments/<student_id>', methods=['GET'], strict_slashes=False)
def get_student_comment(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, comments FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    conn.close()
    
    if not student:
        return jsonify({
            'status': 'error',
            'message': '未找到该学生'
        }), 404
    
    return jsonify({
        'status': 'ok',
        'comment': {
            'studentId': student['id'],
            'studentName': student['name'],
            'content': student['comments'] or ''
        }
    })

# 保存学生评语
@comments_bp.route('/api/comments', methods=['POST'], strict_slashes=False)
def save_student_comment():
    data = request.json
    
    if not data or 'studentId' not in data or 'content' not in data:
        return jsonify({
            'status': 'error',
            'message': '请提供学生ID和评语内容'
        }), 400
        
    student_id = data['studentId']
    content = data['content']
    append_mode = data.get('appendMode', False)
    
    logger.info(f"保存学生评语, 学生ID: {student_id}, 追加模式: {append_mode}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 先检查学生是否存在
    cursor.execute('SELECT id, comments FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return jsonify({
            'status': 'error',
            'message': '未找到该学生'
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
            
        # 更新学生评语
        cursor.execute('UPDATE students SET comments = ?, updated_at = ? WHERE id = ?', 
                      (updated_content, now, student_id))
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'message': '评语保存成功',
            'updatedContent': updated_content
        })
    except Exception as e:
        conn.rollback()
        logger.error(f"保存评语时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'保存评语时出错: {str(e)}'
        }), 500
    finally:
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 记录更新的学生数量
        updated_count = 0
        
        # 获取当前时间，但不再添加到评语中
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 对选中的每个学生更新评语
        for student_id in student_ids:
            # 查询学生当前评语
            cursor.execute('SELECT comments FROM students WHERE id = ?', (student_id,))
            student = cursor.fetchone()
            
            if not student:
                continue  # 跳过不存在的学生ID
            
            current_comment = student[0] or ''
            
            # 根据模式设置新评语
            if append_mode and current_comment:
                # 简化追加模式，直接添加到末尾
                new_comment = f"{current_comment.strip()}\n\n{content}"
            else:
                # 如果是替换模式或无评语，则直接使用新内容
                new_comment = content
            
            # 更新学生评语和更新时间
            cursor.execute('UPDATE students SET comments = ?, updated_at = ? WHERE id = ?', 
                          (new_comment, now, student_id))
            
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
        print("收到评语生成请求:", data)
        
        # 获取全局变量
        deepseek_api = current_app.config.get('deepseek_api')
        
        # 验证请求数据
        comment_generator = CommentGenerator(deepseek_api.api_key if deepseek_api else None)
        is_valid, error_msg = comment_generator.validate_request(data)
        if not is_valid:
            print("请求数据验证失败:", error_msg)
            return jsonify({
                "status": "error",
                "message": error_msg
            })
        
        # 获取学生信息
        student_id = data.get('student_id') or data.get('studentId')
        if not student_id:
            print("缺少学生ID")
            return jsonify({
                "status": "error",
                "message": "缺少学生ID"
            })
            
        # 从数据库获取学生信息
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name, gender FROM students WHERE id = ?', (student_id,))
        student = cursor.fetchone()
        conn.close()
        
        if not student:
            print(f"未找到学生: {student_id}")
            return jsonify({
                "status": "error",
                "message": f"未找到ID为 {student_id} 的学生"
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
        max_length = int(data.get('max_length', 200))
        additional_instructions = data.get('additional_instructions', '')
        
        # 如果有额外指令，添加到学生信息中
        if additional_instructions:
            student_info['additional_instructions'] = additional_instructions
        
        # 记录正在为哪个学生生成评语
        print(f"正在为学生 {student_info['name']}(ID: {student_id}) 生成评语")
        
        # 生成评语
        result = comment_generator.generate_comment(
            student_info=student_info,
            style=style,
            tone=tone,
            max_length=max_length
        )
        
        print(f"评语生成结果(学生ID: {student_id}):", result)
        
        # 返回结果
        if result["status"] == "ok":
            return jsonify({
                "status": "ok",
                "comment": result["comment"],
                "student_id": student_id
            })
        else:
            return jsonify({
                "status": "error",
                "message": result["message"],
                "student_id": student_id
            })
                
    except Exception as e:
        print("生成评语时出错:", str(e))
        print(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": f"生成评语时出错: {str(e)}"
        })

# 导出评语为PDF
@comments_bp.route('/api/export-comments-pdf', methods=['GET'])
def api_export_comments_pdf():
    # 获取班级参数（可选）
    class_name = request.args.get('class')
    logger.info(f"收到导出评语PDF请求，班级: {class_name}")
    
    try:
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
    
    # 调用预览函数
    result = generate_preview_html(class_name)
    
    if result['status'] == 'ok':
        # 返回HTML内容而不是JSON
        return result['html']
    else:
        return jsonify(result), 500

# 初始化评语模块
def init_comments(app):
    # 注册下载评语导出文件的路由
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