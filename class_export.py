# -*- coding: utf-8 -*-
"""
班级导出模块 - 管理员按班级批量导出报告功能
"""

import os
import sqlite3
import tempfile
import zipfile
import datetime
import logging
import traceback
from flask import Blueprint, request, jsonify, make_response
from flask_login import login_required, current_user

# 配置日志
logger = logging.getLogger(__name__)

# 创建蓝图
class_export_bp = Blueprint('class_export', __name__)

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def merge_pdfs(pdf_files, output_path):
    """合并多个PDF文件为一个"""
    try:
        from PyPDF2 import PdfMerger
        
        merger = PdfMerger()
        
        for pdf_file in pdf_files:
            if os.path.exists(pdf_file):
                merger.append(pdf_file)
        
        with open(output_path, 'wb') as output_file:
            merger.write(output_file)
        
        merger.close()
        logger.info(f"成功合并 {len(pdf_files)} 个PDF文件到 {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"合并PDF文件时出错: {str(e)}")
        return False

def convert_docx_to_pdf(input_file, output_file, request_id=None):
    """转换DOCX文件为PDF"""
    try:
        import platform
        system = platform.system()
        
        if system == "Windows":
            # Windows系统使用COM接口转换
            word = None
            doc = None
            try:
                import pythoncom
                from win32com.client import Dispatch
                
                pythoncom.CoInitialize()
                word = Dispatch("Word.Application")
                word.Visible = False
                word.DisplayAlerts = False  # 禁用弹窗
                
                doc = word.Documents.Open(input_file)
                doc.SaveAs(output_file, FileFormat=17)  # 17表示PDF格式
                
                logger.info(f"成功转换PDF: {os.path.basename(input_file)} -> {os.path.basename(output_file)}")
                return True
                
            except Exception as e:
                logger.error(f"Windows PDF转换失败: {str(e)}")
                return False
            finally:
                # 确保资源正确释放
                try:
                    if doc is not None:
                        doc.Close(SaveChanges=False)
                        logger.debug(f"文档已关闭: {os.path.basename(input_file)}")
                except Exception as e:
                    logger.warning(f"关闭文档时出错: {str(e)}")
                
                try:
                    if word is not None:
                        word.Quit()
                        logger.debug("Word应用程序已退出")
                except Exception as e:
                    logger.warning(f"退出Word应用程序时出错: {str(e)}")
                
                try:
                    pythoncom.CoUninitialize()
                    logger.debug("COM环境已释放")
                except Exception as e:
                    logger.warning(f"释放COM环境时出错: {str(e)}")
                
        elif system == "Linux":
            # Linux系统使用LibreOffice转换
            try:
                import subprocess
                
                # 使用unoconv转换
                result = subprocess.run([
                    'unoconv', '-f', 'pdf', '-o', output_file, input_file
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    logger.info(f"成功转换PDF: {os.path.basename(input_file)} -> {os.path.basename(output_file)}")
                    return True
                else:
                    logger.error(f"unoconv转换失败: {result.stderr}")
                    return False
                    
            except Exception as e:
                logger.error(f"Linux PDF转换失败: {str(e)}")
                return False
                
        else:
            logger.error(f"不支持的操作系统: {system}")
            return False
            
    except Exception as e:
        logger.error(f"PDF转换出错: {str(e)}")
        return False

def get_teacher_name(class_id):
    """获取班级对应的班主任姓名"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT u.username FROM users u WHERE u.class_id = ? AND u.is_admin = 0', (class_id,))
        result = cursor.fetchone()
        conn.close()
        return result['username'] if result else '未分配班主任'
    except Exception as e:
        logger.error(f"获取班级 {class_id} 班主任姓名时出错: {str(e)}")
        return '未分配班主任'

# 导入websocket_progress函数来更新进度
def websocket_progress(message, percent=None, request_id=None):
    """更新导出进度信息"""
    try:
        # 从comments模块导入进度更新函数
        from comments import websocket_progress as update_progress
        return update_progress(message, percent, request_id)
    except ImportError:
        logger.warning("无法导入进度更新函数")
        logger.info(f"进度更新: {message} ({percent}%)")

def check_export_cancelled(request_id):
    """检查导出是否被取消"""
    if not request_id:
        return False
    
    try:
        from comments import active_export_requests, export_requests_lock
        with export_requests_lock:
            request_info = active_export_requests.get(request_id)
            if request_info and request_info.get('cancelled'):
                logger.info(f"检测到导出取消请求: {request_id}")
                return True
        return False
    except ImportError:
        return False

def format_elapsed_time(start_time):
    """格式化耗时"""
    if not start_time:
        return ''
    
    elapsed = datetime.datetime.now() - start_time
    elapsed_seconds = int(elapsed.total_seconds())
    
    if elapsed_seconds < 60:
        return f"{elapsed_seconds}秒"
    else:
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        return f"{minutes}分{seconds}秒"

@class_export_bp.route('/api/export-class-reports', methods=['POST'])
@login_required
def api_export_class_reports():
    """管理员按班级批量导出报告"""
    request_id = request.headers.get('X-Export-Request-ID')
    
    try:
        # 检查用户是否为管理员
        if not current_user.is_admin:
            logger.warning(f"非管理员用户 {current_user.username} 尝试按班级导出报告")
            return jsonify({'status': 'error', 'message': '只有管理员可以按班级导出报告'}), 403
            
        # 获取请求数据
        data = request.get_json()
        
        # 验证请求数据
        selected_classes = data.get('classes', [])
        settings = data.get('settings', {})
        request_id = data.get('request_id')
        
        if not selected_classes:
            return jsonify({'status': 'error', 'message': '未选择任何班级'})
            
        logger.info(f"管理员 {current_user.username} 开始按班级导出报告，选择了 {len(selected_classes)} 个班级")
        
        # 记录开始时间
        start_time = datetime.datetime.now()
        
        # 更新初始进度
        websocket_progress(f"[5%] 开始导出 {len(selected_classes)} 个班级的报告...", 5, request_id)
        
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
        
        # 更新进度
        websocket_progress("[10%] 初始化报告导出器...", 10, request_id)
        
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
        
        # 更新进度
        websocket_progress("[15%] 准备导出文件...", 15, request_id)
        
        # 创建临时目录存放所有导出文件
        with tempfile.TemporaryDirectory() as temp_base_dir:
            # 为每个班级导出报告
            all_class_results = {}
            
            # 获取数据库连接
            conn = get_db_connection()
            
            total_classes = len(selected_classes)
            for class_index, class_info in enumerate(selected_classes):
                # 检查是否被取消
                if check_export_cancelled(request_id):
                    websocket_progress("导出已取消", 0, request_id)
                    logger.info(f"班级导出在处理第 {class_index + 1} 个班级时被取消")
                    return jsonify({'status': 'cancelled', 'message': '导出已取消'})
                
                class_id = class_info['id']
                class_name = class_info['name']
                
                # 更新进度 - 显示更详细的信息
                progress = 15 + (class_index / total_classes) * 70  # 15%-85%
                websocket_progress(f"[{progress:.0f}%] 正在处理班级: {class_name} ({class_index + 1}/{total_classes})", progress, request_id)
                
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
                    
                    # 更新详细进度
                    websocket_progress(f"[{progress:.0f}%] 班级 {class_name}: 正在准备 {len(students)} 名学生的数据...", progress, request_id)
                    
                    # 查询学生评语
                    comments_dict = {}
                    for student_index, student in enumerate(students):
                        # 检查是否被取消
                        if check_export_cancelled(request_id):
                            websocket_progress("导出已取消", 0, request_id)
                            logger.info(f"班级 {class_name} 导出在处理学生数据时被取消")
                            return jsonify({'status': 'cancelled', 'message': '导出已取消'})
                        
                        student_id = student['id']
                        student_name = student['name']
                        comments = student.get('comments', '')
                        
                        # 显示学生处理进度
                        if student_index % 5 == 0:  # 每5个学生更新一次进度
                            student_progress = progress + (student_index / len(students)) * 5  # 在当前进度基础上细分
                            websocket_progress(f"[{student_progress:.0f}%] 班级 {class_name}: 正在处理学生 {student_name} ({student_index + 1}/{len(students)})", progress, request_id)
                        
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
                    
                    # 获取班级对应的班主任姓名
                    websocket_progress(f"[{progress:.0f}%] 班级 {class_name}: 正在获取班主任信息...", progress, request_id)
                    teacher_name = get_teacher_name(class_id)
                    logger.info(f"班级 {class_name} 的班主任: {teacher_name}")
                    
                    # 添加班级名称和班主任信息到设置中，用于模板替换
                    class_settings = settings.copy()
                    class_settings['className'] = class_name
                    class_settings['teacherName'] = teacher_name  # 关键：设置班主任签名
                    
                    # 检查是否被取消
                    if check_export_cancelled(request_id):
                        websocket_progress("导出已取消", 0, request_id)
                        logger.info(f"班级 {class_name} 导出在生成报告前被取消")
                        return jsonify({'status': 'cancelled', 'message': '导出已取消'})
                    
                    # 更新进度 - 开始生成报告
                    websocket_progress(f"[{progress:.0f}%] 班级 {class_name}: 正在生成 {len(students)} 份报告...", progress, request_id)
                    
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
                            
                            websocket_progress(f"[{progress:.0f}%] 班级 {class_name}: 正在转换 {len(docx_files)} 个Word文档为PDF...", progress, request_id)
                            
                            if pdf_organization == 'separate':
                                # 按班级分别创建文件夹
                                individual_pdf_dir = os.path.join(class_dir, "单独PDF")
                                os.makedirs(individual_pdf_dir, exist_ok=True)
                                
                                for docx_index, docx_file in enumerate(docx_files):
                                    # 检查是否被取消
                                    if check_export_cancelled(request_id):
                                        websocket_progress("导出已取消", 0, request_id)
                                        logger.info(f"班级 {class_name} 导出在PDF转换时被取消")
                                        return jsonify({'status': 'cancelled', 'message': '导出已取消'})
                                    
                                    # 显示PDF转换进度
                                    pdf_progress = progress + (docx_index / len(docx_files)) * 10  # 在当前进度基础上细分
                                    websocket_progress(f"[{pdf_progress:.0f}%] 班级 {class_name}: 正在转换PDF {docx_file} ({docx_index + 1}/{len(docx_files)})", progress, request_id)
                                    
                                    docx_path = os.path.join(word_extract_dir, docx_file)
                                    pdf_file = docx_file.replace('.docx', '.pdf')
                                    pdf_path = os.path.join(individual_pdf_dir, pdf_file)
                                    
                                    if convert_docx_to_pdf(docx_path, pdf_path):
                                        pdf_files.append(pdf_path)
                                
                                # 合并PDF
                                if pdf_files:
                                    # 检查是否被取消
                                    if check_export_cancelled(request_id):
                                        websocket_progress("导出已取消", 0, request_id)
                                        logger.info(f"班级 {class_name} 导出在PDF合并前被取消")
                                        return jsonify({'status': 'cancelled', 'message': '导出已取消'})
                                    
                                    websocket_progress(f"[{progress:.0f}%] 班级 {class_name}: 正在合并 {len(pdf_files)} 个PDF文件...", progress, request_id)
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
            
            # 最后检查是否被取消
            if check_export_cancelled(request_id):
                websocket_progress("导出已取消", 0, request_id)
                logger.info("班级导出在最终打包前被取消")
                return jsonify({'status': 'cancelled', 'message': '导出已取消'})
            
            # 更新进度
            websocket_progress(f"[90%] 正在打包 {len(all_class_results)} 个班级的导出文件...", 90, request_id)
            
            # 创建最终的ZIP包
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            final_zip_path = os.path.join(temp_base_dir, f"class_reports_{export_type}_{timestamp}.zip")
            
            with zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_DEFLATED) as final_zip:
                for root, dirs, files in os.walk(temp_base_dir):
                    for file in files:
                        if file.endswith(('.zip', '.pdf', '.docx')):
                            file_path = os.path.join(root, file)
                            # 计算相对路径
                            arcname = os.path.relpath(file_path, temp_base_dir)
                            # 排除最终ZIP文件本身
                            if not file.endswith(f"class_reports_{export_type}_{timestamp}.zip"):
                                final_zip.write(file_path, arcname)
            
            # 更新完成进度
            total_elapsed = format_elapsed_time(start_time)
            completion_message = f"[100%] 导出完成！成功处理 {len(all_class_results)} 个班级"
            if total_elapsed:
                completion_message += f" (总耗时: {total_elapsed})"
            websocket_progress(completion_message, 100, request_id)
            
            # 读取最终ZIP文件并返回
            with open(final_zip_path, 'rb') as f:
                zip_data = f.read()
            
            # 设置响应头
            response = make_response(zip_data)
            response.headers['Content-Type'] = 'application/zip'
            response.headers['Content-Disposition'] = f'attachment; filename="class_reports_{export_type}_{timestamp}.zip"'
            
            logger.info(f"班级导出完成，共处理 {len(all_class_results)} 个班级，文件大小: {len(zip_data)} 字节")
            
            # 清理进度信息（标记为完成）
            try:
                from comments import active_export_requests, export_requests_lock
                if request_id:
                    with export_requests_lock:
                        if request_id in active_export_requests:
                            active_export_requests[request_id]['status'] = 'completed'
                            active_export_requests[request_id]['completed_at'] = datetime.datetime.now()
            except ImportError:
                pass
            
            return response
            
    except Exception as e:
        logger.error(f"按班级导出报告时出错: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 更新错误进度
        websocket_progress(f"导出失败: {str(e)}", 0, request_id)
        
        # 清理进度信息
        try:
            from comments import active_export_requests, export_requests_lock
            if request_id:
                with export_requests_lock:
                    if request_id in active_export_requests:
                        active_export_requests[request_id]['status'] = 'error'
                        active_export_requests[request_id]['error'] = str(e)
        except ImportError:
            pass
        
        return jsonify({'status': 'error', 'message': f'导出失败: {str(e)}'}), 500 