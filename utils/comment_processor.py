#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
评语处理模块：提供批量编辑、PDF导出和打印预览功能
"""

import os
import time
import logging
import sqlite3
import traceback
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入reportlab库，如果不存在则设置标志
REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, PageBreak
    REPORTLAB_AVAILABLE = True
    logger.info("ReportLab库已成功导入")
except ImportError:
    logger.error("无法导入ReportLab库，PDF生成功能将不可用")
    logger.error("请使用以下命令安装ReportLab: pip install reportlab")

# 数据库连接
DATABASE = 'students.db'

# PDF导出目录
EXPORTS_FOLDER = 'exports'
os.makedirs(EXPORTS_FOLDER, exist_ok=True)

# 字体配置
FONTS_FOLDER = 'utils/fonts'
os.makedirs(FONTS_FOLDER, exist_ok=True)

# 注册中文字体
def register_fonts():
    """注册中文字体，确保PDF可以正确显示中文"""
    if not REPORTLAB_AVAILABLE:
        logger.error("ReportLab库未安装，无法注册字体")
        return False
        
    try:
        # 使用思源宋体作为默认字体
        if os.path.exists(f'{FONTS_FOLDER}/SimSun.ttf'):
            pdfmetrics.registerFont(TTFont('SimSun', f'{FONTS_FOLDER}/SimSun.ttf'))
            logger.info("成功注册中文字体(SimSun.ttf)")
            return True
        elif os.path.exists(f'{FONTS_FOLDER}/SourceHanSerifCN-Regular.otf'):
            # 尝试使用思源宋体
            pdfmetrics.registerFont(TTFont('SimSun', f'{FONTS_FOLDER}/SourceHanSerifCN-Regular.otf'))
            logger.info("成功注册思源宋体")
            return True
        else:
            # 尝试找一个系统默认字体作为备用
            logger.warning("在字体目录中未找到字体文件，尝试使用系统字体...")
            
            # 尝试Windows系统字体
            if os.path.exists('C:/Windows/Fonts/simsun.ttc'):
                pdfmetrics.registerFont(TTFont('SimSun', 'C:/Windows/Fonts/simsun.ttc'))
                logger.info("成功注册Windows系统字体(simsun.ttc)")
                return True
                
            # 尝试macOS系统字体
            elif os.path.exists('/System/Library/Fonts/PingFang.ttc'):
                pdfmetrics.registerFont(TTFont('SimSun', '/System/Library/Fonts/PingFang.ttc'))
                logger.info("成功注册macOS系统字体(PingFang.ttc)")
                return True
                
            # 尝试使用Helvetica作为备用（不支持中文，但至少能生成PDF）
            else:
                logger.error("无法找到合适的中文字体，将使用默认字体")
                # 使用内置字体，不需要注册
                return True
    except Exception as e:
        logger.error(f"注册字体时出错: {e}")
        logger.error("PDF中可能无法正确显示中文，但将尝试使用默认字体")
        return False

# 获取数据库连接
def get_db_connection():
    """获取SQLite数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# 批量编辑评语
def batch_update_comments(comment_content, append_mode=True):
    """
    批量更新所有学生的评语
    
    参数:
    - comment_content: 要添加的评语内容
    - append_mode: 是否为追加模式（True表示追加到现有评语后，False表示替换现有评语）
    
    返回:
    - 更新结果和统计信息
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取所有学生
        cursor.execute('SELECT id, name, comments FROM students')
        students = cursor.fetchall()
        
        if not students:
            return {
                'status': 'error',
                'message': '没有找到任何学生'
            }
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated_count = 0
        
        for student in students:
            student_id = student['id']
            current_comment = student['comments'] or ''
            
            # 根据模式决定如何更新评语
            if append_mode and current_comment:
                # 追加模式：在原有评语后添加新内容
                updated_content = f"{current_comment}\n\n--- {now} 批量更新 ---\n{comment_content}"
            else:
                # 替换模式：直接使用新评语
                updated_content = comment_content
                
            # 更新数据库
            cursor.execute('UPDATE students SET comments = ?, updated_at = ? WHERE id = ?',
                          (updated_content, now, student_id))
            updated_count += 1
        
        conn.commit()
        
        return {
            'status': 'ok',
            'message': f'成功更新 {updated_count} 名学生的评语',
            'updated_count': updated_count
        }
    
    except Exception as e:
        conn.rollback()
        logger.error(f"批量更新评语时出错: {e}")
        return {
            'status': 'error',
            'message': f'批量更新评语时出错: {str(e)}'
        }
    finally:
        conn.close()

# 生成评语PDF
def generate_comments_pdf(class_name=None):
    """
    生成评语PDF文档
    
    参数:
    - class_name: 班级名称（可选，如果提供则只导出该班级的学生评语）
    
    返回:
    - PDF文件路径
    """
    # 检查是否可用ReportLab
    if not REPORTLAB_AVAILABLE:
        logger.error("导出PDF失败: ReportLab库未安装")
        return {
            'status': 'error',
            'message': 'PDF生成功能不可用。请安装ReportLab库: pip install reportlab'
        }
    
    try:
        # 检查exports目录是否存在且可写
        if not os.path.exists(EXPORTS_FOLDER):
            os.makedirs(EXPORTS_FOLDER, exist_ok=True)
            logger.info(f"创建导出目录: {EXPORTS_FOLDER}")
        
        if not os.access(EXPORTS_FOLDER, os.W_OK):
            logger.error(f"导出目录无写入权限: {EXPORTS_FOLDER}")
            return {
                'status': 'error',
                'message': f'无法写入导出目录，请检查权限: {EXPORTS_FOLDER}'
            }
            
        # 确保注册了中文字体
        font_registered = register_fonts()
        if not font_registered:
            logger.warning("字体注册出现问题，PDF可能无法正确显示中文")
        
        # 获取所有学生数据
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 使用与打印预览相同的查询
            if class_name:
                cursor.execute('SELECT id, name, gender, class, comments, updated_at FROM students WHERE class = ? ORDER BY CAST(id AS INTEGER)', (class_name,))
            else:
                cursor.execute('SELECT id, name, gender, class, comments, updated_at FROM students ORDER BY class, CAST(id AS INTEGER)')
                
            students = cursor.fetchall()
            if not students:
                logger.warning("未找到学生数据，无法生成PDF")
                return {
                    'status': 'error',
                    'message': '没有找到学生数据，无法生成PDF文件'
                }
                
            # 转换为字典列表，与打印预览保持一致
            students_dict = []
            for s in students:
                student_dict = {}
                for key in s.keys():
                    student_dict[key] = s[key]
                students_dict.append(student_dict)
                
            # 按班级分组学生
            students_by_class = {}
            for student in students_dict:
                class_name = student.get('class') or '未分班'
                if class_name not in students_by_class:
                    students_by_class[class_name] = []
                students_by_class[class_name].append(student)
                
            if not students_by_class:
                logger.warning("学生数据分组后为空")
                return {
                    'status': 'error',
                    'message': '学生数据处理失败，无法生成PDF文件'
                }
                
        except Exception as db_error:
            logger.error(f"查询学生数据时出错: {db_error}")
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f'无法获取学生数据: {str(db_error)}'
            }
        finally:
            if conn:
                conn.close()
        
        # 创建导出文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"学生评语_{timestamp}.pdf"
        file_path = os.path.join(EXPORTS_FOLDER, filename)
        
        # 创建安全目录路径
        try:
            # 检查文件是否已存在
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"删除已存在的文件: {file_path}")
        except Exception as file_error:
            logger.error(f"处理文件路径时出错: {file_error}")
        
        try:
            # 创建PDF文档 - 使用A4横向页面，与打印预览保持一致
            doc = SimpleDocTemplate(
                file_path,
                pagesize=landscape(A4),  # 横向A4
                rightMargin=10*mm,
                leftMargin=10*mm,
                topMargin=10*mm,
                bottomMargin=10*mm
            )
            
            # 创建样式
            styles = getSampleStyleSheet()
            
            # 设置字体名称，如果注册了SimSun则使用，否则使用Helvetica
            font_name = 'SimSun' if font_registered else 'Helvetica'
            
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Title'],
                fontName=font_name,
                fontSize=16,
                alignment=1,  # 居中
                spaceAfter=6*mm
            )
            
            header_style = ParagraphStyle(
                'Header',
                parent=styles['Heading2'],
                fontName=font_name,
                fontSize=14,
                alignment=0,  # 左对齐
                spaceAfter=3*mm
            )
            
            normal_style = ParagraphStyle(
                'Normal',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=12,
                leading=14,   # 行间距
                alignment=0   # 左对齐
            )
            
            # 构建文档内容
            story = []
            
            # 计算每页的学生卡片数量
            cards_per_page = 6  # 与打印预览保持一致，每页6个学生
            current_page = 1
            
            # 遍历每个班级
            for class_name, class_students in students_by_class.items():
                try:
                    # 将学生按每页最多6个分组
                    for page_index, page_start in enumerate(range(0, len(class_students), cards_per_page)):
                        # 新页面逻辑
                        if current_page == 1:
                            # 添加标题（仅第一页）
                            story.append(Paragraph("学生评语表", title_style))
                        
                        # 添加班级标题
                        safe_class_name = str(class_name).replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(f"{safe_class_name}", header_style))
                        
                        page_students = class_students[page_start:page_start + cards_per_page]
                        
                        # 创建学生卡片表格 - 3列排列
                        data = []
                        row = []
                        
                        for i, student in enumerate(page_students):
                            try:
                                # 安全获取学生信息
                                student_name = student.get('name', '未知')
                                student_gender = student.get('gender', '')
                                student_id = student.get('id', '未知ID')
                                raw_comment = student.get('comments', '')
                                raw_update_date = student.get('updated_at', '')
                                
                                # 安全处理文本
                                safe_name = student_name.replace('<', '&lt;').replace('>', '&gt;')
                                safe_gender = student_gender.replace('<', '&lt;').replace('>', '&gt;')
                                safe_id = str(student_id).replace('<', '&lt;').replace('>', '&gt;')
                                
                                comment_text = raw_comment if raw_comment else '暂无评语'
                                comment_text = comment_text.replace('<', '&lt;').replace('>', '&gt;')
                                comment_text = comment_text.replace('\n', '<br/>')
                                
                                update_date = raw_update_date if raw_update_date else '未更新'
                                
                                # 构建单元格内容 - 与打印预览保持一致的样式
                                student_info = f"<b>{safe_name}</b> ({safe_gender}) - 学号: {safe_id}"
                                
                                cell_content = f"""
                                <para leftIndent="0" firstLineIndent="0">{student_info}</para>
                                <para leftIndent="0" firstLineIndent="0"><br/></para>
                                <para leftIndent="0" firstLineIndent="0">{comment_text}</para>
                                <para leftIndent="0" firstLineIndent="0"><br/></para>
                                <para leftIndent="0" firstLineIndent="0" align="right"><font size="8">更新时间: {update_date}</font></para>
                                """
                                
                                row.append(Paragraph(cell_content, normal_style))
                            except Exception as cell_error:
                                logger.error(f"处理学生评语时出错: {cell_error}")
                                error_content = "<para><b>数据处理错误</b></para><para>无法显示此学生评语</para>"
                                row.append(Paragraph(error_content, normal_style))
                            
                            # 每3个学生一行
                            if (i + 1) % 3 == 0 or i == len(page_students) - 1:
                                # 如果不足3个，添加空单元格
                                while len(row) < 3:
                                    row.append('')
                                data.append(row)
                                row = []
                        
                        # 创建表格
                        col_widths = [doc.width/3.0 - 5*mm] * 3  # 减去一些边距，避免内容过宽
                        table = Table(data, colWidths=col_widths)
                        
                        # 设置表格样式
                        table.setStyle(TableStyle([
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                            ('LEFTPADDING', (0, 0), (-1, -1), 5),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                            ('TOPPADDING', (0, 0), (-1, -1), 5),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                        ]))
                        
                        story.append(table)
                        
                        # 添加页码
                        page_number = Paragraph(f"第 {current_page} 页", 
                                               ParagraphStyle('PageNumber', 
                                                            fontName=font_name, 
                                                            fontSize=9, 
                                                            alignment=1))
                        story.append(page_number)
                        
                        # 添加分页符，除了最后一页
                        current_page += 1
                        if current_page > 1 and page_index < (len(class_students) - 1) // cards_per_page:
                            story.append(PageBreak())
                
                except Exception as class_error:
                    logger.error(f"处理班级数据时出错: {class_error}")
                    logger.error(traceback.format_exc())
                    continue
            
            # 构建PDF
            try:
                doc.build(story)
                logger.info(f"成功生成PDF文件: {file_path}")
            except Exception as build_error:
                logger.error(f"构建PDF文档时出错: {build_error}")
                logger.error(traceback.format_exc())
                if os.path.exists(file_path):
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size == 0:
                            os.remove(file_path)
                            logger.info(f"已删除空的PDF文件: {file_path}")
                    except Exception:
                        pass
                return {
                    'status': 'error',
                    'message': f'生成PDF文档时出错: {str(build_error)}'
                }
            
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                logger.error(f"生成的PDF文件不存在或为空: {file_path}")
                return {
                    'status': 'error',
                    'message': 'PDF生成失败，文件不存在或为空'
                }
            
            return {
                'status': 'ok',
                'message': '评语导出成功',
                'file_path': file_path,
                'download_url': f'/download/exports/{filename}'
            }
            
        except Exception as e:
            logger.error(f"生成评语PDF时出错: {e}")
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f'生成评语PDF时出错: {str(e)}'
            }
    
    except Exception as e:
        logger.error(f"生成评语PDF时出错: {e}")
        logger.error(traceback.format_exc())
        return {
            'status': 'error',
            'message': f'生成评语PDF时出错: {str(e)}'
        }

# 生成打印预览HTML
def generate_preview_html(class_name=None, current_user=None):
    """
    生成用于打印预览的HTML
    
    参数:
    - class_name: 班级名称（可选，如果提供则只预览该班级的学生评语）
    - current_user: 当前用户对象，用于权限检查
    
    返回:
    - 包含状态和HTML内容的字典
    """
    try:
        # 获取所有学生数据
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 根据用户权限和班级参数构建查询
        if current_user and not current_user.is_admin and current_user.class_id:
            # 如果是班主任，只获取其班级的学生
            cursor.execute('SELECT id, name, gender, class, comments, updated_at FROM students WHERE class_id = ? ORDER BY CAST(id AS INTEGER)', (current_user.class_id,))
        elif class_name:
            # 如果指定了班级，获取该班级的学生
            cursor.execute('SELECT id, name, gender, class, comments, updated_at FROM students WHERE class = ? ORDER BY CAST(id AS INTEGER)', (class_name,))
        else:
            # 否则获取所有学生
            cursor.execute('SELECT id, name, gender, class, comments, updated_at FROM students ORDER BY class, CAST(id AS INTEGER)')
            
        students = cursor.fetchall()
        conn.close()
        
        if not students:
            return {
                'status': 'error',
                'message': '未找到任何学生数据'
            }
        
        # 构建基本HTML结构
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>学生评语打印预览</title>
            <style>
                body {
                    font-family: "Microsoft YaHei", sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .print-page {
                    background: white;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    position: relative;
                    width: 297mm;
                    height: 210mm;
                    box-sizing: border-box;
                    page-break-after: always;
                    overflow: hidden;
                }
                .student-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                    grid-template-rows: 1fr 1fr;
                    grid-gap: 10px;
                    height: calc(100% - 40px); /* 减去页面标题的高度和额外边距 */
                }
                .student-card {
                    border: 1px solid #ddd;
                    padding: 8px;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    position: relative;
                    max-height: 100%;
                    background-color: white;
                }
                .student-info {
                    font-weight: bold;
                    margin-bottom: 6px;
                    background-color: #f9f9f9;
                    padding: 5px;
                    border-bottom: 1px solid #eee;
                    position: sticky;
                    top: 0;
                    z-index: 1;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .student-comment {
                    white-space: pre-wrap;
                    line-height: 1.4;
                    overflow-y: auto;
                    flex-grow: 1;
                    font-size: 0.85em;
                    max-height: calc(100% - 25px); /* 减去学生信息头部的高度 */
                    padding-right: 5px;
                }
                .page-title {
                    text-align: center;
                    font-size: 18px;
                    margin-bottom: 10px;
                    font-weight: bold;
                    height: 25px;
                }
                /* 自定义滚动条样式 */
                .student-comment::-webkit-scrollbar {
                    width: 4px;
                }
                .student-comment::-webkit-scrollbar-track {
                    background: #f1f1f1;
                }
                .student-comment::-webkit-scrollbar-thumb {
                    background: #ccc;
                }
                @media print {
                    body {
                        background: white;
                        padding: 0;
                        margin: 0;
                        width: 297mm;
                        height: 210mm;
                    }
                    .print-page {
                        box-shadow: none;
                        margin: 0;
                        padding: 8mm;
                        width: 100%;
                        height: 100%;
                        overflow: hidden;
                    }
                    .student-grid {
                        grid-gap: 8px;
                        height: calc(100% - 30px);
                    }
                    .student-card {
                        border: 1px solid #ddd;
                        page-break-inside: avoid;
                        overflow: hidden; /* 打印时隐藏溢出内容而不是显示滚动条 */
                        max-height: none; /* 允许打印时自动适应高度 */
                    }
                    .student-comment {
                        overflow: hidden; /* 打印时隐藏溢出内容 */
                        text-overflow: ellipsis; /* 使用省略号表示截断文本 */
                        max-height: none; /* 打印时不限制高度 */
                    }
                    @page {
                        size: landscape;
                        margin: 0;
                    }
                }
            </style>
        </head>
        <body>
        """
        
        # 将学生按照每页6个进行分组
        students_per_page = 6
        total_pages = (len(students) + students_per_page - 1) // students_per_page
        
        for page in range(total_pages):
            # 开始新的一页
            page_title = f"学生评语 - 第{page + 1}页"
            if class_name:
                page_title = f"{class_name}班 - 学生评语 - 第{page + 1}页"
                
            html_content += f"""
            <div class="print-page">
                <div class="page-title">{page_title}</div>
                <div class="student-grid">
            """
            
            # 该页的学生索引范围
            start_idx = page * students_per_page
            end_idx = min(start_idx + students_per_page, len(students))
            
            # 添加该页的学生评语
            for i in range(start_idx, end_idx):
                student = students[i]
                escaped_comments = html_escape(student['comments'] or '暂无评语')
                
                html_content += f"""
                <div class="student-card">
                    <div class="student-info">
                        {student['name']} ({student['gender']}) - 学号: {student['id']}
                    </div>
                    <div class="student-comment">
                        {escaped_comments}
                    </div>
                </div>
                """
            
            # 填充空白卡片以保持布局一致
            for i in range(end_idx - start_idx, students_per_page):
                html_content += """
                <div class="student-card" style="visibility: hidden;"></div>
                """
            
            # 结束当前页
            html_content += """
                </div>
            </div>
            """
        
        # 结束HTML
        html_content += """
        </body>
        </html>
        """
        
        return {
            'status': 'ok',
            'html': html_content
        }
        
    except Exception as e:
        logger.error(f"生成预览HTML时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'status': 'error',
            'message': f'生成预览HTML时出错: {str(e)}'
        }

# 用于HTML转义的辅助函数
def html_escape(text):
    """
    转义HTML特殊字符，防止XSS攻击和显示问题
    """
    if not text:
        return ''
        
    if not isinstance(text, str):
        text = str(text)
        
    # 转义HTML特殊字符
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#39;')
    
    # 保留换行，但确保不会有首行缩进
    text = text.replace('\n', '<br>')
    
    return text 