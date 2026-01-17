#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证性能优化是否正确安装
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
        print(f"❌ 检查{description}时出错: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 性能优化验证工具")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # 1. 检查前端优化文件
    print("📦 检查前端优化文件...")
    all_passed &= check_file_exists('js/performance-optimizer.js', '性能优化工具')
    all_passed &= check_file_exists('js/realtime-sync.js', '实时同步系统')
    all_passed &= check_file_exists('test_performance.html', '性能测试页面')
    print()
    
    # 2. 检查后端优化文件
    print("🔧 检查后端优化文件...")
    all_passed &= check_file_exists('realtime_api.py', '实时更新API')
    all_passed &= check_file_exists('optimize_database.py', '数据库优化脚本')
    print()
    
    # 3. 检查index.html是否引入了优化脚本
    print("📄 检查index.html配置...")
    all_passed &= check_file_content(
        'index.html',
        'js/performance-optimizer.js',
        'index.html已引入性能优化工具'
    )
    all_passed &= check_file_content(
        'index.html',
        'js/realtime-sync.js',
        'index.html已引入实时同步系统'
    )
    all_passed &= check_file_content(
        'index.html',
        'data-src=',
        'index.html已启用iframe懒加载'
    )
    print()
    
    # 4. 检查server.py是否注册了实时更新API
    print("🚀 检查server.py配置...")
    all_passed &= check_file_content(
        'server.py',
        'from realtime_api import realtime_bp',
        'server.py已导入实时更新模块'
    )
    all_passed &= check_file_content(
        'server.py',
        'app.register_blueprint(realtime_bp)',
        'server.py已注册实时更新蓝图'
    )
    all_passed &= check_file_content(
        'server.py',
        'init_realtime(app)',
        'server.py已初始化实时更新'
    )
    print()
    
    # 5. 检查数据库索引
    print("💾 检查数据库优化...")
    if os.path.exists('students.db'):
        import sqlite3
        try:
            conn = sqlite3.connect('students.db')
            cursor = conn.cursor()
            
            # 检查索引
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            required_indexes = [
                'idx_students_class_id',
                'idx_students_id',
                'idx_students_updated_at',
                'idx_users_username',
                'idx_users_class_id',
                'idx_classes_class_name'
            ]
            
            for idx in required_indexes:
                if idx in indexes:
                    print(f"✅ 数据库索引存在: {idx}")
                else:
                    print(f"⚠️  数据库索引缺失: {idx}")
                    all_passed = False
            
            conn.close()
        except Exception as e:
            print(f"❌ 检查数据库索引时出错: {e}")
            all_passed = False
    else:
        print("⚠️  数据库文件不存在: students.db")
    print()
    
    # 6. 检查文档
    print("📚 检查文档...")
    check_file_exists('性能优化实施指南.md', '实施指南')
    check_file_exists('快速集成实时更新.md', '集成指南')
    check_file_exists('性能优化完成总结.md', '完成总结')
    check_file_exists('启动优化系统.md', '启动指南')
    print()
    
    # 总结
    print("=" * 60)
    if all_passed:
        print("🎉 所有检查通过! 性能优化已正确安装!")
        print()
        print("📋 下一步:")
        print("1. 重启服务器: python server.py")
        print("2. 访问测试页面: http://localhost:8080/test_performance.html")
        print("3. 查看文档: 启动优化系统.md")
    else:
        print("⚠️  部分检查未通过,请查看上面的错误信息")
        print()
        print("💡 建议:")
        print("1. 确保所有文件都已创建")
        print("2. 运行: python optimize_database.py")
        print("3. 检查server.py是否正确修改")
    print("=" * 60)

if __name__ == '__main__':
    main()
