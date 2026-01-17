# -*- coding: utf-8 -*-
"""
实时更新API
提供数据变更检查和通知功能
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 创建蓝图
realtime_bp = Blueprint('realtime', __name__, url_prefix='/api')

# 数据库连接
DATABASE = 'students.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@realtime_bp.route('/check-updates', methods=['GET'])
@login_required
def check_updates():
    """
    检查数据更新
    客户端定期调用此API检查是否有新的数据变更
    """
    try:
        # 获取上次检查的时间戳
        since = request.args.get('since', type=int, default=0)
        since_datetime = datetime.fromtimestamp(since / 1000) if since > 0 else datetime.min
        
        updates = []
        
        # 检查学生表更新
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学生数据更新
        cursor.execute('''
            SELECT COUNT(*) as count FROM students 
            WHERE updated_at > ?
        ''', (since_datetime.strftime('%Y-%m-%d %H:%M:%S'),))
        
        student_updates = cursor.fetchone()['count']
        if student_updates > 0:
            updates.append({
                'type': 'student_updated',
                'count': student_updates,
                'timestamp': datetime.now().timestamp() * 1000
            })
        
        # 检查成绩更新
        cursor.execute('''
            SELECT COUNT(*) as count FROM grades 
            WHERE updated_at > ?
        ''', (since_datetime.strftime('%Y-%m-%d %H:%M:%S'),))
        
        grade_updates = cursor.fetchone()['count']
        if grade_updates > 0:
            updates.append({
                'type': 'grade_updated',
                'count': grade_updates,
                'timestamp': datetime.now().timestamp() * 1000
            })
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'updates': updates,
            'timestamp': datetime.now().timestamp() * 1000
        })
        
    except Exception as e:
        logger.error(f"检查更新失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def init_realtime(app):
    """初始化实时更新模块"""
    app.register_blueprint(realtime_bp)
    logger.info("实时更新模块已初始化")
