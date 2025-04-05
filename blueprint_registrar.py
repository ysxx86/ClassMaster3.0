from students import students_bp
from comments import comments_bp, init_comments
from deyu import deyu_bp

def register_blueprints(app):
    """注册所有蓝图"""
    app.register_blueprint(students_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(deyu_bp)
    # 只注册下载路由，不创建表
    init_comments(app)
