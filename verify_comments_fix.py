#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证评语管理修复脚本
检查所有必要的文件和配置是否正确
"""

import os
import sys

def check_file_exists(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}不存在: {filepath}")
        return False

def check_file_content(filepath, search_text, description):
    """检查文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if search_text in content:
                print(f"✅ {description}")
                return True
            else:
                print(f"❌ {description}未找到")
                return False
    except Exception as e:
        print(f"❌ 读取文件失败 {filepath}: {e}")
        return False

def main():
    print("=" * 60)
    print("评语管理修复验证")
    print("=" * 60)
    print()
    
    all_checks_passed = True
    
    # 检查1: 核心文件存在
    print("📁 检查核心文件...")
    files_to_check = [
        ('js/comments.js', '评语管理JS文件'),
        ('js/performance-optimizer.js', '性能优化工具'),
        ('js/realtime-sync.js', '实时同步系统'),
        ('realtime_api.py', '实时更新API'),
        ('server.py', '服务器主文件'),
    ]
    
    for filepath, desc in files_to_check:
        if not check_file_exists(filepath, desc):
            all_checks_passed = False
    
    print()
    
    # 检查2: comments.js中dataService依赖已移除
    print("🔍 检查dataService依赖...")
    checks = [
        ('js/comments.js', '// const exportSettings = dataService.getExportSettings();', 
         'exportSettings依赖已注释'),
        ('js/comments.js', '// const comment = dataService.getCommentByStudentId(studentId);',
         'getCommentByStudentId依赖已注释'),
    ]
    
    for filepath, search_text, desc in checks:
        if not check_file_content(filepath, search_text, desc):
            all_checks_passed = False
    
    print()
    
    # 检查3: server.py中实时更新API已注册
    print("🔌 检查实时更新API注册...")
    if not check_file_content('server.py', 'from realtime_api import realtime_bp', 
                              '实时更新API已导入'):
        all_checks_passed = False
    if not check_file_content('server.py', 'app.register_blueprint(realtime_bp)', 
                              '实时更新蓝图已注册'):
        all_checks_passed = False
    
    print()
    
    # 检查4: 优化文件存在
    print("📄 检查文档文件...")
    docs = [
        '评语加载问题已修复.md',
        '启动优化系统.md',
        '性能优化完成总结.md',
    ]
    
    for doc in docs:
        if not check_file_exists(doc, f'文档: {doc}'):
            all_checks_passed = False
    
    print()
    print("=" * 60)
    
    if all_checks_passed:
        print("✅ 所有检查通过!")
        print()
        print("📋 下一步操作:")
        print("1. 强制刷新浏览器: Ctrl+Shift+R (Windows/Linux) 或 Cmd+Shift+R (Mac)")
        print("2. 打开评语管理页面")
        print("3. 检查评语卡片是否正常显示")
        print()
        print("如果还有问题:")
        print("- 按F12打开浏览器控制台查看错误")
        print("- 检查Network标签的API请求")
        print("- 重启服务器: python server.py")
    else:
        print("❌ 部分检查未通过,请检查上述错误")
        print()
        print("建议:")
        print("- 确保所有文件都已正确修改")
        print("- 检查文件编码是否为UTF-8")
        print("- 重新运行修复脚本")
    
    print("=" * 60)
    
    return 0 if all_checks_passed else 1

if __name__ == '__main__':
    sys.exit(main())
