# -*- coding: utf-8 -*-

import subprocess
import traceback
import os
import platform
import logging
from datetime import datetime
from io import BytesIO
from flask import Blueprint, request, jsonify, send_from_directory, send_file

logger = logging.getLogger(__name__)

dev_guide_bp = Blueprint('dev_guide', __name__, url_prefix='/dev-guide')

CHINESE_FONT_NAME = None


def _register_chinese_font():
    global CHINESE_FONT_NAME
    if CHINESE_FONT_NAME is not None:
        return CHINESE_FONT_NAME

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        CHINESE_FONT_NAME = 'Helvetica'
        return CHINESE_FONT_NAME

    system = platform.system()
    font_candidates = []

    if system == "Darwin":
        font_candidates = [
            ('/System/Library/Fonts/PingFang.ttc', 'PingFang'),
            ('/System/Library/Fonts/STHeiti Light.ttc', 'STHeiti'),
            ('/System/Library/Fonts/Hiragino Sans GB.ttc', 'Hiragino'),
            ('/Library/Fonts/Microsoft/SimSun.ttf', 'SimSun'),
        ]
    elif system == "Windows":
        font_candidates = [
            ('C:/Windows/Fonts/simsun.ttc', 'SimSun'),
            ('C:/Windows/Fonts/simhei.ttf', 'SimHei'),
            ('C:/Windows/Fonts/msyh.ttc', 'Microsoft-YaHei'),
        ]
    else:
        font_candidates = [
            ('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 'WQY-ZenHei'),
            ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'NotoSans'),
        ]

    for font_path, font_name in font_candidates:
        try:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                CHINESE_FONT_NAME = font_name
                logger.info(f"dev_guide PDF: registered font {font_name}")
                return font_name
        except Exception as e:
            logger.debug(f"dev_guide PDF: register font {font_path} failed: {e}")

    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        CHINESE_FONT_NAME = 'STSong-Light'
        logger.info("dev_guide PDF: using CID font STSong-Light")
        return 'STSong-Light'
    except Exception:
        pass

    CHINESE_FONT_NAME = 'Helvetica'
    logger.warning("dev_guide PDF: no Chinese font available, falling back to Helvetica")
    return 'Helvetica'


def _get_git_commits(skip=0, limit=20):
    try:
        total_result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            capture_output=True, text=True, timeout=10
        )
        total = int(total_result.stdout.strip()) if total_result.returncode == 0 else 0

        result = subprocess.run(
            ['git', 'log', f'--skip={skip}', f'--max-count={limit}', '--format=%ai|%an|%s'],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            return [], 0, False

        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line or '|' not in line:
                continue
            parts = line.split('|', 2)
            if len(parts) == 3:
                time_str = parts[0].strip()
                year = time_str[:4] if len(time_str) >= 4 else ''
                month = time_str[5:7] if len(time_str) >= 7 else ''
                commits.append({
                    'time': time_str,
                    'author': parts[1].strip(),
                    'message': parts[2].strip(),
                    'year': year,
                    'month': month
                })

        has_more = (skip + limit) < total
        return commits, total, has_more
    except Exception as e:
        logger.error(f"git log error: {e}")
        return [], 0, False


@dev_guide_bp.route('/')
def dev_guide_page():
    return send_from_directory('pages', 'dev-guide.html')


@dev_guide_bp.route('/api/commits')
def api_commits():
    try:
        skip = request.args.get('skip', 0, type=int)
        limit = request.args.get('limit', 20, type=int)

        if skip < 0:
            skip = 0
        if limit < 1 or limit > 100:
            limit = 20

        commits, total, has_more = _get_git_commits(skip, limit)

        return jsonify({
            'status': 'ok',
            'commits': commits,
            'total': total,
            'skip': skip,
            'limit': limit,
            'has_more': has_more
        })
    except Exception as e:
        logger.error(f"api/commits error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500


@dev_guide_bp.route('/api/export-pdf')
def api_export_pdf():
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak
        )
    except ImportError:
        return jsonify({'status': 'error', 'message': 'reportlab not installed'}), 500

    try:
        font_name = _register_chinese_font()

        commits, _, _ = _get_git_commits(skip=0, limit=1000)

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=25 * mm,
            rightMargin=25 * mm,
            topMargin=25 * mm,
            bottomMargin=25 * mm,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CNTitle', parent=styles['Title'], fontName=font_name,
            fontSize=24, leading=30, alignment=1, spaceAfter=20,
        )
        heading1_style = ParagraphStyle(
            'CNHeading1', parent=styles['Heading1'], fontName=font_name,
            fontSize=18, leading=24, spaceBefore=20, spaceAfter=10,
        )
        heading2_style = ParagraphStyle(
            'CNHeading2', parent=styles['Heading2'], fontName=font_name,
            fontSize=14, leading=20, spaceBefore=14, spaceAfter=8,
        )
        body_style = ParagraphStyle(
            'CNBody', parent=styles['Normal'], fontName=font_name,
            fontSize=11, leading=18, spaceAfter=6,
        )
        toc_style = ParagraphStyle(
            'CNToc', parent=styles['Normal'], fontName=font_name,
            fontSize=12, leading=22, leftIndent=20,
        )

        story = []

        story.append(Spacer(1, 80 * mm))
        story.append(Paragraph('ClassMaster 3.0', title_style))
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph('开发与安装手册', ParagraphStyle(
            'SubTitle', parent=title_style, fontSize=18, leading=24
        )))
        story.append(Spacer(1, 20 * mm))
        story.append(Paragraph(
            f'导出日期：{datetime.now().strftime("%Y-%m-%d %H:%M")}',
            ParagraphStyle('DateStyle', parent=body_style, alignment=1, fontSize=12)
        ))
        story.append(PageBreak())

        story.append(Paragraph('目录', heading1_style))
        story.append(Spacer(1, 6))
        toc_items = [
            '一、开发手册', '  1.1 项目概述', '  1.2 系统架构', '  1.3 技术栈详述',
            '  1.4 数据库设计', '  1.5 模块功能详述', '  1.6 API 接口设计',
            '  1.7 权限体系', '  1.8 编码规范', '  1.9 开发环境', '  1.10 开发流程',
            '二、安装手册', '三、开发记录',
        ]
        for item in toc_items:
            story.append(Paragraph(item, toc_style))
        story.append(PageBreak())

        story.append(Paragraph('一、开发手册', heading1_style))
        story.append(Spacer(1, 6))

        dev_manual_content = [
            ('1.1 项目概述', 'ClassMaster 3.0 是一款基于 Flask 的智能班级管理系统，专为小学班主任设计。系统覆盖学生信息管理、AI智能评语生成、成绩分析、德育六维度评价、家长端查看等核心功能。已在全校33个班级持续使用逾一年，覆盖约1400名学生。'),
            ('1.2 系统架构', '系统采用经典三层架构：前端展示层（HTML/CSS/JS + Chart.js + Boxicons）→ 后端业务层（Python Flask + Blueprint模块化架构 + Flask-Login认证）→ 数据存储层（SQLite + config.json + .env）。请求流程：浏览器 → Flask路由 → 对应Blueprint模块 → 工具层服务 → SQLite数据库。'),
            ('1.3 技术栈详述', '后端：Python 3.8+ / Flask 2.0+（轻量级Web框架）；Flask-Login（会话认证）；Flask-CORS（跨域支持）；SQLAlchemy 1.4+（ORM）。AI：DeepSeek V3/R1（评语生成与智能分析）。数据处理：Pandas 1.5+ / NumPy 1.24+（成绩统计）。文档：python-docx 0.8+（Word导出）；openpyxl 3.0+（Excel处理）；reportlab 4.0+（PDF生成）。前端：原生HTML/CSS/JS；Chart.js（数据可视化）；Boxicons（图标库）；Bootstrap（部分UI组件）。'),
            ('1.4 数据库设计', '使用SQLite数据库（students.db），共18张表。核心表：users（用户账号与角色）、students（学生信息与德育维度）、classes（班级信息）、comments（教师评语）、exams/exam_scores（考试与成绩）、subjects（学科配置）、teaching_assignments/teacher_subjects（教师班级学科分配）、parent_messages（家长寄语）、performance_items/evaluators/scores/results（绩效考核体系）、activities（操作日志）、todos（待办事项）、system_settings（系统设置）。外键关系：students.class_id→classes.id，comments.student_id→students.id，exam_scores.exam_id→exams.id，teaching_assignments.teacher_id→users.id等。'),
            ('1.5 模块功能详述', '评语管理(comments.py)：AI批量生成个性化评语，支持DeepSeek V3/R1模型，结构化提示词模板，一键导出Word。成绩分析(grade_analysis.py)：多科目Excel批量导入，自动计算优秀率/及格率/平均分，分数段分布，多次考试横向对比，根据年级自动调整优秀标准。德育评价(deyu.py)：品德/学习/健康/审美/实践/生活六维度实时评价，学期汇总。学生管理(students.py)：Excel批量导入，学籍信息CRUD。班级管理(classes.py)：班级创建与班主任绑定。用户管理(users.py)：管理员/班主任/科任教师多角色权限。仪表盘(dashboard.py)：数据总览与待办提醒。学科管理(subjects.py)：学科配置与教师分配。绩效考核(performance.py)：教师绩效评估体系。家长端(parent.py)：年级+班级+姓名验证，查看学生信息，提交寄语。系统设置(system_api.py)：DeepSeek API配置，学期设置。'),
            ('1.6 API 接口设计', '系统采用Flask Blueprint模块化路由：students_bp(/api/students)学生CRUD；comments_bp(/api/comments)评语管理与AI生成；grades_bp(/api/grades)成绩管理；deyu_bp(/api/deyu)德育评价；grade_analysis_bp(/api/grade-analysis)成绩分析；classes_bp(/api/classes)班级管理；users_bp(/api/users)用户管理；parent_bp(/api/parent)家长端接口；system_api_bp(/api/system)系统设置；dev_guide_bp(/dev-guide)开发指南。所有API需登录认证（除家长端和开发指南），管理员接口需admin_required装饰器。'),
            ('1.7 权限体系', '四级权限体系：管理员（全部权限，含用户管理、系统设置、全校数据访问）；班主任（本班数据访问，学生管理、评语生成、成绩录入、德育评价）；科任教师（指定班级的成绩录入与查看权限）；家长（通过年级+班级+姓名验证，只读查看学生信息，可提交寄语）。数据隔离通过check_student_access函数实现，班主任只能访问class_id匹配的学生数据。'),
            ('1.8 编码规范', 'Python后端：遵循PEP 8，类名PascalCase，函数/变量snake_case，常量UPPER_SNAKE_CASE，公共函数添加Docstring，行宽最大120字符。前端：HTML语义化标签2空格缩进，CSS类名kebab-case，JS变量camelCase，类PascalCase，使用const/let禁止var。'),
            ('1.9 开发环境', '操作系统Windows 10/11（推荐）、macOS、Linux。Python 3.8+。IDE推荐VS Code/Cursor。浏览器Chrome/Edge。Git 2.0+。DeepSeek API Key需在platform.deepseek.com申请。'),
            ('1.10 开发流程', '1.Fork仓库→2.克隆到本地→3.创建feature分支→4.按编码规范开发→5.python server.py本地测试→6.git commit提交→7.git push推送→8.提交Pull Request→9.代码审查→10.合并到主分支。'),
        ]

        for title, content in dev_manual_content:
            story.append(Paragraph(title, heading2_style))
            story.append(Paragraph(content, body_style))
            story.append(Spacer(1, 4))

        story.append(PageBreak())

        story.append(Paragraph('二、安装手册', heading1_style))
        story.append(Spacer(1, 6))

        install_manual_content = [
            ('环境要求', 'Python 3.8+，pip，Git。推荐使用虚拟环境（venv）隔离依赖。需申请DeepSeek API Key。'),
            ('获取代码', 'git clone https://gitee.com/ysxx86/class-master.git（国内推荐）或 git clone https://github.com/ysxx86/ClassMaster3.0.git'),
            ('安装依赖', 'pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple。项目内置dependency_manager.py自动检查缺失依赖。'),
            ('配置文件', '复制.env.example为.env，填入DEEPSEEK_API_KEY=sk-xxx。config.json首次运行自动生成。'),
            ('启动服务', 'python app.py --host 0.0.0.0 --port 8080。生产环境建议Gunicorn：gunicorn -c gunicorn_config.py app:app。'),
            ('默认账号', '管理员默认账号admin，默认密码admin123，首次登录后请立即修改。'),
        ]

        for title, content in install_manual_content:
            story.append(Paragraph(title, heading2_style))
            story.append(Paragraph(content, body_style))
            story.append(Spacer(1, 4))

        story.append(PageBreak())

        story.append(Paragraph('三、开发记录', heading1_style))
        story.append(Spacer(1, 6))

        if commits:
            grouped = {}
            for c in commits:
                ym = c.get('year', '') + '-' + c.get('month', '')
                if ym not in grouped:
                    grouped[ym] = []
                grouped[ym].append(c)

            for ym in sorted(grouped.keys(), reverse=True):
                story.append(Paragraph(ym, heading2_style))
                table_data = [['时间', '作者', '提交信息']]
                for c in grouped[ym]:
                    time_str = c['time'][:19] if len(c['time']) > 19 else c['time']
                    msg = c['message'][:60] + '...' if len(c['message']) > 60 else c['message']
                    table_data.append([time_str, c['author'], msg])

                col_widths = [45 * mm, 25 * mm, 95 * mm]
                table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D9D9D9')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(table)
                story.append(Spacer(1, 10))
        else:
            story.append(Paragraph('暂无开发记录', body_style))

        page_count = [0]

        def on_page(canvas, doc):
            page_count[0] += 1
            canvas.saveState()
            canvas.setFont(font_name, 9)
            canvas.drawCentredString(A4[0] / 2, 15 * mm, f'{page_count[0]}')
            canvas.restoreState()

        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

        buf.seek(0)
        filename = f'ClassMaster3.0_开发手册_{datetime.now().strftime("%Y%m%d")}.pdf'

        return send_file(
            buf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        logger.error(f"api/export-pdf error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500
