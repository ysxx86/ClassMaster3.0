import os
import shutil
import sqlite3
import datetime
import json
import logging
import time
import uuid
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from functools import wraps

# 配置
DATABASE = 'students.db'
BACKUP_FOLDER = 'uploads/backups'
BACKUP_INFO_FILE = os.path.join(BACKUP_FOLDER, 'backup_info.json')

# 确保备份文件夹存在
os.makedirs(BACKUP_FOLDER, exist_ok=True)

# 创建蓝图
backup_bp = Blueprint('backup', __name__)

# 配置日志
logger = logging.getLogger(__name__)

# 管理员验证装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({
                "status": "error",
                "message": "需要管理员权限"
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_backup_info():
    """获取备份信息"""
    if not os.path.exists(BACKUP_INFO_FILE):
        return []
    
    try:
        with open(BACKUP_INFO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取备份信息失败: {str(e)}")
        return []

def save_backup_info(backups):
    """保存备份信息"""
    try:
        with open(BACKUP_INFO_FILE, 'w', encoding='utf-8') as f:
            json.dump(backups, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存备份信息失败: {str(e)}")
        return False

def create_backup():
    """创建数据库备份"""
    try:
        # 生成备份文件名
        timestamp = datetime.datetime.now()
        backup_id = str(uuid.uuid4())
        formatted_time = timestamp.strftime("%Y%m%d_%H%M%S")
        backup_filename = f"students_backup_{formatted_time}.db"
        backup_path = os.path.join(BACKUP_FOLDER, backup_filename)
        
        # 确保数据库文件存在
        if not os.path.exists(DATABASE):
            return {
                "status": "error",
                "message": "数据库文件不存在"
            }
        
        # 复制数据库文件
        shutil.copy2(DATABASE, backup_path)
        
        # 获取文件大小（字节）
        file_size = os.path.getsize(backup_path)
        
        # 获取现有备份信息
        backups = get_backup_info()
        
        # 添加新备份信息
        backup_info = {
            "id": backup_id,
            "filename": backup_filename,
            "timestamp": timestamp.isoformat(),
            "size": file_size,
            "description": "系统自动备份"
        }
        
        backups.append(backup_info)
        
        # 保存备份信息
        if not save_backup_info(backups):
            # 如果保存信息失败，删除备份文件
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return {
                "status": "error",
                "message": "保存备份信息失败"
            }
        
        return {
            "status": "success",
            "message": "数据库备份创建成功",
            "backup": backup_info
        }
    except Exception as e:
        logger.error(f"创建备份失败: {str(e)}")
        return {
            "status": "error",
            "message": f"创建备份失败: {str(e)}"
        }

def restore_backup(backup_id):
    """恢复数据库备份"""
    try:
        # 获取备份信息
        backups = get_backup_info()
        backup = next((b for b in backups if b["id"] == backup_id), None)
        
        if not backup:
            return {
                "status": "error",
                "message": "找不到指定的备份"
            }
        
        backup_path = os.path.join(BACKUP_FOLDER, backup["filename"])
        
        # 检查备份文件是否存在
        if not os.path.exists(backup_path):
            return {
                "status": "error",
                "message": "备份文件不存在"
            }
        
        # 创建当前数据库的临时备份（以防恢复失败）
        temp_backup = f"{DATABASE}.temp"
        shutil.copy2(DATABASE, temp_backup)
        
        try:
            # 关闭所有数据库连接
            # 注意：这在实际应用中可能需要更复杂的处理
            time.sleep(1)  # 给现有连接一些时间完成操作
            
            # 复制备份文件到数据库文件
            shutil.copy2(backup_path, DATABASE)
            
            # 恢复成功，删除临时备份
            if os.path.exists(temp_backup):
                os.remove(temp_backup)
            
            return {
                "status": "success",
                "message": "数据库恢复成功"
            }
        except Exception as e:
            # 恢复失败，还原数据库
            if os.path.exists(temp_backup):
                shutil.copy2(temp_backup, DATABASE)
                os.remove(temp_backup)
            
            raise e
    except Exception as e:
        logger.error(f"恢复备份失败: {str(e)}")
        return {
            "status": "error",
            "message": f"恢复备份失败: {str(e)}"
        }

def delete_backup(backup_id):
    """删除数据库备份"""
    try:
        # 获取备份信息
        backups = get_backup_info()
        backup = next((b for b in backups if b["id"] == backup_id), None)
        
        if not backup:
            return {
                "status": "error",
                "message": "找不到指定的备份"
            }
        
        backup_path = os.path.join(BACKUP_FOLDER, backup["filename"])
        
        # 删除备份文件
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        # 更新备份信息
        backups = [b for b in backups if b["id"] != backup_id]
        
        # 保存备份信息
        if not save_backup_info(backups):
            return {
                "status": "error",
                "message": "更新备份信息失败"
            }
        
        return {
            "status": "success",
            "message": "备份已成功删除"
        }
    except Exception as e:
        logger.error(f"删除备份失败: {str(e)}")
        return {
            "status": "error",
            "message": f"删除备份失败: {str(e)}"
        }

# API路由
@backup_bp.route('/api/database/backups', methods=['GET'])
@login_required
@admin_required
def get_backups():
    """获取所有备份"""
    try:
        backups = get_backup_info()
        # 按时间降序排序
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return jsonify({
            "status": "success",
            "backups": backups
        })
    except Exception as e:
        logger.error(f"获取备份列表失败: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"获取备份列表失败: {str(e)}"
        }), 500

@backup_bp.route('/api/database/backup', methods=['POST'])
@login_required
@admin_required
def create_backup_api():
    """创建备份API"""
    result = create_backup()
    if result["status"] == "success":
        return jsonify(result)
    else:
        return jsonify(result), 500

@backup_bp.route('/api/database/restore/<backup_id>', methods=['POST'])
@login_required
@admin_required
def restore_backup_api(backup_id):
    """恢复备份API"""
    result = restore_backup(backup_id)
    if result["status"] == "success":
        return jsonify(result)
    else:
        return jsonify(result), 500

@backup_bp.route('/api/database/backup/<backup_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_backup_api(backup_id):
    """删除备份API"""
    result = delete_backup(backup_id)
    if result["status"] == "success":
        return jsonify(result)
    else:
        return jsonify(result), 500

def init_backup(app=None):
    """初始化备份模块"""
    # 确保备份文件夹存在
    os.makedirs(BACKUP_FOLDER, exist_ok=True)
    
    # 如果备份信息文件不存在，创建一个空的
    if not os.path.exists(BACKUP_INFO_FILE):
        save_backup_info([])
    
    logger.info("数据库备份模块已初始化") 