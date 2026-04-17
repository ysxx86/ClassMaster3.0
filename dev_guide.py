# -*- coding: utf-8 -*-

import subprocess
import traceback
import os
import platform
import tempfile
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


def _get_git_commits(page=1, per_page=20):
    try:
        total_result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            capture_output=True, text=True, timeout=10
        )
        total = int(total_result.stdout.strip()) if total_result.returncode == 0 else 0

        skip = (page - 1) * per_page
        result = subprocess.run(
            ['git', 'log', f'--skip={skip}', f'--max-count={per_page}', '--format=%ai|%an|%s'],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            return [], 0

        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line or '|' not in line:
                continue
            parts = line.split('|', 2)
            if len(parts) == 3:
                commits.append({
                    'time': parts[0].strip(),
                    'author': parts[1].strip(),
                    'message': parts[2].strip()
                })

        return commits, total
    except Exception as e:
        logger.error(f"git log error: {e}")
        return [], 0


@dev_guide_bp.route('/')
def dev_guide_page():
    return send_from_directory('pages', 'dev-guide.html')


@dev_guide_bp.route('/api/commits')
def api_commits():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20

        commits, total = _get_git_commits(page, per_page)

        return jsonify({
            'status': 'ok',
            'commits': commits,
            'total': total,
            'page': page,
            'per_page': per_page
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
            PageBreak, Frame, PageTemplate
        )
    except ImportError:
        return jsonify({'status': 'error', 'message': 'reportlab not installed'}), 500

    try:
        font_name = _register_chinese_font()

        commits, _ = _get_git_commits(page=1, per_page=1000)

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
            'CNTitle',
            parent=styles['Title'],
            fontName=font_name,
            fontSize=24,
            leading=30,
            alignment=1,
            spaceAfter=20,
        )

        heading1_style = ParagraphStyle(
            'CNHeading1',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=18,
            leading=24,
            spaceBefore=20,
            spaceAfter=10,
        )

        heading2_style = ParagraphStyle(
            'CNHeading2',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=14,
            leading=20,
            spaceBefore=14,
            spaceAfter=8,
        )

        body_style = ParagraphStyle(
            'CNBody',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            leading=18,
            spaceAfter=6,
        )

        toc_style = ParagraphStyle(
            'CNToc',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=12,
            leading=22,
            leftIndent=20,
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
        story.append(Paragraph('一、开发手册', toc_style))
        story.append(Paragraph('二、安装手册', toc_style))
        story.append(Paragraph('三、开发记录', toc_style))
        story.append(PageBreak())

        story.append(Paragraph('一、开发手册', heading1_style))
        story.append(Spacer(1, 6))

        dev_manual_content = [
            ('项目概述', 'ClassMaster 3.0 是一款基于 Flask 的智能班级管理系统，支持学生信息管理、成绩分析、评语生成、德育评价、家长端等功能。'),
            ('技术栈', '后端：Python 3 + Flask + SQLite；前端：HTML/CSS/JavaScript + Bootstrap；PDF生成：ReportLab；AI评语：DeepSeek API。'),
            ('项目结构', 'app.py 为主入口，各功能模块以 Blueprint 形式组织（students、comments、grades、deyu 等），工具类位于 utils/ 目录，页面模板位于 pages/ 目录。'),
            ('数据库', '使用 SQLite 数据库（students.db），通过 config_manager.py 统一管理连接，表结构在 init_db() 中初始化。'),
            ('蓝图注册', '各功能模块在 app.py 中通过 app.register_blueprint() 注册，蓝图定义在各模块文件的顶层。'),
            ('权限控制', '使用 Flask-Login 进行用户认证，admin_required 装饰器控制管理员权限，check_student_access 控制班主任数据访问范围。'),
        ]

        for title, content in dev_manual_content:
            story.append(Paragraph(title, heading2_style))
            story.append(Paragraph(content, body_style))
            story.append(Spacer(1, 4))

        story.append(PageBreak())

        story.append(Paragraph('二、安装手册', heading1_style))
        story.append(Spacer(1, 6))

        install_manual_content = [
            ('环境要求', 'Python 3.8+，pip，Git。推荐使用虚拟环境（venv）隔离依赖。'),
            ('获取代码', 'git clone https://gitee.com/ysxx86/class-master.git'),
            ('安装依赖', 'pip install -r requirements.txt。项目使用 dependency_manager.py 自动检查并安装缺失依赖。'),
            ('配置文件', '系统配置通过 config_manager.py 管理，支持 config.json 和数据库 system_settings 表双存储。'),
            ('启动服务', 'python app.py --host 0.0.0.0 --port 8080。生产环境建议使用 Gunicorn：gunicorn -c gunicorn_config.py app:app。'),
            ('默认账号', '管理员默认账号 admin，默认密码请在首次登录后及时修改。'),
        ]

        for title, content in install_manual_content:
            story.append(Paragraph(title, heading2_style))
            story.append(Paragraph(content, body_style))
            story.append(Spacer(1, 4))

        story.append(PageBreak())

        story.append(Paragraph('三、开发记录', heading1_style))
        story.append(Spacer(1, 6))

        if commits:
            table_data = [['时间', '作者', '提交信息']]
            for c in commits:
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
