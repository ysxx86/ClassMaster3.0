# -*- coding: utf-8 -*-
# 自动安装所需依赖
import sys
import subprocess
import os
import json
import argparse

def check_and_install(package, version=None):
    """检查并安装Python包"""
    package_with_version = f"{package}=={version}" if version else package
    
    try:
        # 尝试导入模块
        __import__(package)
        print(f"✓ {package} 已安装")
    except ImportError:
        print(f"! 未找到 {package} 模块，正在安装...")
        try:
            # 使用系统Python运行pip安装
            subprocess.check_call([sys.executable, "-m", "pip", "install", 
                                  package_with_version, "--no-cache-dir"])
            print(f"✓ {package} 安装成功")
        except Exception as e:
            print(f"! {package} 安装失败: {str(e)}")
            print(f"  请手动运行: pip install {package_with_version}")

# 检查关键依赖
print("检查并安装关键依赖...")
REQUIRED_PACKAGES = [
    ("flask", "3.0.2"),
    ("flask_cors", "3.0.10"),
    ("flask_login", "0.6.3"),  # 添加Flask-Login依赖
    ("pandas", "2.2.1"),
    ("openpyxl", "3.1.2"),
    ("werkzeug", "2.3.0")
]

# 单独处理requests和reportlab
try:
    import requests
    print("✓ requests 已安装")
except ImportError:
    print("! 未找到 requests 模块，评语AI生成功能将不可用")
    print("  如需使用AI生成评语，请运行: pip install requests==2.31.0")

try:
    import reportlab
    print("✓ reportlab 已安装")
except ImportError:
    print("! 未找到 reportlab 模块，PDF导出功能将不可用")
    print("  如需使用PDF导出功能，请运行: pip install reportlab==4.1.0")

# 安装基础依赖
for package, version in REQUIRED_PACKAGES:
    check_and_install(package, version)

print("依赖检查完成，开始导入模块...\n")

# 原始的导入语句
from flask import Flask, request, jsonify, send_from_directory, render_template, url_for, send_file, make_response, redirect, flash
from flask_cors import CORS
# 导入Flask-Login相关模块
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
from utils.excel_processor import ExcelProcessor
try:
    from utils.pdf_exporter_fixed import export_comments_to_pdf  # 导入修复后的PDF导出函数
except ImportError:
    # 创建一个简化版的PDF导出函数，返回格式与正常函数一致
    def export_comments_to_pdf(*args, **kwargs):
        return {
            'status': 'error',
            'message': 'PDF导出功能不可用，请安装reportlab模块'
        }
    print("! PDF导出功能不可用，请安装reportlab模块")
    
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

# 导入用户模块
from users import users_bp, init_users

# 导入班级模块
from classes import classes_bp, init_classes

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

# 系统设置存储
SYSTEM_SETTINGS = {
    "deepseek_api_key": DEEPSEEK_API_KEY,
    "deepseek_api_enabled": bool(DEEPSEEK_API_KEY)
}

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/root_server.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("服务器启动")

# 创建Flask应用，指定静态文件夹
app = Flask(__name__, 
            static_url_path='', 
            static_folder='./',
            template_folder='templates')
CORS(app)  # 启用跨域资源共享

# 设置密钥（用于会话安全）
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")
app.config['JSON_AS_ASCII'] = False  # 确保JSON响应支持中文
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # 关闭JSON格式化
app.config['TRAP_HTTP_EXCEPTIONS'] = True  # 捕获HTTP异常

# 初始化Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'users.login'  # 设置登录视图

# 用户加载函数
@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.get_by_id(user_id)

# 将deepseek_api添加到应用配置中
app.config['deepseek_api'] = deepseek_api

# 注册学生蓝图
app.register_blueprint(students_bp)

# 注册评语蓝图
app.register_blueprint(comments_bp)

# 注册成绩蓝图
app.register_blueprint(grades_bp)

# 注册德育蓝图
app.register_blueprint(deyu_bp)

# 注册用户蓝图
app.register_blueprint(users_bp)

# 注册班级蓝图
app.register_blueprint(classes_bp)

# 初始化评语模块
init_comments(app)

# 初始化成绩模块
init_grades(app)

# 初始化德育模块
init_deyu(app)

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

# 配置
UPLOAD_FOLDER = 'uploads'
TEMPLATE_FOLDER = 'templates'
EXPORTS_FOLDER = 'exports'
DATABASE = 'students.db'

# 将UPLOAD_FOLDER添加到app.config中
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保所有必要的文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)
os.makedirs(EXPORTS_FOLDER, exist_ok=True)

# 创建数据库连接
def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

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
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': '服务器正常运行中'})

# API获取当前登录用户信息
@app.route('/api/current-user', methods=['GET'])
@login_required
def get_current_user():
    """获取当前用户信息"""
    try:
        # 使用直接的SQL查询获取用户及其班级信息
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 记录当前用户基本信息，便于调试
        logger.info(f"当前用户ID: {current_user.id}, 用户名: {current_user.username}, 班级ID: {current_user.class_id}")
        
        # 先获取用户信息
        cursor.execute('SELECT id, username, is_admin, class_id FROM users WHERE id = ?', (current_user.id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            logger.warning(f"未找到用户ID: {current_user.id}")
            conn.close()
            return jsonify({'status': 'error', 'message': '找不到用户信息'}), 404
        
        # 初始化班级名称为"暂无班级"
        class_name = "暂无班级"
        class_id = user_data['class_id']
        
        # 如果用户有班级ID，直接查询班级名称
        if class_id:
            # 将class_id转换为整数进行查询
            try:
                numeric_class_id = int(class_id)
                logger.info(f"用户有班级ID: {class_id} (已转换为整数: {numeric_class_id}), 查询班级名称")
                
                # 使用参数化查询防止SQL注入
                cursor.execute('SELECT class_name FROM classes WHERE id = ?', (numeric_class_id,))
                class_data = cursor.fetchone()
                
                if class_data and class_data['class_name']:
                    class_name = class_data['class_name']
                    logger.info(f"找到班级名称: {class_name}")
                else:
                    logger.warning(f"未找到班级ID {class_id} 对应的班级名称")
                    
                    # 额外查询所有班级，用于调试
                    cursor.execute('SELECT id, class_name FROM classes')
                    all_classes = [dict(c) for c in cursor.fetchall()]
                    logger.info(f"所有班级: {all_classes}")
                    
                    # 尝试使用字符串比较查找
                    for cls in all_classes:
                        if str(cls['id']) == str(class_id):
                            class_name = cls['class_name']
                            logger.info(f"通过字符串比较找到班级: ID={cls['id']}, 名称={class_name}")
                            break
            except (ValueError, TypeError):
                logger.error(f"无法将班级ID转换为整数: {class_id}")
        else:
            logger.info("用户没有班级ID，显示'暂无班级'")
        
        conn.close()
        
        # 构建用户信息
        user_info = {
            'id': user_data['id'],
            'username': user_data['username'],
            'is_admin': bool(user_data['is_admin']),
            'class_id': class_id,
            'class_name': class_name,
            'role': "admin" if bool(user_data['is_admin']) else "teacher"
        }
        
        logger.info(f"返回用户信息: user={user_info['username']}, class_id={user_info['class_id']}, class_name={user_info['class_name']}")
        logger.info(f"用户信息JSON: {json.dumps(user_info, ensure_ascii=False)}")
        
        return jsonify({
            'status': 'ok',
            'user': user_info
        })
        
    except Exception as e:
        logger.error(f"获取当前用户信息时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'获取当前用户信息失败: {str(e)}'}), 500

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

# 获取数据库信息API
@app.route('/api/database-info', methods=['GET'])
def database_info():
    try:
        # 获取数据库文件路径
        db_path = os.path.abspath(DATABASE)
        
        # 获取文件修改时间
        if os.path.exists(db_path):
            last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(db_path)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_modified = '数据库文件不存在'
        
        # 获取学生数量
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM students')
        student_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'path': db_path,
            'last_modified': last_modified,
            'student_count': student_count
        })
    except Exception as e:
        print(f"获取数据库信息时出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'获取数据库信息时出错: {str(e)}'
        }), 500

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

# 提供导出文件下载 - 已移至comments.py init_comments函数中
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
    try:
        data = request.get_json()
        api_key = data.get('apiKey', '')
        
        if not api_key:
            return jsonify({'status': 'error', 'message': 'API密钥不能为空'})
            
        # 创建临时API对象
        from utils.deepseek_api import DeepSeekAPI
        api = DeepSeekAPI(api_key)
        result = api.test_connection()
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"测试DeepSeek API时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'测试API出错: {str(e)}'})

# 保存DeepSeek API设置
@app.route('/api/settings/deepseek', methods=['POST'])
@login_required
def save_deepseek_api_settings():
    global deepseek_api
    
    try:
        data = request.get_json()
        api_key = data.get('apiKey', '')
        
        # 可以添加验证API密钥格式的代码
        # 此处省略验证逻辑
        
        # 更新全局变量
        SYSTEM_SETTINGS['deepseek_api_key'] = api_key
        SYSTEM_SETTINGS['deepseek_api_enabled'] = bool(api_key)
        
        # 更新API对象
        if deepseek_api:
            deepseek_api.update_api_key(api_key)
        else:
            from utils.deepseek_api import DeepSeekAPI
            deepseek_api = DeepSeekAPI(api_key)
            
        # 更新应用配置
        current_app.config['deepseek_api'] = deepseek_api
            
        return jsonify({
            'status': 'ok', 
            'message': 'API设置已更新',
            'api_enabled': bool(api_key)
        })
    except Exception as e:
        logger.error(f"保存DeepSeek API设置时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'保存设置出错: {str(e)}'})

# 获取系统设置
@app.route('/api/settings', methods=['GET'])
@login_required
def get_system_settings():
    # 添加用户权限检查，只有管理员可以获取完整的系统设置
    if not current_user.is_admin:
        # 非管理员用户，只返回有限的设置信息
        filtered_settings = {
            'system_name': SYSTEM_SETTINGS.get('system_name', '班主任管理系统'),
            'school_name': SYSTEM_SETTINGS.get('school_name', '泉州东海湾实验学校')
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
        app.run(host=args.host, port=args.port)
