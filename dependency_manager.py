import sys
import subprocess

def check_and_install(package, version=None):
    """检查并安装Python包"""
    package_with_version = f"{package}=={version}" if version else package
    
    try:
        __import__(package)
        print(f"✓ {package} 已安装")
    except ImportError:
        print(f"! 未找到 {package} 模块，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", 
                                  package_with_version, "--no-cache-dir"])
            print(f"✓ {package} 安装成功")
        except Exception as e:
            print(f"! {package} 安装失败: {str(e)}")
            print(f"  请手动运行: pip install {package_with_version}")

def install_required_packages():
    """安装所有必需的Python包"""
    print("检查并安装关键依赖...")
    REQUIRED_PACKAGES = [
        ("flask", "3.0.2"),
        ("flask_cors", "3.0.10"),
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
