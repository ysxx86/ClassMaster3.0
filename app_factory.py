from flask import Flask
from flask_cors import CORS
from config import UPLOAD_FOLDER

def create_app():
    """创建Flask应用"""
    app = Flask(__name__, 
                static_url_path='', 
                static_folder='./',
                template_folder='./')
    CORS(app)  # 启用跨域资源共享
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    return app
