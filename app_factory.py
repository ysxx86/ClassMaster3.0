from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from datetime import timedelta
from config_manager import config, UPLOAD_FOLDER

def create_app():
    """创建Flask应用"""
    app = Flask(__name__, 
                static_url_path='', 
                static_folder='./',
                template_folder='./')
    
    # 基本配置
    app.config['SECRET_KEY'] = 'your-secret-key'  # 在生产环境中应使用安全的密钥
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # 初始化CORS
    CORS(app)
    
    # 配置登录管理器
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'users.login'
    
    # 注册蓝图
    from students import students_bp
    app.register_blueprint(students_bp)
    
    from dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    return app
