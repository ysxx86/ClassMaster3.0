# -*- coding: utf-8 -*-
"""
ClassMaster 2.2 - 智能班级管理系统主服务器
重构后的版本，使用统一的配置和依赖管理
"""

# 使用新的依赖管理器
from dependency_manager import install_required_packages

# 检查并安装依赖
install_required_packages()

# 导入统一配置管理器
from config_manager import config, DATABASE, UPLOAD_FOLDER, TEMPLATE_FOLDER, EXPORTS_FOLDER

import os
import json
import argparse
import re
import random
from functools import wraps
import threading
from utils.excel_processor import ExcelProcessor

# 依赖检查已通过dependency_manager处理

# 导入应用工厂
from app_factory import create_app
from flask import Flask, request, jsonify, send_from_directory, render_template, url_for, send_file, make_response, redirect, flash, session
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
import os
import sqlite3
import pandas as pd
import datetime
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from werkzeug.utils import secure_filename
import shutil
import time
import logging
import traceback
from utils.pdf_exporter_fixed import export_comments_to_pdf  # 导入修复后的PDF导出函数
from utils.comment_generator import CommentGenerator
from utils.report_exporter import ReportExporter
# 导入学生模块
from students import students_bp, create_student_template

# 导入评语模块
from comments import comments_bp, init_comments

# 导入成绩模块
from grades import grades_bp, init_grades

# 导入德育模块
from deyu import deyu_bp, init_deyu

# 导入成绩分析模块
from grade_analysis import grade_analysis_bp, init_grade_analysis

# 导入用户模块
from users import users_bp, init_users

# 导入班级模块
from classes import classes_bp, init_classes

# 导入数据库备份模块
from database_backup import backup_bp, init_backup

# 导入仪表盘模块
try:
    from dashboard import init_dashboard
    print("✓ 仪表盘模块已导入")
    dashboard_enabled = True
except ImportError:
    print("! 仪表盘模块导入失败，相关功能将不可用")
    dashboard_enabled = False

# 设置DeepSeek API全局变量
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
deepseek_api = None

# 尝试导入和初始化DeepSeek API
try:
    from utils.deepseek_api import DeepSeekAPI
    if DEEPSEEK_API_KEY:
        deepseek_api = DeepSeekAPI(DEEPSEEK_API_KEY)
        print("✓ DeepSeek API 已初始化")
    else:
        deepseek_api = DeepSeekAPI(None)
        print("! DeepSeek API密钥未设置，AI评语生成功能不可用")
except ImportError:
    print("! 无法导入DeepSeekAPI，AI评语生成功能不可用")
    deepseek_api = None

# 使用统一配置管理器的系统设置
SYSTEM_SETTINGS = config.system_settings
DEEPSEEK_API_KEY = config.DEEPSEEK_API_KEY

logger = logging.getLogger(__name__)
logger.info("服务器启动")

# 创建Flask应用，指定静态文件夹
app = Flask(__name__, 
            static_url_path='', 
            static_folder='./',
            template_folder='templates')
CORS(app)  # 启用跨域资源共享

# 设置密钥（用于会话安全）
app.secret_key = config.SECRET_KEY
app.config['JSON_AS_ASCII'] = config.JSON_AS_ASCII
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # 禁用JSON美化，减少响应大小
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# 初始化登录管理
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'users.login'  # 设置登录视图的端点

# 系统设置已通过config_manager加载

# 设置DeepSeek API实例
if SYSTEM_SETTINGS.get('deepseek_api_enabled'):
    from utils.deepseek_api import DeepSeekAPI
    deepseek_api = DeepSeekAPI(SYSTEM_SETTINGS.get('deepseek_api_key', ''))
    app.config['deepseek_api'] = deepseek_api
else:
    deepseek_api = None
    app.config['deepseek_api'] = None

# 额外的静态文件路由
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('js', filename)

@app.route('/fonts/<path:filename>')
def serve_fonts(filename):
    return send_from_directory('fonts', filename)

# 添加错误处理器处理404错误
@app.errorhandler(404)
def page_not_found(e):
    # 检查是否是静态资源请求
    path = request.path
    if path.startswith('/css/') or path.startswith('/js/') or path.startswith('/fonts/') or path.startswith('/img/'):
        # 对于静态资源请求的404，重定向到登录页面
        return redirect(url_for('users.login'))
    
    # 返回JSON响应，方便前端处理
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': '请求的资源不存在', 'code': 404}), 404
    
    # 对于普通页面请求，重定向到登录页面
    return redirect(url_for('users.login'))

# 添加405错误处理器
@app.errorhandler(405)
def method_not_allowed(e):
    # 对于API请求，返回JSON响应
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error', 
            'message': '不支持的请求方法', 
            'code': 405
        }), 405
    
    # 对于普通请求，重定向到首页
    return redirect(url_for('index'))

# 添加500错误处理器
@app.errorhandler(500)
def internal_server_error(e):
    """处理服务器内部错误"""
    # 记录错误
    app.logger.error(f"500 错误: {str(e)}")
    
    # 对于API请求，返回JSON响应
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error', 
            'message': '服务器内部错误', 
            'code': 500
        }), 500
    
    # 对于普通请求，重定向到登录页面
    return redirect(url_for('users.login'))

# API登出已移动到system_api蓝图

# 用户加载函数
@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.get_by_id(user_id)

# 添加管理员权限验证装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            # 对API请求返回JSON响应，对页面请求重定向
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': '需要管理员权限'}), 403
            flash('该操作需要管理员权限。', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# 注册学生蓝图
app.register_blueprint(students_bp)

# 注册评语蓝图
app.register_blueprint(comments_bp)

# 注册成绩蓝图
app.register_blueprint(grades_bp)

# 注册德育蓝图
app.register_blueprint(deyu_bp)

# 注册成绩分析蓝图
app.register_blueprint(grade_analysis_bp)

# 注册用户蓝图
app.register_blueprint(users_bp)

# 注册班级蓝图
app.register_blueprint(classes_bp)

# 注册数据库备份模块蓝图
app.register_blueprint(backup_bp)

# 注册系统API蓝图
from system_api import system_api_bp
app.register_blueprint(system_api_bp)

# 注册班级导出蓝图
from class_export import class_export_bp
app.register_blueprint(class_export_bp)

# 全局错误处理中间件
@app.before_request
def before_request():
    """全局请求前处理"""
    # 记录请求信息，便于调试
    if app.debug:
        app.logger.debug(f"收到请求: {request.method} {request.path}")

@app.after_request
def after_request(response):
    """全局请求后处理"""
    # 记录响应状态，便于调试
    if app.debug and response.status_code >= 400:
        app.logger.debug(f"响应状态: {response.status_code}")
    
    # 确保会话状态被保存
    if hasattr(request, 'session'):
        session.modified = True
    
    return response

# 初始化评语模块
init_comments(app)

# 初始化成绩模块
init_grades(app)

# 初始化德育模块
init_deyu(app)

# 初始化成绩分析模块
init_grade_analysis(app)

# 初始化用户模块
init_users()

# 初始化班级模块
init_classes()

# 初始化数据库备份模块
init_backup()

# 初始化仪表盘模块
if dashboard_enabled:
    try:
        dashboard_components = init_dashboard(app)
        print("✓ 仪表盘功能已初始化")
    except Exception as e:
        print(f"! 仪表盘初始化失败: {str(e)}")
        dashboard_enabled = False

# 全局API: 密码修改
@app.route('/api/change-password', methods=['POST'])
@login_required
def global_change_password():
    """全局API: 密码修改，转发到users_bp的change_password函数"""
    from users import change_password
    return change_password()

# 轮播图片管理API
@app.route('/api/carousel/images', methods=['GET'])
def get_carousel_images():
    """获取轮播图片列表"""
    try:
        # 创建目录（如果不存在）
        backgrounds_dir = os.path.join('img', 'backgrounds')
        if not os.path.exists(backgrounds_dir):
            os.makedirs(backgrounds_dir)
            
        # 获取轮播设置中的最大图片数量
        max_images = 0  # 0表示不限制
        try:
            settings_file = os.path.join('img', 'carousel_settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if 'maxImages' in settings:
                        max_images = int(settings['maxImages'])
        except (json.JSONDecodeError, ValueError, TypeError, FileNotFoundError) as e:
            logger.warning(f"获取轮播设置中的maxImages失败: {str(e)}")
            
        # 获取所有图片文件
        image_files = []
        for filename in os.listdir(backgrounds_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                file_path = os.path.join(backgrounds_dir, filename)
                # 获取文件大小（以MB为单位）和修改时间
                size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # 尝试从文件名提取序号，用于排序
                try:
                    # 匹配bg01.jpg, bg02.jpg等格式的文件名
                    match = re.match(r'bg(\d+)\.(jpg|jpeg|png)', filename.lower())
                    if match:
                        order = int(match.group(1))
                    else:
                        # 如果不是标准格式，则使用文件修改时间的时间戳作为排序依据
                        order = int(os.path.getmtime(file_path))
                except (ValueError, TypeError):
                    # 如果提取失败，则使用文件修改时间的时间戳
                    order = int(os.path.getmtime(file_path))
                
                image_files.append({
                    'name': filename,
                    'url': f'/img/backgrounds/{filename}',  # 路径保持不变，确保不会被重复添加前缀
                    'size': size_mb,
                    'modified': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'order': order  # 添加排序字段
                })
        
        # 按order字段排序
        image_files.sort(key=lambda x: x['order'])
        
        # 如果设置了最大图片数量且大于0，则限制返回的图片数量
        if max_images > 0 and len(image_files) > max_images:
            image_files = image_files[:max_images]
            logger.info(f"限制轮播图片数量为{max_images}张")
        
        # 移除order字段，不需要返回给前端
        for img in image_files:
            img.pop('order', None)
        
        # 确保Content-Type正确设置为application/json
        response = jsonify({
            'status': 'success',
            'images': image_files
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        logger.error(f"获取轮播图片列表失败: {str(e)}")
        response = jsonify({
            'status': 'error',
            'message': f'获取轮播图片失败: {str(e)}'
        }), 500
        if response[0]:
            response[0].headers['Content-Type'] = 'application/json'
        return response

@app.route('/api/carousel/images', methods=['POST'])
@login_required
def upload_carousel_image():
    """上传轮播图片"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            logger.error("未找到上传的文件，request.files内容：%s", request.files)
            return jsonify({
                'status': 'error',
                'message': '未找到上传的文件'
            }), 400
            
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': '未选择文件'
            }), 400
            
        # 检查文件类型
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            return jsonify({
                'status': 'error',
                'message': '只支持JPG或PNG格式的图片'
            }), 400
            
        # 检查文件大小 (限制为5MB)
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # 重置文件指针到开头
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'status': 'error',
                'message': f'文件过大，最大支持5MB，当前文件大小: {round(file_size / (1024 * 1024), 2)}MB'
            }), 400
            
        # 验证图片内容
        try:
            from PIL import Image
            img = Image.open(file)
            img.verify()  # 验证图片文件
            file.seek(0)  # 重置文件指针
            
            # 获取图片尺寸
            img = Image.open(file)
            width, height = img.size
            file.seek(0)  # 重置文件指针
            
            # 检查图片尺寸 (可选，确保图片符合展示要求)
            MIN_WIDTH, MIN_HEIGHT = 800, 400  # 最小宽高要求
            if width < MIN_WIDTH or height < MIN_HEIGHT:
                return jsonify({
                    'status': 'error',
                    'message': f'图片尺寸过小，建议至少{MIN_WIDTH}x{MIN_HEIGHT}像素，当前尺寸: {width}x{height}像素'
                }), 400
        except Exception as e:
            logger.error(f"验证图片失败: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'无效的图片文件: {str(e)}'
            }), 400
            
        # 创建目录（如果不存在）
        backgrounds_dir = os.path.join('img', 'backgrounds')
        try:
            if not os.path.exists(backgrounds_dir):
                os.makedirs(backgrounds_dir)
                logger.info(f"创建轮播图片目录：{backgrounds_dir}")
        except Exception as e:
            logger.error(f"创建轮播图片目录失败: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'无法创建图片存储目录: {str(e)}'
            }), 500
            
        # 获取现有文件数量
        existing_files = [f for f in os.listdir(backgrounds_dir) 
                         if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # 处理替换逻辑
        replace_mode = False
        replace_index = 0
        if 'replace_index' in request.form:
            try:
                replace_index = int(request.form['replace_index'])
                if replace_index > 0:  # 任何大于0的索引都有效
                    replace_mode = True
            except ValueError:
                pass
        
        # 如果是替换模式，使用现有的文件名
        if replace_mode:
            # 查找对应索引的文件
            matching_files = [f for f in existing_files if f.startswith(f"bg{replace_index:02d}")]
            if matching_files:
                # 删除旧文件
                for old_file in matching_files:
                    old_path = os.path.join(backgrounds_dir, old_file)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                        logger.info(f"删除准备替换的轮播图片：{old_file}")
                
                # 使用相同索引和新文件的扩展名
                file_ext = os.path.splitext(file.filename)[1].lower()
                new_filename = f"bg{replace_index:02d}{file_ext}"
            else:
                # 如果未找到指定索引的文件，使用新索引
                file_ext = os.path.splitext(file.filename)[1].lower()
                new_filename = f"bg{len(existing_files) + 1:02d}{file_ext}"
        else:
            # 生成新的文件名，使用当前最大索引+1
            max_index = 0
            for f in existing_files:
                match = re.match(r'bg(\d+)\.(jpg|jpeg|png)', f.lower())
                if match:
                    try:
                        index = int(match.group(1))
                        max_index = max(max_index, index)
                    except ValueError:
                        continue
            
            file_ext = os.path.splitext(file.filename)[1].lower()
            new_filename = f"bg{max_index + 1:02d}{file_ext}"
        
        # 保存文件
        file_path = os.path.join(backgrounds_dir, new_filename)
        file.save(file_path)
        
        # 记录日志
        logger.info(f"成功{'替换' if replace_mode else '上传'}轮播图片：{new_filename}")
        
        # 返回成功响应
        return jsonify({
            'status': 'success',
            'message': f"图片{'替换' if replace_mode else '上传'}成功",
            'image': {
                'name': new_filename,
                'url': f'/img/backgrounds/{new_filename}',  # 确保URL路径正确
                'size': round(os.path.getsize(file_path) / (1024 * 1024), 2),
                'modified': datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        logger.error(f"上传轮播图片失败: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'上传图片失败: {str(e)}'
        }), 500

@app.route('/api/carousel/images/<filename>', methods=['DELETE'])
@login_required
def delete_carousel_image(filename):
    """删除轮播图片"""
    try:
        # 安全检查文件名
        if '..' in filename or '/' in filename:
            return jsonify({
                'status': 'error',
                'message': '无效的文件名'
            }), 400
            
        # 检查文件是否存在
        backgrounds_dir = os.path.join('img', 'backgrounds')
        file_path = os.path.join(backgrounds_dir, filename)
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': '文件不存在'
            }), 404
            
        # 删除文件
        os.remove(file_path)
        
        # 记录日志
        logger.info(f"成功删除轮播图片：{filename}")
        
        # 重命名其他文件以保持连续序号
        try:
            # 获取剩余文件并按名称排序
            remaining_files = [f for f in os.listdir(backgrounds_dir) 
                              if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            remaining_files.sort()
            
            # 按序号依次重命名
            for i, old_name in enumerate(remaining_files):
                # 获取文件扩展名
                _, file_ext = os.path.splitext(old_name)
                # 新文件名
                new_name = f"bg{i+1:02d}{file_ext}"
                # 如果与当前名称不同，则重命名
                if old_name != new_name:
                    old_path = os.path.join(backgrounds_dir, old_name)
                    new_path = os.path.join(backgrounds_dir, new_name)
                    os.rename(old_path, new_path)
                    logger.info(f"轮播图片重命名：{old_name} -> {new_name}")
        except Exception as e:
            # 重命名错误不影响删除操作的结果，仅记录日志
            logger.error(f"重命名轮播图片失败: {str(e)}", exc_info=True)
        
        # 返回成功响应
        return jsonify({
            'status': 'success',
            'message': '图片删除成功'
        })
    except Exception as e:
        logger.error(f"删除轮播图片失败: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'删除图片失败: {str(e)}'
        }), 500

@app.route('/api/carousel/settings', methods=['GET'])
def get_carousel_settings():
    """获取轮播设置"""
    try:
        # 获取或创建默认设置
        settings_file = os.path.join('img', 'carousel_settings.json')
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            # 默认设置
            settings = {
                'interval': 5000,
                'animation': 'fade',
                'indicatorStyle': 'rounded-pill',
                'indicatorColor': '#3498db',
                'showProgress': True,
                'maxImages': 5  # 默认最大显示5张图片
            }
            
        # 确保Content-Type正确设置为application/json
        response = jsonify({
            'status': 'success',
            'settings': settings
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        logger.error(f"获取轮播设置失败: {str(e)}")
        response = jsonify({
            'status': 'error',
            'message': f'获取轮播设置失败: {str(e)}'
        }), 500
        if response[0]:
            response[0].headers['Content-Type'] = 'application/json'
        return response

@app.route('/api/carousel/settings', methods=['POST'])
@login_required  # 保留保存设置的登录验证，只有登录用户才能修改设置
def save_carousel_settings():
    """保存轮播设置"""
    try:
        # 获取设置数据
        settings = request.json
        
        # 验证所需字段
        required_fields = ['interval', 'animation', 'indicatorStyle', 'indicatorColor', 'showProgress']
        for field in required_fields:
            if field not in settings:
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必要的设置字段: {field}'
                }), 400
        
        # 确保maxImages字段存在，如不存在则设置默认值
        if 'maxImages' not in settings:
            settings['maxImages'] = 5
        
        # 验证maxImages为数字且大于0
        try:
            max_images = int(settings['maxImages'])
            if max_images <= 0:
                settings['maxImages'] = 5
        except (ValueError, TypeError):
            settings['maxImages'] = 5
            
        # 创建目录（如果不存在）
        img_dir = os.path.join('img')
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
            
        # 保存设置
        settings_file = os.path.join('img', 'carousel_settings.json')
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            'status': 'success',
            'message': '轮播设置保存成功'
        })
    except Exception as e:
        logger.error(f"保存轮播设置失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'保存轮播设置失败: {str(e)}'
        }), 500

# 统一格式的重置密码API
@app.route('/api/users/reset-password/<int:user_id>', methods=['POST'])
@login_required
def unified_reset_password(user_id):
    """使用统一格式的重置密码API"""
    # 只有管理员可以重置密码
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '只有管理员可以重置用户密码'}), 403
    
    try:
        from werkzeug.security import generate_password_hash
        import random
        import string
        import datetime
        import sqlite3
        
        # 生成随机密码
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        
        # 生成密码哈希
        password_hash = generate_password_hash(new_password)
        
        # 更新数据库
        conn = sqlite3.connect('students.db')
        cursor = conn.cursor()
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
        UPDATE users SET password_hash = ?, updated_at = ?, reset_password = ? WHERE id = ?
        ''', (password_hash, now, new_password, user_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        conn.commit()
        conn.close()
        
        # 返回新密码
        return jsonify({
            'status': 'ok', 
            'message': '密码已重置', 
            'new_password': new_password
        })
    except Exception as e:
        logger.error(f"重置用户密码时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'重置密码失败: {str(e)}'}), 500

# 创建数据库连接
def get_db_connection():
    """获取数据库连接"""
    return config.get_db_connection()

def save_setting_to_db(key, value, description=None):
    """将设置保存到数据库的 system_settings 表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 确保 system_settings 表存在
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 插入或更新设置
        cursor.execute('''
        INSERT OR REPLACE INTO system_settings (key, value, description, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (key, value, description))
        
        conn.commit()
        conn.close()
        logger.info(f"成功保存设置到数据库: {key} = {value}")
    except Exception as e:
        logger.error(f"保存设置到数据库时出错: {key} = {value}, 错误: {str(e)}")
        if 'conn' in locals():
            conn.close()
        raise

def update_config_file():
    """从数据库读取设置并更新配置文件"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 从数据库读取所有设置
        cursor.execute('SELECT key, value FROM system_settings')
        db_settings = {row['key']: row['value'] for row in cursor.fetchall()}
        conn.close()
        
        # 更新全局配置
        if db_settings:
            config.system_settings.update(db_settings)
            # 保存到 config.json 文件
            config.save_json_config()
            logger.info("成功从数据库更新配置文件")
        else:
            logger.warning("数据库中没有找到系统设置")
            
    except Exception as e:
        logger.error(f"更新配置文件时出错: {str(e)}")
        if 'conn' in locals():
            conn.close()
        # 不抛出异常，避免阻断程序运行

# 初始化数据库
def init_db():
    logger.info("初始化数据库")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 创建学生表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        gender TEXT NOT NULL,
        class TEXT,
        class_id INTEGER,
        height REAL,
        weight REAL,
        chest_circumference REAL,
        vital_capacity REAL,
        dental_caries TEXT,
        vision_left REAL,
        vision_right REAL,
        physical_test_status TEXT,
        comments TEXT,
        pinzhi INTEGER,
        xuexi INTEGER,
        jiankang INTEGER,
        shenmei INTEGER,
        shijian INTEGER,
        shenghuo INTEGER,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    
    # 检查是否所有必要的列都存在，如果不存在则添加
    cursor.execute("PRAGMA table_info(students)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    logger.info(f"现有数据库列: {existing_columns}")
    
    # 定义应该存在的列及其类型
    expected_columns = {
        'class_id': 'INTEGER',
        'chest_circumference': 'REAL',
        'vital_capacity': 'REAL',
        'dental_caries': 'TEXT',
        'vision_left': 'REAL',
        'vision_right': 'REAL',
        'physical_test_status': 'TEXT',
        'comments': 'TEXT',
        'pinzhi': 'INTEGER',
        'xuexi': 'INTEGER',
        'jiankang': 'INTEGER',
        'shenmei': 'INTEGER',
        'shijian': 'INTEGER',
        'shenghuo': 'INTEGER'
    }
    
    # 添加缺失的列
    for column, col_type in expected_columns.items():
        if column not in existing_columns:
            logger.warning(f"添加缺失的列: {column} ({col_type})")
            try:
                cursor.execute(f"ALTER TABLE students ADD COLUMN {column} {col_type}")
                conn.commit()
                logger.info(f"成功添加列: {column}")
            except sqlite3.Error as e:
                logger.error(f"添加列 {column} 时出错: {e}")
    
    # 提交并关闭连接
    conn.commit()
    conn.close()
    
    logger.info("数据库初始化完成")

# 重置数据库功能
def reset_db():
    """重置数据库，备份旧数据库并创建新的"""
    try:
        # 如果数据库存在，创建备份
        if os.path.exists(DATABASE):
            backup_path = f"{DATABASE}.backup_{int(time.time())}"
            shutil.copy2(DATABASE, backup_path)
            logger.info(f"创建数据库备份: {backup_path}")
            
            # 删除旧数据库
            os.remove(DATABASE)
            logger.info(f"删除旧数据库: {DATABASE}")
        
        # 初始化新数据库
        init_db()
        return True, "数据库已成功重置，旧数据已备份"
    except Exception as e:
        logger.error(f"重置数据库时出错: {e}")
        logger.error(traceback.format_exc())
        return False, f"重置数据库失败: {str(e)}"

# 初始化数据库
init_db()

# 创建模板文件
try:
    create_student_template()
except Exception as e:
    print(f"创建学生模板时出错: {str(e)}")

# 初始化用户表
init_users()

# 初始化班级模块
init_classes()

# 全局变量
DATABASE_FILE = os.environ.get('CLASS_MASTER_DB', 'classmaster.db')
LOG_FILE = os.environ.get('CLASS_MASTER_LOG', 'classmaster.log')

# 主页路由
@app.route('/')
@login_required
def index():
    return send_from_directory('./', 'index.html')

# 页面路由
@app.route('/pages/<path:path>')
@login_required
def serve_pages(path):
    # 检查admin页面的访问权限
    if 'admin' in path and not current_user.is_admin:
        # 非管理员用户尝试访问管理页面，立即重定向到首页
        logger.warning(f"用户 {current_user.username} (ID: {current_user.id}) 尝试访问管理页面 {path}，但权限不足")
        return redirect(url_for('index'))
    
    return send_from_directory('pages', path)

# 健康检查API
# 健康检查API已移动到system_api蓝图

# 当前用户信息API已移动到system_api蓝图

@login_required
def download_template():
    template_path = os.path.join(TEMPLATE_FOLDER, 'student_template.xlsx')
    if not os.path.exists(template_path):
        create_student_template()
    
    return jsonify({
        'status': 'ok',
        'message': '模板文件准备就绪',
        'template_url': f'/download/template/student_template.xlsx'
    })

# 提供模板下载
@app.route('/download/template/<filename>', methods=['GET'])
@login_required
def serve_template(filename):
    return send_from_directory(TEMPLATE_FOLDER, filename)

# 获取所有学生API
@app.route('/api/students', methods=['GET'], strict_slashes=False)
@login_required
def get_all_students():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students ORDER BY CAST(id AS INTEGER)')
    students = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'count': len(students),
        'students': students
    })

# 添加权限检查通用函数
def check_student_access(student_id):
    """
    检查当前用户是否有权限访问指定学生
    
    Args:
        student_id: 学生ID
        
    Returns:
        bool: 是否有访问权限
    """
    # 管理员可以访问所有学生
    if current_user.is_admin:
        return True
    
    # 获取学生的班级ID
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT class_id FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    
    if not student:
        return False
    
    # 班主任只能访问自己班级的学生
    student_class_id = student[0]  # 使用索引0访问第一列的值
    teacher_class_id = current_user.class_id
    
    # 记录详细的权限检查日志
    logger.info(f"权限检查: 用户={current_user.username}, 学生ID={student_id}, "
               f"学生班级ID={student_class_id}, 班主任班级ID={teacher_class_id}")
    
    # 检查班级ID是否匹配
    return student_class_id == teacher_class_id

# 获取单个学生API
@app.route('/api/students/<student_id>', methods=['GET'], strict_slashes=False)
@login_required
def get_student(student_id):
    # 获取数据库连接
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查询学生信息
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    # 如果学生不存在，直接返回404
    if not student:
        conn.close()
        return jsonify({'status': 'error', 'message': '未找到学生'}), 404
    
    # 使用权限检查函数
    if not check_student_access(student_id):
        conn.close()
        logger.warning(f"用户 {current_user.username} (ID: {current_user.id}) 尝试访问非本班学生 {student_id}，权限不足")
        return jsonify({'status': 'error', 'message': '权限不足，无法访问非本班学生'}), 403
    
    # 关闭数据库连接
    conn.close()
    
    # 返回学生信息
    return jsonify({
        'status': 'ok',
        'student': dict(student)
    })

# 添加新学生API
@app.route('/api/students', methods=['POST'], strict_slashes=False)
@login_required
def add_student():
    data = request.json
    
    if not data:
        return jsonify({'status': 'error', 'message': '无效的请求数据'}), 400
    
    required_fields = ['id', 'name', 'gender']
    for field in required_fields:
        if field not in data:
            return jsonify({'status': 'error', 'message': f'缺少必要的字段: {field}'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查学生ID是否已存在
    cursor.execute('SELECT id FROM students WHERE id = ?', (data['id'],))
    if cursor.fetchone():
        conn.close()
        return jsonify({'status': 'error', 'message': f'学号 {data["id"]} 已存在'}), 400
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 确保数值类型字段的正确处理
    height = data.get('height')
    weight = data.get('weight')
    chest_circumference = data.get('chest_circumference')
    vital_capacity = data.get('vital_capacity')
    vision_left = data.get('vision_left')
    vision_right = data.get('vision_right')
    
    try:
        cursor.execute('''
        INSERT INTO students (
            id, name, gender, class, height, weight,
            chest_circumference, vital_capacity, dental_caries,
            vision_left, vision_right, physical_test_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data['name'], data['gender'], data.get('class', ''),
            height, weight, 
            chest_circumference, vital_capacity, data.get('dental_caries', ''),
            vision_left, vision_right, data.get('physical_test_status', ''),
            now, now
        ))
        
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'message': f'成功添加学生: {data["name"]}',
            'student_id': data['id']
        })
    except Exception as e:
        conn.rollback()
        print(f"添加学生时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'添加学生时出错: {str(e)}'}), 500
    finally:
        conn.close()

# 更新学生API
@app.route('/api/students/<student_id>', methods=['PUT'], strict_slashes=False)
@login_required
def update_student(student_id):
    logger.info(f"收到更新学生信息请求，学生ID: {student_id}")
    
    try:
        data = request.json
        logger.info(f"请求数据: {data}")
        
        if not data:
            logger.error("无效的请求数据")
            return jsonify({'status': 'error', 'message': '无效的请求数据'}), 400
        
        # 确保请求的ID与URL中的ID一致
        if 'id' in data and data['id'] != student_id:
            logger.error(f"URL中的ID({student_id})与请求体中的ID({data['id']})不一致")
            return jsonify({'status': 'error', 'message': '学生ID不一致'}), 400
        
        # 使用权限检查函数
        if not check_student_access(student_id):
            logger.warning(f"用户 {current_user.username} (ID: {current_user.id}) 尝试修改非本班学生 {student_id}，权限不足")
            return jsonify({'status': 'error', 'message': '权限不足，无法修改非本班学生'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学生是否存在
        cursor.execute('SELECT id FROM students WHERE id = ?', (student_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': f'未找到学号为 {student_id} 的学生'}), 404
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 更详细的数值处理和日志
        numeric_fields = {
            'height': 'height',
            'weight': 'weight',
            'chest_circumference': 'chest_circumference',
            'vital_capacity': 'vital_capacity',
            'vision_left': 'vision_left',
            'vision_right': 'vision_right',
        }
        
        processed_values = {}
        
        # 处理数值字段
        for field, db_field in numeric_fields.items():
            raw_value = data.get(field, None)
            logger.info(f"字段 {field} 原始值: {raw_value}, 类型: {type(raw_value).__name__}")
            
            try:
                if raw_value is None or raw_value == '' or raw_value == 'null' or raw_value == 'undefined':
                    processed_values[db_field] = None
                    logger.info(f"字段 {field} 设为None")
                else:
                    # 如果是字符串，处理逗号等
                    if isinstance(raw_value, str):
                        # 替换逗号为点
                        raw_value = raw_value.replace(',', '.')
                        logger.info(f"字段 {field} 预处理后: {raw_value}")
                    
                    # 转换为浮点数
                    value = float(raw_value)
                    # 处理0值
                    processed_values[db_field] = 0.0 if value == 0 else value
                    logger.info(f"字段 {field} 成功转换为: {processed_values[db_field]}")
            except (ValueError, TypeError) as e:
                logger.warning(f"字段 {field} 值 '{raw_value}' 转换错误: {str(e)}")
                processed_values[db_field] = None
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(students)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"数据库表列: {existing_columns}")
        
        # 检查所需列是否存在，如不存在则添加
        required_columns = list(numeric_fields.values()) + ['dental_caries', 'physical_test_status']
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.warning(f"数据库表缺少列: {missing_columns}")
            for column in missing_columns:
                column_type = "TEXT" if column in ['dental_caries', 'physical_test_status'] else "REAL"
                logger.info(f"添加缺失的列: {column} ({column_type})")
                try:
                    cursor.execute(f"ALTER TABLE students ADD COLUMN {column} {column_type}")
                except sqlite3.Error as e:
                    logger.error(f"添加列 {column} 时出错: {str(e)}")
            
            conn.commit()
            logger.info("已添加缺失的列")
        
        # 构建更新SQL
        update_fields = []
        params = []
        
        # 基本字段
        update_fields.append("name = ?")
        params.append(data.get('name', ''))
        
        update_fields.append("gender = ?")
        params.append(data.get('gender', ''))
        
        update_fields.append("class = ?")
        params.append(data.get('class', ''))
        
        # 数值字段
        for db_field in numeric_fields.values():
            if db_field in existing_columns:
                update_fields.append(f"{db_field} = ?")
                params.append(processed_values.get(db_field))
        
        # 文本字段
        if 'dental_caries' in existing_columns:
            update_fields.append("dental_caries = ?")
            params.append(data.get('dental_caries', ''))
        
        if 'physical_test_status' in existing_columns:
            update_fields.append("physical_test_status = ?")
            params.append(data.get('physical_test_status', ''))
        
        # 更新时间
        update_fields.append("updated_at = ?")
        params.append(now)
        
        # 添加WHERE条件
        params.append(student_id)
        
        # 构建完整的SQL语句
        update_sql = f"UPDATE students SET {', '.join(update_fields)} WHERE id = ?"
        logger.info(f"更新SQL: {update_sql}")
        logger.info(f"参数: {params}")
        
        # 执行更新
        cursor.execute(update_sql, params)
        conn.commit()
        
        logger.info(f"成功更新学生信息: ID={student_id}, 名称={data.get('name', 'unknown')}")
        
        return jsonify({
            'status': 'ok',
            'message': f'成功更新学生信息: {data.get("name", student_id)}',
            'student_id': student_id
        })
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        error_msg = f"数据库错误: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        error_msg = f"更新学生信息时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
    finally:
        if conn:
            conn.close()

# 删除学生API
@app.route('/api/students/<student_id>', methods=['DELETE'], strict_slashes=False)
@login_required
def delete_student(student_id):
    # 使用权限检查函数
    if not check_student_access(student_id):
        logger.warning(f"用户 {current_user.username} (ID: {current_user.id}) 尝试删除非本班学生 {student_id}，权限不足")
        return jsonify({'status': 'error', 'message': '权限不足，无法删除非本班学生'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查学生是否存在
    cursor.execute('SELECT id, name FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return jsonify({'status': 'error', 'message': f'未找到学号为 {student_id} 的学生'}), 404
    
    student_name = student['name']
    
    try:
        cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'message': f'成功删除学生: {student_name}',
            'student_id': student_id
        })
    except Exception as e:
        conn.rollback()
        logger.error(f"删除学生时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'删除学生时出错: {str(e)}'}), 500
    finally:
        conn.close()

# 重置数据库API
@app.route('/api/reset-database', methods=['POST'])
def reset_database_api():
    # 安全检查，要求确认参数
    data = request.json or {}
    confirm = data.get('confirm', False)
    
    if not confirm:
        return jsonify({
            'status': 'error',
            'message': '请提供确认参数以重置数据库'
        }), 400
    
    success, message = reset_db()
    
    if success:
        return jsonify({
            'status': 'ok',
            'message': message
        })
    else:
        return jsonify({
            'status': 'error',
            'message': message
        }), 500

# 数据库信息API已移动到system_api蓝图

# 获取学生评语API - 已移至comments.py
# @app.route('/api/comments/<student_id>', methods=['GET'], strict_slashes=False)
# def get_student_comment(student_id):
#     # ... 移除此函数的内容 ...

# 保存学生评语API - 已移至comments.py
# @app.route('/api/comments', methods=['POST'], strict_slashes=False)
# def save_student_comment():
#     # ... 移除此函数的内容 ...

# 获取评语模板API - 已移至comments.py
# @app.route('/api/comment-templates', methods=['GET'])
# def get_comment_templates():
#     # ... 移除此函数的内容 ...

# 批量更新评语 - 已移至comments.py
# @app.route('/api/batch-update-comments', methods=['POST'])
# def batch_update_comments():
#     # ... 移除此函数的内容 ...

# 导出评语为PDF - 已移至comments.py
# @app.route('/api/export-comments-pdf', methods=['GET'])
# def api_export_comments_pdf():
#     # ... 移除此函数的内容 ...

# 提供导出文件下载 - 已移至comments.py
# @app.route('/download/exports/<path:filename>', methods=['GET'])
# def download_export(filename):
#     # ... 移除此函数的内容 ...

# 生成打印预览HTML - 已移至comments.py
# @app.route('/api/preview-comments', methods=['GET'])
# def api_preview_comments():
#     # ... 移除此函数的内容 ...

# AI生成评语API - 已移至comments.py
# @app.route('/api/generate-comment', methods=['POST'])
# def generate_comment():
#     # ... 移除此函数的内容 ...

# 学生成绩管理
# grades_manager已在文件开头初始化


# 测试DeepSeek API连接
@app.route('/api/test-deepseek', methods=['POST'])
@login_required
def test_deepseek_api():
    # 获取提交的API密钥
    data = request.get_json()
    api_key = data.get('api_key', '')
    
    try:
        # 测试API连接
        from utils.deepseek_api import DeepSeekAPI
        api = DeepSeekAPI(api_key)
        result = api.test_connection()
        
        # 返回测试结果
        return jsonify(result)
    except Exception as e:
        logger.error(f"测试DeepSeek API时出错: {str(e)}")
        return jsonify({"status": "error", "message": f"测试API连接时出错: {str(e)}"})

# 保存DeepSeek API设置
@app.route('/api/settings/deepseek', methods=['POST'])
@login_required
@admin_required
def save_deepseek_api_settings():
    global deepseek_api
    # 获取提交的API密钥
    data = request.get_json()
    api_key = data.get('api_key', '')
    
    try:
        # 保存API密钥到设置
        SYSTEM_SETTINGS['deepseek_api_key'] = api_key
        SYSTEM_SETTINGS['deepseek_api_enabled'] = bool(api_key)
        
        # 更新配置文件
        update_config_file()
        
        # 更新API客户端实例
        if deepseek_api:
            deepseek_api.update_api_key(api_key)
        else:
            from utils.deepseek_api import DeepSeekAPI
            deepseek_api = DeepSeekAPI(api_key)
        
        # 更新应用配置
        app.config['deepseek_api'] = deepseek_api
        
        return jsonify({
            "status": "ok",
            "message": "DeepSeek API设置已保存",
            "deepseek_api_enabled": bool(api_key)
        })
    except Exception as e:
        logger.error(f"保存DeepSeek API设置时出错: {str(e)}")
        return jsonify({"status": "error", "message": f"保存API设置时出错: {str(e)}"})

# 获取系统设置
@app.route('/api/settings', methods=['GET'])
@login_required
def get_system_settings():
    try:
        # 从数据库重新加载设置，确保获取最新数据
        update_config_file()
        
        # 添加用户权限检查，只有管理员可以获取完整的系统设置
        if not current_user.is_admin:
            # 非管理员用户，只返回有限的设置信息
            filtered_settings = {
                'system_name': SYSTEM_SETTINGS.get('system_name', '班主任管理系统'),
                'school_name': SYSTEM_SETTINGS.get('school_name', '泉州东海湾实验学校'),
                'school_year': SYSTEM_SETTINGS.get('school_year', '2024-2025'),
                'semester': SYSTEM_SETTINGS.get('semester', '2'),
                'start_date': SYSTEM_SETTINGS.get('start_date', '2025-03-01')
            }
            return jsonify({
                'status': 'ok',
                'settings': filtered_settings
            })
        
        # 管理员用户，返回完整设置
        return jsonify({
            'status': 'ok',
            'settings': SYSTEM_SETTINGS
        })
    except Exception as e:
        logger.error(f"获取系统设置时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"获取系统设置时出错: {str(e)}"
        }), 500

# 更新系统设置
@app.route('/api/settings/update', methods=['POST'])
@login_required
@admin_required
def update_system_settings():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '没有提供设置数据'
            }), 400
        
        # 更新设置
        for key, value in data.items():
            # 保存到数据库
            save_setting_to_db(key, value)
        
        # 更新配置文件
        update_config_file()
        
        return jsonify({
            'status': 'ok',
            'message': '系统设置已更新'
        })
    except Exception as e:
        logger.error(f"更新系统设置时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"更新系统设置时出错: {str(e)}"
        }), 500

# 更新学期设置
@app.route('/api/settings/semester', methods=['POST'])
@login_required
@admin_required
def update_semester_settings():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '没有提供设置数据'
            }), 400
        
        # 获取学年、学期和开学时间
        school_year = data.get('school_year')
        semester = data.get('semester')
        start_date = data.get('start_date')
        
        # 验证数据
        if not school_year or not semester or not start_date:
            return jsonify({
                'status': 'error',
                'message': '学年、学期和开学时间都是必填项'
            }), 400
        
        # 保存到数据库
        save_setting_to_db('school_year', school_year, '学年设置')
        save_setting_to_db('semester', semester, '学期设置 (1: 第一学期, 2: 第二学期)')
        save_setting_to_db('start_date', start_date, '开学时间')
        
        # 更新配置文件
        update_config_file()
        
        return jsonify({
            'status': 'ok',
            'message': '学期设置已更新'
        })
    except Exception as e:
        logger.error(f"更新学期设置时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"更新学期设置时出错: {str(e)}"
        }), 500

# 模板管理API
@app.route('/api/templates', methods=['GET'])
@login_required
def get_templates():
    try:
        template_dir = os.path.join(TEMPLATE_FOLDER, 'docx')
        os.makedirs(template_dir, exist_ok=True)
        os.makedirs(os.path.join(template_dir, 'custom'), exist_ok=True)
        
        # 获取Word模板列表
        exporter = ReportExporter(templates_dir=template_dir)
        templates = exporter.list_templates()
        
        # 获取Excel模板列表（兼容旧逻辑）
        template_files = os.listdir(TEMPLATE_FOLDER)
        excel_templates = [f for f in template_files if f.endswith('.xlsx') or f.endswith('.xls')]
        
        return jsonify({
            'status': 'ok',
            'templates': templates,
            'excel_templates': excel_templates
        })
    except Exception as e:
        logger.error(f"获取模板列表时出错: {str(e)}")
        return jsonify({"status": "error", "message": f"获取模板列表失败: {str(e)}"})

@app.route('/api/templates', methods=['POST'])
@login_required
def upload_template():
    """上传自定义报告模板"""
    try:
        if 'template' not in request.files:
            return jsonify({"status": "error", "message": "未上传模板文件"})
            
        template_file = request.files['template']
        if template_file.filename == '':
            return jsonify({"status": "error", "message": "未选择文件"})
            
        if not template_file.filename.endswith('.docx'):
            return jsonify({"status": "error", "message": "请上传.docx格式的Word文档"})
        
        # 读取文件内容
        template_data = template_file.read()
        
        # 确保模板目录存在
        template_dir = os.path.join(TEMPLATE_FOLDER, 'docx')
        custom_dir = os.path.join(template_dir, 'custom')
        os.makedirs(template_dir, exist_ok=True)
        os.makedirs(custom_dir, exist_ok=True)
        
        # 保存模板
        exporter = ReportExporter(templates_dir=template_dir)
        success, message = exporter.save_template(template_data, template_file.filename)
        
        if success:
            return jsonify({"status": "ok", "message": message})
        else:
            return jsonify({"status": "error", "message": message})
            
    except Exception as e:
        app.logger.error(f"上传模板时出错: {str(e)}")
        return jsonify({"status": "error", "message": f"上传模板失败: {str(e)}"})

# 图片路由
@app.route('/img/<path:path>')
def serve_img(path):
    return send_from_directory('img', path)

# 获取考试并检查访问权限
def get_exam_access(exam_id):
    """
    检查当前用户是否有权限访问指定的考试，并返回考试信息
    
    Args:
        exam_id: 考试ID
        
    Returns:
        考试信息字典，如果没有权限或考试不存在则返回None
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取考试信息
        cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
        exam = cursor.fetchone()
        
        if not exam:
            return None
            
        exam_dict = dict(exam)
        
        # 检查权限：管理员或班主任只能访问自己班级的考试
        if not current_user.is_admin and current_user.class_id != exam_dict['class_id']:
            return None
            
        return exam_dict
    except Exception as e:
        logger.error(f"检查考试访问权限时出错: {str(e)}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

# 上传试卷PDF
@app.route('/api/exams/<exam_id>/paper', methods=['POST'])
@login_required
def upload_exam_paper(exam_id):
    # 检查是否有权限访问该考试
    exam = get_exam_access(exam_id)
    if not exam:
        return jsonify({"status": "error", "message": "无权访问该考试或考试不存在"})
    
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "未找到上传的文件"})
        
        file = request.files['file']
        
        # 检查文件类型
        if file.filename == '':
            return jsonify({"status": "error", "message": "未选择文件"})
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"status": "error", "message": "请上传PDF格式的文件"})
        
        # 确保存储目录存在
        papers_dir = os.path.join(app.root_path, 'static', 'papers')
        if not os.path.exists(papers_dir):
            os.makedirs(papers_dir)
        
        # 保存文件
        filename = f"exam_{exam_id}_paper.pdf"
        file_path = os.path.join(papers_dir, filename)
        file.save(file_path)
        
        # 更新数据库，记录试卷已上传
        db_conn = get_db_connection()
        db_conn.execute(
            "UPDATE exams SET has_paper = 1, paper_path = ? WHERE id = ?",
            (filename, exam_id)
        )
        db_conn.commit()
        db_conn.close()
        
        # 开始后台分析任务
        # 在实际应用中，应该使用异步任务队列（如Celery）来处理
        # 这里简化处理，创建一个标记文件表示分析正在进行
        analysis_dir = os.path.join(app.root_path, 'static', 'analysis')
        if not os.path.exists(analysis_dir):
            os.makedirs(analysis_dir)
            
        processing_flag_path = os.path.join(analysis_dir, f"exam_{exam_id}_processing.flag")
        with open(processing_flag_path, 'w') as f:
            f.write('processing')
        
        # 这里模拟异步任务启动
        # 实际应用中应该将分析任务提交到任务队列
        # 为简化示例，这里假设有一个后台线程会定期检查并处理这些文件
        
        return jsonify({
            "status": "ok",
            "message": "试卷上传成功，开始分析",
            "exam_id": exam_id
        })
    except Exception as e:
        logger.error(f"上传试卷时出错: {str(e)}")
        return jsonify({"status": "error", "message": f"上传试卷时出错: {str(e)}"})

# 获取试卷分析结果
@app.route('/api/exams/<exam_id>/paper-analysis', methods=['GET'])
@login_required
def get_exam_paper_analysis(exam_id):
    # 检查是否有权限访问该考试
    exam = get_exam_access(exam_id)
    if not exam:
        return jsonify({"status": "error", "message": "无权访问该考试或考试不存在"})
    
    try:
        # 检查是否已上传试卷
        db_conn = get_db_connection()
        exam_data = db_conn.execute(
            "SELECT has_paper, paper_path FROM exams WHERE id = ?",
            (exam_id,)
        ).fetchone()
        
        if not exam_data or not exam_data['has_paper']:
            return jsonify({"status": "error", "message": "未上传试卷"})
        
        # 检查分析结果是否存在
        analysis_dir = os.path.join(app.root_path, 'static', 'analysis')
        analysis_file_path = os.path.join(analysis_dir, f"exam_{exam_id}_analysis.json")
        processing_flag_path = os.path.join(analysis_dir, f"exam_{exam_id}_processing.flag")
        
        # 如果分析结果已存在
        if os.path.exists(analysis_file_path):
            with open(analysis_file_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
                
            return jsonify({
                "status": "ok",
                "analysis": analysis_data,
                "exam_id": exam_id
            })
        # 如果分析正在进行中
        elif os.path.exists(processing_flag_path):
            return jsonify({
                "status": "processing",
                "message": "试卷分析正在进行中",
                "exam_id": exam_id
            })
        # 如果分析结果不存在，需要启动分析
        else:
            # 创建处理标记
            with open(processing_flag_path, 'w') as f:
                f.write('processing')
                
            # 在实际应用中，应该提交到任务队列异步处理
            # 为简化示例，创建一个模拟的分析结果
            
            # 获取考试相关数据
            class_id = exam['class_id']
            subjects = json.loads(exam['subjects'])
            
            # 获取学生成绩数据，用于题目错误率分析
            scores = db_conn.execute(
                "SELECT s.student_id, s.student_name, s.subject, s.score FROM scores s "
                "WHERE s.exam_id = ?",
                (exam_id,)
            ).fetchall()
            db_conn.close()
            
            # 准备测试数据
            # 实际应用中，需要从PDF解析题目数据
            subject = subjects[0]  # 假设只有一个学科
            student_scores = [s['score'] for s in scores if s['subject'] == subject]
            students_count = len(set([s['student_id'] for s in scores if s['subject'] == subject]))
            
            # 模拟题目数据
            questions_data = []
            for i in range(1, 21):  # 20道题
                # 随机生成错误率和分值
                error_rate = random.uniform(0.1, 0.9)
                score = random.choice([1, 2, 3, 5, 10])
                
                question = {
                    "number": i,
                    "type": random.choice(["选择题", "填空题", "解答题", "判断题", "应用题"]),
                    "score": score,
                    "error_rate": error_rate,
                    "student_count": students_count
                }
                questions_data.append(question)
            
            # 获取班级名称
            class_data = db_conn.execute(
                "SELECT class_name FROM classes WHERE id = ?",
                (class_id,)
            ).fetchone()
            class_name = class_data['class_name'] if class_data else "未知班级"
            
            # 使用DeepSeek API分析试卷
            if deepseek_api:
                analysis_result = deepseek_api.analyze_exam_paper(
                    questions_data,
                    student_scores,
                    subject,
                    exam['exam_name'],
                    class_name
                )
                
                # 保存分析结果
                analysis_data = {
                    "subject": subject,
                    "total_score": sum(q['score'] for q in questions_data),
                    "questions": questions_data,
                    "ai_analysis": analysis_result.get("analysis", {})
                }
                
                with open(analysis_file_path, 'w', encoding='utf-8') as f:
                    json.dump(analysis_data, f, ensure_ascii=False, indent=2)
                
                # 删除处理标记
                if os.path.exists(processing_flag_path):
                    os.remove(processing_flag_path)
                
                return jsonify({
                    "status": "ok",
                    "analysis": analysis_data,
                    "exam_id": exam_id
                })
            else:
                # DeepSeek API不可用时返回错误
                return jsonify({
                    "status": "error",
                    "message": "DeepSeek API不可用，无法进行分析",
                    "exam_id": exam_id
                })
    except Exception as e:
        logger.error(f"获取试卷分析结果时出错: {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"获取试卷分析结果时出错: {str(e)}"})

# 下载试卷分析报告
@app.route('/api/exams/<exam_id>/paper-analysis-report', methods=['GET'])
@login_required
def download_exam_paper_analysis_report(exam_id):
    # 检查是否有权限访问该考试
    exam = get_exam_access(exam_id)
    if not exam:
        return jsonify({"status": "error", "message": "无权访问该考试或考试不存在"})
    
    try:
        # 检查分析结果是否存在
        analysis_dir = os.path.join(app.root_path, 'static', 'analysis')
        analysis_file_path = os.path.join(analysis_dir, f"exam_{exam_id}_analysis.json")
        
        if not os.path.exists(analysis_file_path):
            return jsonify({"status": "error", "message": "分析结果不存在，请先进行分析"})
        
        # 读取分析结果
        with open(analysis_file_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # 创建报告文件
        reports_dir = os.path.join(app.root_path, 'static', 'reports')
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
            
        report_file_path = os.path.join(reports_dir, f"exam_{exam_id}_analysis_report.html")
        
        # 创建HTML报告内容
        # 这里简化处理，实际应用中可以使用Jinja2等模板引擎生成更复杂的报告
        subject = analysis_data.get('subject', '未知学科')
        questions = analysis_data.get('questions', [])
        ai_analysis = analysis_data.get('ai_analysis', {})
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>试卷分析报告 - {exam['exam_name']}</title>
            <style>
                body {{ font-family: 'PingFang SC', 'Helvetica Neue', Arial, sans-serif; padding: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .section {{ margin-bottom: 30px; }}
                .section-title {{ font-size: 18px; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .alert {{ padding: 15px; border-radius: 4px; margin-bottom: 15px; }}
                .alert-info {{ background-color: #d9edf7; border: 1px solid #bce8f1; color: #31708f; }}
                .alert-warning {{ background-color: #fcf8e3; border: 1px solid #faebcc; color: #8a6d3b; }}
                .card {{ border: 1px solid #ddd; border-radius: 4px; margin-bottom: 15px; }}
                .card-header {{ background-color: #f5f5f5; padding: 10px 15px; border-bottom: 1px solid #ddd; font-weight: bold; }}
                .card-body {{ padding: 15px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>试卷分析报告</h1>
                <h2>{exam['exam_name']} - {subject}</h2>
                <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="section">
                <div class="section-title">题目分析</div>
                <table>
                    <thead>
                        <tr>
                            <th>题号</th>
                            <th>题型</th>
                            <th>分值</th>
                            <th>正确率</th>
                            <th>错误人数</th>
                            <th>难度等级</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # 添加题目分析表格
        for q in questions:
            error_rate = q.get('error_rate', 0)
            correct_rate = (1 - error_rate) * 100
            error_count = round(error_rate * q.get('student_count', 0))
            
            # 根据错误率确定难度
            difficulty = "简单"
            if error_rate > 0.7:
                difficulty = "困难"
            elif error_rate > 0.4:
                difficulty = "中等"
                
            html_content += f"""
                        <tr>
                            <td>{q.get('number', '')}</td>
                            <td>{q.get('type', '未知')}</td>
                            <td>{q.get('score', '')}</td>
                            <td>{correct_rate:.1f}%</td>
                            <td>{error_count} / {q.get('student_count', '')}</td>
                            <td>{difficulty}</td>
                        </tr>
            """
            
        html_content += """
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">AI教学分析</div>
        """
        
        # 添加总体评价
        overall = ai_analysis.get('overall', '暂无总体评价')
        html_content += f"""
                <div class="alert alert-info">
                    <strong>总体评价：</strong>
                    <p>{overall}</p>
                </div>
        """
        
        # 添加薄弱知识点
        weak_points = ai_analysis.get('weak_points', [])
        if weak_points:
            html_content += """
                <div class="section-title">薄弱知识点分析</div>
            """
            
            for point in weak_points:
                html_content += f"""
                <div class="alert alert-warning">
                    <strong>{point.get('title', '薄弱点')}</strong>
                    <p>{point.get('description', '')}</p>
                </div>
                """
        
        # 添加教学建议
        suggestions = ai_analysis.get('suggestions', [])
        if suggestions:
            html_content += """
                <div class="section-title">教学建议</div>
            """
            
            for suggestion in suggestions:
                html_content += f"""
                <div class="card">
                    <div class="card-header">{suggestion.get('title', '建议')}</div>
                    <div class="card-body">
                        <p>{suggestion.get('description', '')}</p>
                    </div>
                </div>
                """
        
        # 完成HTML
        html_content += """
            </div>
        </body>
        </html>
        """
        
        # 保存HTML报告
        with open(report_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 返回报告文件
        return send_file(report_file_path, as_attachment=True, attachment_filename=f"{exam['exam_name']}_{subject}_分析报告.html")
    except Exception as e:
        logger.error(f"下载分析报告时出错: {str(e)}")
        return jsonify({"status": "error", "message": f"下载分析报告时出错: {str(e)}"})

# 初始化数据应用
if __name__ == '__main__':
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='ClassMaster 2.0 服务器')
    parser.add_argument('--host', default='0.0.0.0', help='绑定的主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='绑定的端口号 (默认: 8080)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()
    
    # 初始化数据库，只确保表和列存在，不会重置数据
    init_db()
    logger.info("数据库初始化完成，保留已有数据")
    
    # 打印重要配置信息
    print("=============== 健康体检系统服务器 ===============")
    print(f"数据库路径: {os.path.abspath(DATABASE)}")
    print(f"上传文件夹: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"模板文件夹: {os.path.abspath(TEMPLATE_FOLDER)}")
    print(f"服务器地址: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}")
    
    # 设置Flask应用程序
    is_production = os.environ.get('FLASK_ENV') == 'production'
    if is_production:
        # 生产环境设置
        app.run(host=args.host, port=args.port)
    else:
        # 开发环境设置
        app.debug = True if args.debug else False
        app.config['PROPAGATE_EXCEPTIONS'] = True
        app.run(host=args.host, port=args.port, threaded=True)
