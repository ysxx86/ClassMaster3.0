# -*- coding: utf-8 -*-
"""
ClassMaster 3.0 - 智能班级管理系统

server.py - 兼容层入口文件
主入口已迁移到 app.py，此文件仅用于向后兼容

启动方式:
    python server.py
    或
    python app.py
"""

import os
import sys

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入主应用（这会执行 app.py 中的所有初始化代码）
from app import app

# 导出 app 实例供 Gunicorn 等服务器使用
# Gunicorn 命令: gunicorn server:app
application = app
__all__ = ['app', 'application']

if __name__ == '__main__':
    # 直接运行时的入口点
    # 导入主应用的 main 逻辑
    import argparse

    parser = argparse.ArgumentParser(description='ClassMaster 3.0 服务器')
    parser.add_argument('--host', default='0.0.0.0', help='绑定的主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='绑定的端口号 (默认: 8080)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()

    is_production = os.environ.get('FLASK_ENV') == 'production'
    if is_production:
        app.run(host=args.host, port=args.port)
    else:
        app.debug = True if args.debug else False
        app.run(host=args.host, port=args.port, threaded=True)
