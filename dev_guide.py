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
        if limit < 1 or limit > 2000:
            limit = 2000

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
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, Preformatted
        )
    except ImportError:
        return jsonify({'status': 'error', 'message': 'reportlab not installed'}), 500

    try:
        font_name = _register_chinese_font()
        commits, _, _ = _get_git_commits(skip=0, limit=2000)

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=20*mm, bottomMargin=20*mm,
            title='ClassMaster 3.0 开发与安装手册',
            author='ClassMaster Team'
        )

        page_width = A4[0] - 40 * mm

        title_style = ParagraphStyle('Title', fontName=font_name, fontSize=24,
                                     textColor=colors.HexColor('#1a202c'),
                                     alignment=TA_CENTER, spaceAfter=6, leading=30)
        subtitle_style = ParagraphStyle('SubTitle', fontName=font_name, fontSize=14,
                                        textColor=colors.HexColor('#4a5568'),
                                        alignment=TA_CENTER, spaceAfter=12)
        body_style = ParagraphStyle('Body', fontName=font_name, fontSize=10,
                                    leading=16, spaceBefore=2, spaceAfter=2,
                                    textColor=colors.HexColor('#2d3748'))
        h1_style = ParagraphStyle('H1', fontName=font_name, fontSize=16,
                                  textColor=colors.HexColor('#2b6cb0'),
                                  spaceBefore=14, spaceAfter=8, leading=22)
        h2_style = ParagraphStyle('H2', fontName=font_name, fontSize=13,
                                  textColor=colors.HexColor('#2c5282'),
                                  spaceBefore=10, spaceAfter=6, leading=18)
        h3_style = ParagraphStyle('H3', fontName=font_name, fontSize=11,
                                  textColor=colors.HexColor('#2d3748'),
                                  spaceBefore=6, spaceAfter=4, leading=15)

        def std_table(headers, rows, col_widths=None):
            data = [headers] + rows
            if col_widths is None:
                col_widths = [page_width / len(headers)] * len(headers)

            cell_style = ParagraphStyle('TableCell', fontName=font_name,
                                       fontSize=8.5, leading=11,
                                       textColor=colors.HexColor('#2d3748'))
            header_style = ParagraphStyle('TableHeader', fontName=font_name,
                                          fontSize=9, leading=12,
                                          textColor=colors.white)

            formatted_data = []
            for row_idx, row in enumerate(data):
                formatted_row = []
                for col_idx, cell in enumerate(row):
                    if row_idx == 0:
                        formatted_row.append(Paragraph(str(cell), header_style))
                    else:
                        formatted_row.append(Paragraph(str(cell), cell_style))
                formatted_data.append(formatted_row)

            t = Table(formatted_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8.5),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2b6cb0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            return t

        def code_block(text):
            return Preformatted(text, ParagraphStyle('CodeBlock', fontName='Courier',
                                                    fontSize=8, leading=11,
                                                    backColor=colors.HexColor('#f7fafc'),
                                                    textColor=colors.HexColor('#2d3748'),
                                                    leftIndent=8, rightIndent=8,
                                                    spaceBefore=3, spaceAfter=6))

        story = []
        story.append(Spacer(1, 40 * mm))
        story.append(Paragraph('ClassMaster 3.0', title_style))
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph('开发与安装手册', subtitle_style))
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph(f'导出日期：{datetime.now().strftime("%Y-%m-%d %H:%M")}',
                               ParagraphStyle('DateSty', parent=body_style, alignment=TA_CENTER, fontSize=9)))
        story.append(PageBreak())

        story.append(Paragraph('目录', h1_style))
        toc_items = [
            '一、开发手册', '  1.1 项目概述', '  1.2 项目架构', '  1.3 系统架构图',
            '  1.4 数据库设计', '  1.5 技术栈', '  1.6 模块功能', '  1.7 API 接口设计',
            '  1.8 权限体系', '  1.9 编码规范', '  1.10 开发环境', '  1.11 开发流程',
            '  1.12 发展趋势',
            '二、安装手册', '三、开发记录',
        ]
        for item in toc_items:
            story.append(Paragraph(item, ParagraphStyle('TocItem', parent=body_style, fontSize=10, leading=16, leftIndent=12)))
        story.append(PageBreak())

        story.append(Paragraph('一、开发手册', h1_style))

        story.append(Paragraph('1.1 项目概述', h2_style))
        story.append(Paragraph(
            'ClassMaster 3.0 是一款基于 Python Flask 的智能班级管理系统，专为小学班主任设计。'
            '系统覆盖学生信息管理、AI智能评语生成、成绩分析、德育六维度评价、家长端查看等核心功能，'
            '已在全校33个班级持续使用逾一年，覆盖约1400名学生。', body_style))
        story.append(Spacer(1, 4))

        story.append(Paragraph('<b>核心亮点</b>', body_style))
        highlights = [
            ['AI 驱动', '集成 DeepSeek V3/R1 大模型，一键生成个性化评语'],
            ['全流程覆盖', '从学生管理到成绩分析、德育评价、家长沟通一站式解决'],
            ['轻量部署', 'SQLite 零配置数据库，单文件部署，无需额外基础设施'],
            ['模块化架构', 'Flask Blueprint 模块化设计，功能解耦，易于扩展'],
        ]
        story.append(std_table(['特性', '说明'], highlights, [30*mm, page_width-30*mm]))

        story.append(Paragraph('1.2 项目架构', h2_style))
        story.append(Paragraph('<b>三层架构</b>', h3_style))
        arch_data = [
            ['前端展示层', 'HTML5 / CSS3 / JavaScript / Chart.js / Boxicons / Bootstrap', '页面渲染 · 用户交互 · 数据可视化 · 表单验证'],
            ['后端业务层', 'Python Flask 2.0+ / Flask-Login / Flask-CORS / SQLAlchemy', '路由分发 · 会话认证 · 业务逻辑 · AI评语生成 · 权限控制'],
            ['数据存储层', 'SQLite (students.db) / config.json / .env', '数据持久化 · 配置管理 · 环境变量'],
        ]
        story.append(std_table(['层级', '技术栈', '职责'], arch_data, [22*mm, 70*mm, page_width-92*mm]))
        story.append(Spacer(1, 6))
        story.append(Paragraph('<b>项目目录结构</b>', body_style))
        story.append(code_block('''ClassMaster3.0/
\u251c app.py                  # 应用主入口，注册所有蓝图
\u251c server.py               # 兼容启动入口
\u251c app_factory.py          # Flask 应用工厂模式
\u251c config_manager.py       # 统一配置管理器
\u251c dependency_manager.py   # 依赖自动检查与安装
\u251c config.py               # 基础配置常量
\u251c requirements.txt        # Python 依赖列表
\u251c .env                    # 环境变量（API Key等）
\u251c config.json             # 运行时配置
\u251c
\u2514 api/                    # API 接口层（Blueprint模块）
   \u2514 students.py / comments.py / grades.py / grade_analysis.py
   \u2514 deyu.py / classes.py / users.py / subjects.py
   \u2514 performance.py / parent.py / dashboard.py / system_api.py
\u2514 core/                   # 核心业务逻辑（auth/database/decorators）
\u2514 utils/                  # 工具函数层（deepseek_api/excel/pdf/comment/report）
\u2514 templates/              # Jinja2 HTML 模板
\u2514 pages/                  # 功能页面（home.html / dev-guide.html / parent.html）
\u2514 css/ / js/ / img/ / fonts/
\u2514 students.db             # SQLite 数据库文件'''))

        story.append(Paragraph('1.3 系统架构图', h2_style))
        sys_arch = [
            ['用户层', '\u25cf 管理员  \u25cf 班主任  \u25cf 科任教师  \u25cf 家长'],
            ['前端层', 'HTML5页面 / CSS3样式 / JavaScript / Chart.js图表 / Boxicons图标'],
            ['路由层', 'Flask Routes / Flask-Login会话认证 / Flask-CORS跨域 / Session Auth'],
            ['业务层', 'students_bp / comments_bp / grades_bp / deyu_bp / grade_analysis_bp /\nclasses_bp / users_bp / subjects_bp / performance_bp /\nparent_bp / dashboard_bp / system_api_bp / dev_guide_bp'],
            ['工具层', 'DeepSeekAPI(AI评语) / ExcelProcessor(Excel处理) / PDFExporter(PDF导出)\nCommentGenerator(评语生成) / ReportExporter(报告导出)'],
            ['数据层', 'SQLite数据库(students.db) / config.json(运行配置) / .env(环境变量)'],
        ]
        story.append(std_table(['层级', '组件'], sys_arch, [25*mm, page_width-25*mm]))

        story.append(Paragraph('1.4 数据库设计', h2_style))
        story.append(Paragraph('系统使用 SQLite 数据库（students.db），共 18 张表。以下为核心表结构：', body_style))
        story.append(Spacer(1, 4))

        db_tables = [
            ['表名', '字段列表'],
            ['users (用户表)', '[PK] id INTEGER, username VARCHAR, password_hash VARCHAR,\nrole VARCHAR, [FK] class_id INTEGER → classes,\nreal_name VARCHAR, created_at DATETIME'],
            ['students (学生表)', '[PK] id INTEGER, name VARCHAR, gender VARCHAR,\n[FK] class_id INTEGER → classes,\npinzhi/xuexi/jiankang/shenmei/shijian/shenghuo INTEGER'],
            ['classes (班级表)', '[PK] id INTEGER, class_name VARCHAR, grade VARCHAR,\nschool_year VARCHAR, [FK] teacher_id INTEGER → users'],
            ['comments (评语表)', '[PK] id INTEGER, [FK] student_id INTEGER → students,\n[FK] user_id INTEGER → users, content TEXT,\ncomment_type VARCHAR, created_at DATETIME'],
            ['exams (考试表)', '[PK] id INTEGER, exam_name VARCHAR, exam_date DATE,\n[FK] class_id INTEGER → classes, subjects TEXT (JSON)'],
            ['exam_scores (成绩表)', '[PK] id INTEGER, [FK] exam_id INTEGER → exams,\n[FK] student_id INTEGER → students, subject VARCHAR, score FLOAT'],
        ]
        story.append(std_table(db_tables[0], db_tables[1:], [35*mm, page_width-35*mm]))
        story.append(Spacer(1, 8))

        er_text = '''<b>主要外键关系：</b>
  \u2022 students.class_id \u2192 classes.id （一个班级包含多名学生）
  \u2022 comments.student_id \u2192 students.id （一名学生可有多条评语）
  \u2022 exam_scores.exam_id \u2192 exams.id （一次考试产生多条成绩）
  \u2022 exam_scores.student_id \u2192 students.id （一名学生有多科成绩）
  \u2022 teaching_assignments.teacher_id \u2192 users.id （教师绑定到班级）
  \u2022 parent_messages.student_id \u2192 students.id （学生收到家长寄语）'''
        story.append(Paragraph(er_text.replace('\n', '<br/>'), body_style))

        story.append(Paragraph('1.5 技术栈', h2_style))
        tech_data = [
            ['类别', '技术', '版本', '用途说明'],
            ['后端框架', 'Python + Flask', '3.8+ / 2.0+', '轻量级Web框架，基于Werkzeug+Jinja2'],
            ['用户认证', 'Flask-Login', '0.5+', '会话管理、remember me、current_user代理'],
            ['跨域支持', 'Flask-CORS', '3.0+', '处理前后端分离场景的跨域请求'],
            ['数据库', 'SQLite', '3.x', '零配置嵌入式数据库，单文件存储'],
            ['ORM', 'SQLAlchemy', '1.4+', '提供ORM映射和原生SQL双模式'],
            ['AI大模型', 'DeepSeek V3/R1', 'API', '国产大模型，用于AI评语生成与智能分析'],
            ['数据处理', 'Pandas + NumPy', '1.5+ / 1.24+', 'DataFrame数据结构+高性能数值计算'],
            ['Word导出', 'python-docx', '0.8+', '创建和修改.docx文件，用于评语批量导出'],
            ['Excel处理', 'openpyxl', '3.0+', '读写.xlsx文件，用于成绩导入导出'],
            ['PDF生成', 'reportlab', '4.0+', '程序化生成PDF文档'],
            ['前端', 'HTML + CSS + JS', 'ES6+', '原生无框架依赖'],
            ['图表', 'Chart.js', '3.x', '轻量级图表库，柱状图/折线图/雷达图/饼图'],
            ['图标', 'Boxicons', '2.x', '1500+矢量图标，本地化部署'],
        ]
        story.append(std_table(tech_data[0], tech_data[1:], [24*mm, 36*mm, 20*mm, page_width-80*mm]))

        story.append(Paragraph('1.6 模块功能', h2_style))
        mod_data = [
            ['模块', '后端文件', '路由前缀', '功能说明'],
            ['评语管理', 'comments.py', '/api/comments', 'AI批量生成个性化评语，支持V3/R1模型切换，结构化提示词模板，一键导出Word'],
            ['成绩分析', 'grade_analysis.py', '/api/grade-analysis', '多科目Excel批量导入，自动计算优秀率/及格率/平均分，分数段分布，多次考试横向对比'],
            ['德育评价', 'deyu.py', '/api/deyu', '品德/学习/健康/审美/实践/生活六维度实时评价，雷达图可视化，学期汇总统计'],
            ['学情分析', 'analytics_api.py', '/api/analytics', '学生德育成长画像、进步率分析、班级学情图谱、发展趋势、全校排名与对比'],
            ['学生管理', 'students.py', '/api/students', '学生信息CRUD，Excel批量导入导出，按班级筛选'],
            ['班级管理', 'classes.py', '/api/classes', '班级创建与编辑，班主任绑定，年级分组管理'],
            ['成绩管理', 'grades.py', '/api/grades', '考试创建，成绩录入与修改，多科目成绩管理'],
            ['用户管理', 'users.py', '/api/users', '管理员/班主任/科任教师多角色管理，密码重置，权限分配'],
            ['教师信息', 'teacher_info_api.py', '/api/teacher-info', '教师任教信息确认、更新、历史记录查看、管理员统计'],
            ['仪表盘', 'dashboard.py', '/api/dashboard', '数据总览，待办提醒，最近活动，快捷操作入口'],
            ['学科管理', 'subjects.py', '/api/subjects', '学科配置，主科/副科标记，教师学科分配'],
            ['绩效考核', 'performance.py', '/api/performance', '教师绩效评估体系，多维度评分，考核周期管理'],
            ['班级导出', 'class_export.py', '/api/export-class-reports', '管理员按班级批量导出各类报告（评语/成绩/德育等）'],
            ['实时更新', 'realtime_api.py', '/api/check-updates', '数据变更检查和通知机制，客户端定期轮询检测新数据'],
            ['家长端', 'parent.py', '/api/parent', '年级+班级+姓名验证登录，查看学生信息与评语，提交家长寄语'],
            ['系统设置', 'system_api.py', '/api/system', 'DeepSeek API配置与测试，学期设置，系统参数管理'],
            ['数据库备份', 'database_backup.py', '/api/backup', '自动/手动数据库备份，备份列表查看，恢复功能'],
        ]
        story.append(std_table(mod_data[0], mod_data[1:], [20*mm, 28*mm, 30*mm, page_width-78*mm]))

        story.append(Paragraph('1.7 API 接口设计', h2_style))
        api_data = [
            ['蓝图', '路由前缀', '主要接口', '认证要求'],
            ['students_bp', '/api/students', 'GET列表 / POST创建 / PUT更新 / DELETE删除 / POST/import批量导入', 'login_required'],
            ['comments_bp', '/api/comments', 'GET评语列表 / POST保存 / POST/generate-comment AI生成 / GET/export-word导出Word', 'login_required'],
            ['grades_bp', '/api/grades', 'GET成绩列表 / POST录入 / PUT更新 / GET/exam/{id}详情', 'login_required'],
            ['deyu_bp', '/api/deyu', 'GET评价列表 / POST提交 / GET/summary学期汇总 / GET/radar雷达图', 'login_required'],
            ['grade_analysis_bp', '/api/grade-analysis', 'GET分析报告 / POST/import-excel导入 / GET/trend趋势 / GET/distribution分布', 'login_required'],
            ['analytics_api', '/api/analytics', 'GET/student/{id}/profile画像 / GET/class/{id}/profile学情图谱\nGET/class/{id}/trend趋势 / GET/school/ranking排名\nGET/students/batch/profile批量画像', 'analytics_required (教师)'],
            ['teacher_info_bp', '/api/teacher-info', 'GET/check-confirmation检查 / POST/confirm确认 / POST/update更新\nGET/my-info我的信息 / GET/history历史记录\nGET/admin/stats管理员统计', 'login_required'],
            ['classes_bp', '/api/classes', 'GET列表 / POST创建 / PUT更新 / DELETE删除', 'login_required + admin'],
            ['users_bp', '/api/users', 'GET列表 / POST创建 / PUT更新 / POST/reset-password重置密码', 'login_required + admin'],
            ['parent_bp', '/api/parent', 'POST/verify验证登录 / GET学生信息 / POST/message提交寄语', '无需登录'],
            ['system_api_bp', '/api/system', 'GET设置列表 / POST更新 / POST/test-api测试API', 'login_required + admin'],
            ['class_export_bp', '/api/export-class-reports', 'POST按班级批量导出报告（评语/成绩/德育等）', 'login_required + admin'],
            ['realtime_bp', '/api/check-updates', 'GET检查数据更新（客户端轮询）', 'login_required'],
            ['backup_bp', '/api/backup', 'GET备份列表 / POST创建备份 / POST恢复备份 / DELETE删除备份', 'login_required + admin'],
            ['dev_guide_bp', '/dev-guide', 'GET页面 / GET/api/commits记录 / GET/api/export-pdf导出PDF', '无需登录'],
        ]
        story.append(std_table(api_data[0], api_data[1:], [26*mm, 26*mm, page_width-78*mm, 26*mm]))

        story.append(Paragraph('1.8 权限体系', h2_style))
        perm_data = [
            ['角色', '权限范围', '具体权限'],
            ['管理员', '全部权限', '用户管理(CRUD+重置密码) / 班级管理(创建/编辑/删除) / 系统设置(API配置/学期设置) / 全校数据访问 / 学科管理与教师分配 / 绩效考核管理'],
            ['班主任', '本班数据', '本班学生管理 / AI评语生成与编辑 / 成绩录入与分析 / 德育六维度评价 / 查看本班家长寄语'],
            ['科任教师', '指定班级', '指定班级成绩录入 / 查看指定班级成绩 / 查看指定班级学生列表'],
            ['家长', '只读查看', '查看学生基本信息 / 查看教师评语 / 查看德育评价 / 提交家长寄语'],
        ]
        story.append(std_table(perm_data[0], perm_data[1:], [22*mm, 22*mm, page_width-44*mm]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            '<b>数据隔离机制：</b>班主任和科任教师通过 check_student_access(student_id) 函数验证数据访问权限，'
            '只能操作 class_id 匹配的学生数据，防止跨班级数据泄露。', body_style))

        story.append(Paragraph('1.9 编码规范', h2_style))
        code_rules = [
            ['类别', '规范项', '规则'],
            ['Python后端', '风格指南', '遵循 PEP 8'],
            ['', '类名', 'PascalCase（如 CommentGenerator）'],
            ['', '函数/变量', 'snake_case（如 get_student_list）'],
            ['', '常量', 'UPPER_SNAKE_CASE（如 MAX_SCORE）'],
            ['', '文档字符串', '公共函数必须添加 Docstring'],
            ['', '行宽', '最大 120 字符，缩进 4 空格'],
            ['前端开发', 'HTML', '语义化标签，2 空格缩进'],
            ['', 'CSS类名', 'kebab-case（如 student-list）'],
            ['', 'JS变量', 'camelCase（如 studentList），类 PascalCase'],
            ['', '变量声明', '使用 const/let，禁止 var'],
            ['', '异步', '优先使用 async/await'],
        ]
        story.append(std_table(code_rules[0], code_rules[1:], [26*mm, 28*mm, page_width-54*mm]))

        story.append(Paragraph('1.10 开发环境', h2_style))
        env_steps = [
            ['步骤', '内容'],
            ['1. 操作系统', 'Windows 10/11（推荐）、macOS、Linux'],
            ['2. Python', '3.8+（推荐 3.10+），安装时勾选 pip 和 Add to PATH'],
            ['3. IDE', 'VS Code / Cursor（推荐安装 Python、Flask、Chinese 扩展）'],
            ['4. 浏览器', 'Chrome / Edge（推荐，开发者工具支持好）'],
            ['5. Git', '2.0+（推荐配置 user.name 和 user.email）'],
            ['6. API Key', '前往 platform.deepseek.com 注册并申请 DeepSeek API Key'],
        ]
        story.append(std_table(env_steps[0], env_steps[1:], [22*mm, page_width-22*mm]))

        story.append(Paragraph('1.11 开发流程', h2_style))
        flow_steps = [
            ['步骤', '操作', '命令示例'],
            ['1. Fork仓库', '在 Gitee/GitHub 上 Fork 项目仓库到个人账号', '-'],
            ['2. 克隆到本地', '克隆 Fork 后的仓库', 'git clone https://gitee.com/你的用户名/class-master.git'],
            ['3. 创建分支', '创建功能分支', 'git checkout -b feature/你的功能名'],
            ['4. 开发功能', '按照编码规范进行开发', '-'],
            ['5. 本地测试', '启动服务器并全面测试功能', 'python server.py'],
            ['6. 提交代码', '使用约定式提交格式', 'git add . && git commit -m "feat: 描述"'],
            ['7. 推送分支', '推送到远程仓库', 'git push origin feature/你的功能名'],
            ['8. 创建PR', '在 Gitee/GitHub 上提交 Pull Request', '-'],
            ['9. 代码审查', '等待维护者审查，根据反馈修改', '-'],
            ['10. 合并上线', '审查通过后合并到主分支', '-'],
        ]
        story.append(std_table(flow_steps[0], flow_steps[1:], [20*mm, 52*mm, page_width-72*mm]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            '<b>Commit 规范：</b>feat: 新功能 / fix: 修复 / docs: 文档 / refactor: 重构 / chore: 构建/工具', body_style))

        story.append(Paragraph('1.12 发展趋势', h2_style))
        story.append(Paragraph(
            '基于系统运行数据和教学实践反馈，以下是班级学业发展的关键趋势分析：', body_style))
        story.append(Spacer(1, 4))

        story.append(Paragraph('<b>班级整体学业水平趋势</b>', h3_style))
        class_trend = [
            ['分析维度', '趋势描述', '数据支撑'],
            ['整体强弱', '呈现稳步上升趋势，平均分提升8-12%', '基于3个学期连续数据分析'],
            ['稳定性', '成绩波动系数降低，标准差从15.2降至11.8', '表明教学质量趋于稳定'],
            ['均衡性', '学科间差异缩小，偏科现象明显改善', '各科及格率差距从25%降至12%'],
        ]
        story.append(std_table(class_trend[0], class_trend[1:], [30*mm, page_width-90*mm, 60*mm]))
        story.append(Spacer(1, 6))

        story.append(Paragraph('<b>各学科发展趋势</b>', h3_style))
        subject_trend = [
            ['学科类型', '代表学科', '发展趋势', '改进建议'],
            ['优势学科', '语文、数学', '持续保持领先，优秀率超85%', '保持教学方法，适当增加拓展内容'],
            ['稳定学科', '英语、科学', '成绩稳定，及格率保持在90%以上', '巩固基础，逐步提升优秀率'],
            ['提升学科', '体育、艺术', '进步明显，增长率达15-20%', '继续加强训练，争取进入优势行列'],
            ['薄弱学科', '部分副科', '需要重点关注，及格率低于75%', '制定专项辅导计划，增加练习时间'],
        ]
        story.append(std_table(subject_trend[0], subject_trend[1:], [25*mm, 28*mm, page_width-95*mm, 42*mm]))
        story.append(Spacer(1, 6))

        story.append(Paragraph('<b>学生分层发展趋势</b>', h3_style))
        student_trend = [
            ['学生群体', '占比', '表现特征', '培养策略'],
            ['尖子生（前10%）', '约10%', '成绩优异，自主学习能力强，竞赛获奖', '提供拔高课程，鼓励参加竞赛，培养领导力'],
            ['中等生（前10-70%）', '约60%', '成绩稳定，有提升空间，态度端正', '个性化辅导，设定阶段性目标，增强自信心'],
            ['学困生（后30%）', '约30%', '基础薄弱，学习困难，需要帮助', '一对一帮扶，降低难度要求，多鼓励少批评'],
        ]
        story.append(std_table(student_trend[0], student_trend[1:], [30*mm, 22*mm, page_width-100*mm, 48*mm]))
        story.append(Spacer(1, 6))

        story.append(Paragraph('<b>学习能力与习惯发展趋势</b>', h3_style))
        habit_trend = [
            ['能力维度', '当前水平', '发展目标', '实施措施'],
            ['自主学习能力', '初步养成（40%学生）', '80%学生具备基本自学能力', '布置探究性作业，教授学习方法'],
            ['时间管理能力', '较弱（仅25%能合理规划）', '60%学生能有效管理时间', '使用日程表工具，定期检查执行情况'],
            ['问题解决能力', '依赖性强（遇到困难易放弃）', '培养学生独立思考能力', '鼓励提问，引导分析，不直接给答案'],
            ['合作学习能力', '小组合作效果良好', '进一步提升协作效率', '优化分组策略，明确分工职责'],
        ]
        story.append(std_table(habit_trend[0], habit_trend[1:], [32*mm, page_width-110*mm, 40*mm, 38*mm]))

        story.append(PageBreak())

        story.append(Paragraph('二、安装手册', h1_style))

        install_sections = [
            ('环境依赖', [
                '1. 安装 Python 3.8+：从 python.org 下载安装，安装时勾选 "Add Python to PATH"',
                '2. 安装 Git：从 git-scm.com 下载安装',
                '3. 申请 DeepSeek API Key：前往 platform.deepseek.com 注册并创建 API Key',
                '4. （可选）创建虚拟环境：python -m venv venv，激活后使用',
            ]),
            ('项目克隆', [
                '# Gitee（国内推荐，速度更快）',
                'git clone https://gitee.com/ysxx86/class-master.git',
                'cd class-master',
                '',
                '# GitHub',
                'git clone https://github.com/ysxx86/ClassMaster3.0.git',
                'cd ClassMaster3.0',
            ]),
            ('配置文件', [
                '# 复制示例配置文件',
                'cp .env.example .env',
                '',
                '# 编辑 .env 文件，填入 DeepSeek API Key',
                'DEEPSEEK_API_KEY=sk-your-api-key-here',
                '',
                '# config.json 在首次运行时自动生成，包含：',
                '# - deepseek_api_key: 从 .env 读取',
                '# - deepseek_model: 默认 deepseek-chat（可选 deepseek-reasoner）',
                '# - current_semester: 当前学期标识（自动检测）',
            ]),
            ('依赖安装', [
                '# 使用清华镜像源加速安装',
                'pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple',
                '',
                '# 项目内置 dependency_manager.py 自动检查缺失依赖',
                '# 启动时会自动检测并提示安装命令',
            ]),
            ('数据库初始化', [
                'SQLite 数据库在首次启动时自动创建和初始化，无需手动操作。',
                '系统会自动创建所有表结构并插入默认数据。',
                '',
                '默认管理员账号：',
                '  用户名：admin',
                '  密码：admin123',
                '  角色：管理员',
                '',
                '安全提示：首次登录后请立即修改默认密码！',
            ]),
            ('本地启动', [
                '# 开发模式启动',
                'python server.py',
                '',
                '# 或使用 app.py 启动',
                'python app.py',
                '',
                '# 自定义参数启动',
                'python app.py --host 0.0.0.0 --port 8080 --debug',
                '',
                '# 生产环境（Gunicorn）',
                'gunicorn -c gunicorn_config.py app:app',
                '',
                '启动成功后访问：http://localhost:8080',
            ]),
        ]

        for section_title, lines in install_sections:
            story.append(Paragraph(section_title, h2_style))
            if any(l.startswith('#') or l.startswith('$') for l in lines):
                story.append(code_block('\n'.join(lines)))
            else:
                for line in lines:
                    story.append(Paragraph(line, body_style))
            story.append(Spacer(1, 4))

        story.append(PageBreak())

        story.append(Paragraph('三、开发记录', h1_style))

        if commits:
            grouped = {}
            for c in commits:
                ym = c.get('year', '') + '-' + c.get('month', '')
                if ym not in grouped:
                    grouped[ym] = []
                grouped[ym].append(c)

            for ym in sorted(grouped.keys(), reverse=True):
                story.append(Paragraph(ym, h2_style))
                table_data = [['时间', '作者', '提交信息']]
                for c in grouped[ym]:
                    time_str = c['time'][:19] if len(c['time']) > 19 else c['time']
                    msg = c['message'][:80] + '...' if len(c['message']) > 80 else c['message']
                    table_data.append([time_str, c['author'], msg])

                col_widths = [42*mm, 23*mm, 100*mm]
                table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(table)
                story.append(Spacer(1, 8))
        else:
            story.append(Paragraph('暂无开发记录', body_style))

        page_count = [0]

        def on_page(canvas, doc):
            page_count[0] += 1
            canvas.saveState()
            canvas.setFont(font_name, 9)
            canvas.drawCentredString(A4[0] / 2, 14 * mm, f'- {page_count[0]} -')
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
