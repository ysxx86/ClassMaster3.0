#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF导出模块：专门负责生成学生评语的PDF文件
更加精简和稳健的实现 - 修复评语对齐问题、添加首行缩进、自适应评语高度
"""

import os
import logging
import sqlite3
import traceback
import time
from datetime import datetime
from flask_login import current_user

# 配置日志
logger = logging.getLogger(__name__)

# 导入PDF生成相关库
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
    REPORTLAB_AVAILABLE = True
    logger.info("PDF导出模块: ReportLab库已成功导入")
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.error("PDF导出模块: 无法导入ReportLab库，PDF生成功能将不可用")

# 数据库连接和导出目录配置
DATABASE = 'students.db'
EXPORTS_FOLDER = 'exports'

# 确保导出目录存在
if not os.path.exists(EXPORTS_FOLDER):
    try:
        os.makedirs(EXPORTS_FOLDER, exist_ok=True)
        logger.info(f"创建导出目录: {EXPORTS_FOLDER}")
    except Exception as e:
        logger.error(f"创建导出目录失败: {str(e)}")

# 字体目录
FONTS_FOLDER = 'utils/fonts'
os.makedirs(FONTS_FOLDER, exist_ok=True)

# 获取数据库连接
def get_db_connection():
    """获取SQLite数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# 注册中文字体
def register_fonts():
    """注册中文字体，确保PDF可以正确显示中文"""
    if not REPORTLAB_AVAILABLE:
        logger.error("ReportLab库不可用，无法注册字体")
        return False
    
    # 检查字体目录
    if not os.path.exists(FONTS_FOLDER):
        try:
            os.makedirs(FONTS_FOLDER, exist_ok=True)
            logger.info(f"创建字体目录: {FONTS_FOLDER}")
        except Exception as e:
            logger.error(f"创建字体目录失败: {str(e)}")
    
    # 尝试注册常见中文字体 - 优先使用macOS系统字体
    font_files = [
        # macOS系统字体
        ('/System/Library/Fonts/PingFang.ttc', 'PingFang'),
        ('/System/Library/Fonts/STHeiti Light.ttc', 'STHeiti'),
        ('/System/Library/Fonts/STHeiti Medium.ttc', 'STHeiti-Medium'),
        ('/System/Library/Fonts/Hiragino Sans GB.ttc', 'Hiragino'),
        ('/Library/Fonts/Microsoft/SimSun.ttf', 'SimSun'),
        ('/Library/Fonts/Arial Unicode.ttf', 'Arial-Unicode'),
        # 项目字体目录
        (f'{FONTS_FOLDER}/SimSun.ttf', 'SimSun'),
        (f'{FONTS_FOLDER}/SourceHanSerifCN-Regular.otf', 'SourceHan'),
        # Windows系统字体
        ('C:/Windows/Fonts/simsun.ttc', 'SimSun-Win'),
        ('C:/Windows/Fonts/simhei.ttf', 'SimHei-Win')
    ]
    
    # 尝试所有可能的字体，直到成功注册一个
    for font_path, font_name in font_files:
        try:
            if os.path.exists(font_path):
                logger.info(f"找到字体文件: {font_path}")
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                logger.info(f"成功注册中文字体: {font_path} 作为 {font_name}")
                return font_name
            else:
                logger.info(f"字体文件不存在: {font_path}")
        except Exception as e:
            logger.warning(f"注册字体 {font_path} 失败: {str(e)}")
            logger.warning(traceback.format_exc())
    
    # 如果无法找到中文字体，尝试使用默认字体
    logger.warning("无法注册中文字体，将使用默认字体")
    return 'Helvetica'

# 获取班主任姓名
def get_teacher_name(class_id):
    """根据班级ID获取班主任姓名"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询班级对应的班主任信息
        cursor.execute('SELECT u.username FROM users u WHERE u.class_id = ?', (class_id,))
        teacher = cursor.fetchone()
        conn.close()
        
        if teacher:
            return teacher['username']
        else:
            return "未设置"
    except Exception as e:
        logger.error(f"获取班主任信息失败: {str(e)}")
        return "未知"

# 核心导出函数
def export_comments_to_pdf(class_name=None, output_file=None, school_name=None, school_year=None):
    """
    将学生评语导出为PDF文件
    
    参数:
    - class_name: 班级名称（可选，仅导出指定班级）
    - output_file: 输出文件名（可选，如未指定则自动生成）
    - school_name: 学校名称（可选，显示在标题中）
    - school_year: 学年（可选，显示在标题中）
    
    返回:
    - 包含状态和文件路径的字典
    """
    start_time = time.time()
    logger.info(f"开始导出评语PDF，班级: {class_name}, 学校: {school_name}, 学年: {school_year}")
    
    # 检查PDF生成库是否可用
    if not REPORTLAB_AVAILABLE:
        logger.error("PDF生成库(ReportLab)未安装")
        return {
            'status': 'error', 
            'message': 'PDF生成库(ReportLab)未安装，无法生成PDF文件。请安装库: pip install reportlab'
        }
    
    # 确保导出目录存在且可写
    try:
        if not os.path.exists(EXPORTS_FOLDER):
            os.makedirs(EXPORTS_FOLDER, exist_ok=True)
            logger.info(f"创建导出目录: {EXPORTS_FOLDER}")
            
        # 尝试创建测试文件验证写入权限
        test_file = os.path.join(EXPORTS_FOLDER, "test_write.txt")
        try:
            with open(test_file, 'w') as f:
                f.write("测试写入权限")
            if os.path.exists(test_file):
                os.remove(test_file)
            logger.info("导出目录写入权限测试成功")
        except Exception as e:
            logger.error(f"导出目录写入权限测试失败: {str(e)}")
            return {'status': 'error', 'message': f'导出目录没有写入权限: {str(e)}'}
            
    except Exception as e:
        logger.error(f"创建导出目录时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return {'status': 'error', 'message': f'创建导出目录时出错: {str(e)}'}
    
    # 生成导出文件名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    if not output_file:
        filename = f"学生评语_{timestamp}.pdf"
    else:
        filename = output_file
    
    file_path = os.path.join(EXPORTS_FOLDER, filename)
    logger.info(f"导出文件路径: {file_path}")
    
    # 注册字体
    try:
        font_name = register_fonts()
        logger.info(f"使用字体: {font_name}")
    except Exception as e:
        logger.error(f"注册字体时出错: {str(e)}")
        return {'status': 'error', 'message': f'注册字体时出错: {str(e)}'}
    
    # 获取学生数据
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询语句，增加班级ID筛选
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated and hasattr(current_user, 'is_admin') and not current_user.is_admin and hasattr(current_user, 'class_id') and current_user.class_id:
            # 班主任只能导出本班级学生，优先使用班主任自己的 class_id 进行筛选，避免使用不可靠的 class_name 参数
            query = ('SELECT s.id as id, s.name as name, s.gender as gender, '
                     'c.class_name as class, s.class_id as class_id, s.comments as comments, s.updated_at as updated_at '
                     'FROM students s LEFT JOIN classes c ON s.class_id = c.id '
                     'WHERE s.class_id = ? ORDER BY CAST(s.id AS INTEGER)')
            logger.info(f"班主任模式: 执行查询: {query} 参数: {current_user.class_id}")
            cursor.execute(query, (current_user.class_id,))
        else:
            # 管理员可以导出所有班级，未登录用户或会话过期的用户视为游客
            if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
                logger.warning("未登录用户或会话过期，无法访问数据")
                return {'status': 'error', 'message': '您需要登录后才能导出报告'}
                
            if class_name:
                # class_name 可能是 class id（数字）或班级名称（字符串），分别处理
                try:
                    class_id_param = int(class_name)
                    query = ('SELECT s.id as id, s.name as name, s.gender as gender, '
                             'c.class_name as class, s.class_id as class_id, s.comments as comments, s.updated_at as updated_at '
                             'FROM students s LEFT JOIN classes c ON s.class_id = c.id '
                             'WHERE s.class_id = ? ORDER BY CAST(s.id AS INTEGER)')
                    logger.info(f"管理员模式(按ID筛选): 执行查询: {query} 参数: {class_id_param}")
                    cursor.execute(query, (class_id_param,))
                except ValueError:
                    # 按班级名称筛选
                    query = ('SELECT s.id as id, s.name as name, s.gender as gender, '
                             'c.class_name as class, s.class_id as class_id, s.comments as comments, s.updated_at as updated_at '
                             'FROM students s LEFT JOIN classes c ON s.class_id = c.id '
                             'WHERE c.class_name = ? ORDER BY CAST(s.id AS INTEGER)')
                    logger.info(f"管理员模式(按名称筛选): 执行查询: {query} 参数: {class_name}")
                    cursor.execute(query, (class_name,))
            else:
                query = ('SELECT s.id as id, s.name as name, s.gender as gender, '
                         'c.class_name as class, s.class_id as class_id, s.comments as comments, s.updated_at as updated_at '
                         'FROM students s LEFT JOIN classes c ON s.class_id = c.id ORDER BY c.class_name, CAST(s.id AS INTEGER)')
                logger.info(f"管理员模式: 执行查询: {query}")
                cursor.execute(query)
        
        # 获取数据
        students = cursor.fetchall()
        conn.close()
        
        # 检查是否有数据
        if not students or len(students) == 0:
            logger.warning("没有找到学生数据，无法生成PDF")
            return {'status': 'error', 'message': '没有找到学生数据，无法生成PDF文件'}
        
        # 如果学生数量过多，考虑分批处理
        total_students = len(students)
        if total_students > 100:
            logger.warning(f"学生数量较多 ({total_students})，PDF生成可能需要较长时间")
        
        logger.info(f"成功获取 {total_students} 名学生数据")
    except Exception as e:
        logger.error(f"查询学生数据时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return {'status': 'error', 'message': f'查询学生数据时出错: {str(e)}'}
    
    # 生成PDF文件
    try:
        # 分析学生数据
        students_by_class = {}
        class_teacher_map = {}  # 存储班级ID和班主任的映射
        
        for s in students:
            class_name = s['class'] if s['class'] else '未分班'
            class_id = s['class_id']
            
            if class_name not in students_by_class:
                students_by_class[class_name] = []
                # 获取班主任信息
                if class_id and class_id not in class_teacher_map:
                    class_teacher_map[class_id] = get_teacher_name(class_id)
            
            students_by_class[class_name].append(dict(s))
        
        # 创建横向A4文档 - 与打印预览保持一致
        doc = SimpleDocTemplate(
            file_path,
            pagesize=landscape(A4),
            rightMargin=10*mm,  # 增加右边距，确保内容不会超出红色框
            leftMargin=10*mm,   # 增加左边距，确保内容不会超出红色框
            topMargin=5*mm,    # 保持适当的上边距
            bottomMargin=5*mm  # 保持适当的下边距
        )
        
        # 创建样式
        styles = getSampleStyleSheet()
        
        # 定义标题样式
        title_style = ParagraphStyle(
            'Title', 
            parent=styles['Normal'], 
            fontName=font_name, 
            fontSize=14, 
            alignment=0,  # 左对齐
            spaceAfter=2*mm,
            fontWeight='bold'
        )
        
        # 定义班级标题样式
        class_style = ParagraphStyle(
            'Class', 
            parent=styles['Normal'], 
            fontName=font_name, 
            fontSize=12, 
            alignment=0,  # 左对齐
            spaceBefore=1*mm,
            spaceAfter=2*mm
        )
        
        # 定义页码样式
        page_number_style = ParagraphStyle(
            'PageNumber',
            parent=styles['Normal'], 
            fontName=font_name, 
            fontSize=9,
            alignment=1,  # 居中
            textColor=colors.gray
        )
        
        # 创建文档内容
        story = []
        
        # 处理每个班级
        for class_name, class_students in students_by_class.items():
            # 获取班级对应的班主任姓名
            class_id = class_students[0]['class_id'] if class_students else None
            teacher_name = class_teacher_map.get(class_id, "未设置") if class_id else "未设置"
            
            # 每页显示6个学生卡片（3列2行）
            cards_per_page = 6
            
            # 按每页6个学生分组
            for page_start in range(0, len(class_students), cards_per_page):
                page_students = class_students[page_start:page_start + cards_per_page]
                
                # 创建页面标题和班级信息
                title_elements = [
                    [Paragraph("学生评语表", title_style), 
                     Paragraph(f"班级：{class_name}      班主任：{teacher_name}", class_style)]
                ]
                title_table = Table(title_elements, colWidths=[90*mm, 170*mm])
                title_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                story.append(title_table)
                story.append(Spacer(1, 2*mm))  # 减小标题和内容之间的间距
                
                # 创建本页的学生卡片表格
                student_cards = []
                
                # 分两行处理，每行3个卡片
                for row_idx in range(2):  # 处理2行
                    row_start = page_start + row_idx * 3  # 每行3个学生
                    if row_start < len(class_students):
                        # 获取当前行的学生（最多3个）
                        end_idx = min(row_start + 3, len(class_students))
                        row_students = class_students[row_start:end_idx]
                        
                        # 预先计算所有评语，找出最大高度
                        row_comments = []
                        max_height = 0
                        
                        for student in row_students:
                            raw_comments = student.get('comments', '')
                            comments = str(raw_comments).replace('<', ' ').replace('>', ' ') if raw_comments else '暂无评语'
                            
                            # 创建评语段落以测量高度 - 使用小四号字体(12pt)
                            comment_style = ParagraphStyle(
                                'Comment',
                                parent=styles['Normal'],
                                fontName=font_name,
                                fontSize=12,  # 小四号字体大小
                                alignment=0,
                                firstLineIndent=24,  # 设置首行缩进2个字符
                                spaceBefore=1*mm,
                                spaceAfter=1*mm,
                                leading=16  # 行间距
                            )
                            
                            # 评语的有效宽度应考虑到表格内边距
                            effective_width = 85*mm  # 减小评语宽度，避免超出红色框
                            p = Paragraph(comments, comment_style)
                            w, h = p.wrap(effective_width, 500*mm)  # 给予充足高度以测量实际需要的高度
                            
                            # 确保我们有足够空间显示评语
                            if h > max_height:
                                max_height = h
                            
                            row_comments.append((comments, p, h))
                        
                        # 设置最小高度，确保短评语也有足够空间
                        if max_height < 28*mm:
                            max_height = 28*mm
                        
                        # 为长评语增加额外空间，确保内容不会被截断
                        max_height += 5*mm
                        
                        # 现在用计算好的高度创建卡片
                        row_cards = []
                        
                        for i, student in enumerate(row_students):
                            if i < len(row_comments):
                                # 处理学生数据
                                student_id = str(student.get('id', '未知ID'))
                                student_name = str(student.get('name', '未知姓名'))
                                student_gender = str(student.get('gender', '未知'))
                                comments = row_comments[i][0]
                                
                                # 创建学生卡片内容
                                student_info = f"{student_name} ({student_gender}) - 学号: {student_id}"
                                
                                # 学生信息样式
                                student_info_style = ParagraphStyle(
                                    'StudentInfo',
                                    parent=styles['Normal'],
                                    fontName=font_name,
                                    fontSize=12,
                                    alignment=0,
                                    fontWeight='bold',
                                    spaceAfter=1*mm  # 减小学生信息和评语之间的间距
                                )
                                
                                # 创建卡片内容元素，仅包含学生信息和评语
                                card_elements = [
                                    [Paragraph(student_info, student_info_style)],
                                    [Paragraph(comments, comment_style)]
                                ]
                                
                                # 创建学生卡片表格，使用计算好的高度
                                card_style = TableStyle([
                                    ('BOX', (0, 0), (-1, -1), 1, colors.black),
                                    ('VALIGN', (0, 0), (0, 0), 'TOP'),  # 信息顶部对齐
                                    ('VALIGN', (0, 1), (0, 1), 'TOP'),  # 评语顶部对齐
                                    ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),  # 进一步减小左内边距
                                    ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),  # 进一步减小右内边距
                                    ('TOPPADDING', (0, 0), (-1, -1), 2*mm),   # 减小顶部内边距
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm)  # 减小底部内边距
                                ])
                                
                                # 使用自适应高度，确保所有卡片高度一致
                                card_table = Table(card_elements, 
                                                colWidths=[90*mm],  # 减小卡片宽度
                                                rowHeights=[8*mm, max_height],  
                                                hAlign='CENTER')  # 水平居中对齐
                                card_table.setStyle(card_style)
                                row_cards.append(card_table)
                        
                        # 补齐行中不足的卡片（使用空白）
                        while len(row_cards) < 3:
                            # 创建一个空的卡片，保持与其他卡片相同大小
                            empty_card = Table([[""], [""]], 
                                            colWidths=[90*mm],  # 与其他卡片宽度保持一致
                                            rowHeights=[8*mm, max_height],  # 与其他卡片高度保持一致
                                            hAlign='CENTER')  # 水平居中对齐
                            empty_card.setStyle(TableStyle([
                                ('BOX', (0, 0), (-1, -1), 1, colors.white),  # 白色边框，实际上不可见
                            ]))
                            row_cards.append(empty_card)
                        
                        student_cards.append(row_cards)
                
                # 创建学生卡片网格
                grid_style = TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # 顶部对齐
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 居中对齐表格
                    # 调整内边距，使卡片之间有适当间距
                    ('LEFTPADDING', (0, 0), (-1, -1), 1.5*mm),  # 增加左右间距
                    ('RIGHTPADDING', (0, 0), (-1, -1), 1.5*mm),  # 增加左右间距
                    ('TOPPADDING', (0, 0), (-1, -1), 1*mm),  # 增加上下间距
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm)  # 保持行间距
                ])
                
                # 使用固定宽度确保所有卡片对齐
                student_grid = Table(student_cards, 
                                    colWidths=[90*mm, 90*mm, 90*mm],  # 减小卡片宽度
                                    repeatRows=0)  # 首行不重复
                student_grid.setStyle(grid_style)
                story.append(student_grid)
                
                # 每页结束后添加分页符（除非是最后一页）
                if page_start + cards_per_page < len(class_students):
                    story.append(PageBreak())
            
            # 每个班级结束后添加分页符（除非是最后一个班级）
            if class_name != list(students_by_class.keys())[-1]:
                story.append(PageBreak())
        
        # 添加页码
        def add_page_number(canvas, doc):
            canvas.saveState()
            # 绘制页码 - 上移位置
            page_num = canvas.getPageNumber()
            text = f"第 {page_num} 页"
            canvas.setFont(font_name, 9)
            canvas.setFillColor(colors.gray)
            # 页码上移到距离底边15mm位置
            canvas.drawCentredString(doc.width/2 + doc.leftMargin, 15*mm, text)
            canvas.restoreState()
            
        # 构建PDF文档
        doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
        
        # 检查文件是否成功生成
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            logger.info(f"PDF文件成功生成: {file_path}")
            
            # 定时检查生成进度
            current_time = time.time()
            if current_time - start_time > 30:  # 如果已经运行超过30秒
                logger.warning(f"PDF生成时间较长: {current_time - start_time:.2f}秒")
            
            # 生成URL
            server_url = "http://127.0.0.1:8080"  # 默认本地地址
            download_url = f"/download/exports/{filename}"
            
            # 返回结果
            elapsed_time = time.time() - start_time
            logger.info(f"PDF导出完成，用时: {elapsed_time:.2f}秒")
            return {
                'status': 'ok',
                'file_path': file_path,
                'download_url': download_url,
                'filename': filename
            }
        else:
            return {'status': 'error', 'message': 'PDF文件生成失败，文件不存在或为空'}
    except Exception as e:
        logger.error(f"生成PDF文件时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return {'status': 'error', 'message': f'生成PDF文件时出错: {str(e)}'} 