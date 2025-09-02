# -*- coding: utf-8 -*-
"""
系统API蓝图
包含健康检查、用户信息、登出等通用API
"""

from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user, logout_user
from config_manager import config
import logging

# 创建系统API蓝图
system_api_bp = Blueprint('system_api', __name__, url_prefix='/api')

logger = logging.getLogger(__name__)

@system_api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查API"""
    return jsonify({'status': 'ok', 'message': '服务正常运行'})

@system_api_bp.route('/current-user', methods=['GET'])
@login_required
def get_current_user():
    """获取当前用户信息"""
    try:
        # 获取当前用户的基本信息
        user_info = {
            'id': current_user.id,
            'username': current_user.username,
            'is_admin': current_user.is_admin
        }
        
        # 获取用户的班级信息
        if hasattr(current_user, 'class_id') and current_user.class_id:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT class_name FROM classes WHERE id = ?', (current_user.class_id,))
            class_result = cursor.fetchone()
            if class_result:
                user_info['class_id'] = current_user.class_id
                user_info['class_name'] = class_result['class_name']
            conn.close()
        
        return jsonify({
            'status': 'success',
            'user': user_info
        })
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '获取用户信息失败'
        }), 500

@system_api_bp.route('/logout', methods=['POST', 'GET'])
def api_logout():
    """API方式的登出，用于前端AJAX调用"""
    try:
        if current_user.is_authenticated:
            logout_user()
            session.clear()
            session.modified = True
        
        return jsonify({'status': 'ok', 'message': '已成功登出'})
    except Exception as e:
        logger.error(f"登出出错: {str(e)}")
        return jsonify({'status': 'error', 'message': '登出过程中发生错误'}), 500

@system_api_bp.route('/database-info', methods=['GET'])
def database_info():
    """获取数据库信息"""
    try:
        import os
        db_path = os.path.abspath(config.DATABASE)
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        
        # 获取数据库表的行数
        conn = config.get_db_connection()
        cursor = conn.cursor()
        
        tables_info = {}
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table['name']
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            count = cursor.fetchone()['count']
            tables_info[table_name] = count
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'database': {
                'path': db_path,
                'size_mb': round(db_size / (1024 * 1024), 2),
                'tables': tables_info
            }
        })
    except Exception as e:
        logger.error(f"获取数据库信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取数据库信息失败: {str(e)}'
        }), 500 