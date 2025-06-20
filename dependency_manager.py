# -*- coding: utf-8 -*-
"""
依赖管理模块
检查和安装项目所需的Python包
"""

import sys
import subprocess

def check_and_install(package, version=None):
    """检查并安装Python包"""
    package_with_version = f"{package}=={version}" if version else package
    
    try:
        __import__(package)
        print(f"✓ {package} 已安装")
        return True
    except ImportError:
        print(f"! 未找到 {package} 模块，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", 
                                  package_with_version, "--no-cache-dir"])
            print(f"✓ {package} 安装成功")
            return True
        except Exception as e:
            print(f"! {package} 安装失败: {str(e)}")
            print(f"  请手动运行: pip install {package_with_version}")
            return False

def install_required_packages():
    """安装所有必需的Python包"""
    print("检查并安装关键依赖...")
    REQUIRED_PACKAGES = [
        ("flask", "3.0.2"),
        ("flask_cors", "3.0.10"),
        ("flask_login", "0.6.3"),  # 添加Flask-Login依赖
        ("pandas", "2.2.1"),
        ("openpyxl", "3.1.2"),
        ("werkzeug", "2.3.0")
    ]

    # 检查基础依赖
    success_count = 0
    for package, version in REQUIRED_PACKAGES:
        if check_and_install(package, version):
            success_count += 1

    # 单独处理可选依赖
    check_optional_dependencies()

    print("依赖检查完成，开始导入模块...\n")
    return success_count == len(REQUIRED_PACKAGES)

def check_optional_dependencies():
    """检查可选依赖"""
    # 检查requests (AI评语功能需要)
    try:
        import requests
        print("✓ requests 已安装")
    except ImportError:
        print("! 未找到 requests 模块，评语AI生成功能将不可用")
        print("  如需使用AI生成评语，请运行: pip install requests==2.31.0")

    # 检查reportlab (PDF导出功能需要)  
    try:
        import reportlab
        print("✓ reportlab 已安装")
    except ImportError:
        print("! 未找到 reportlab 模块，PDF导出功能将不可用")
        print("  如需使用PDF导出功能，请运行: pip install reportlab==4.1.0")

if __name__ == "__main__":
    # 如果直接运行此模块，则执行依赖检查
    install_required_packages()
