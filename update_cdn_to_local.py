#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新CDN链接为本地文件路径
"""

import os
import re
import glob

# 定义替换规则
replacements = {
    # Bootstrap
    r'https://cdn\.jsdelivr\.net/npm/bootstrap@5\.3\.0-alpha1/dist/css/bootstrap\.min\.css': '/css/bootstrap.min.css',
    r'https://cdn\.jsdelivr\.net/npm/bootstrap@5\.1\.3/dist/css/bootstrap\.min\.css': '/css/bootstrap.min.css',
    r'https://cdn\.jsdelivr\.net/npm/bootstrap@5\.3\.0-alpha1/dist/js/bootstrap\.bundle\.min\.js': '/js/libs/bootstrap.bundle.min.js',
    r'https://cdn\.jsdelivr\.net/npm/bootstrap@5\.1\.3/dist/js/bootstrap\.bundle\.min\.js': '/js/libs/bootstrap.bundle.min.js',
    
    # Boxicons
    r'https://cdn\.jsdelivr\.net/npm/boxicons@latest/css/boxicons\.min\.css': '/css/boxicons-local.css',
    
    # Chart.js
    r'https://cdn\.jsdelivr\.net/npm/chart\.js': '/js/libs/chart.js',
    
    # jQuery
    r'https://cdn\.jsdelivr\.net/npm/jquery@3\.6\.0/dist/jquery\.min\.js': '/js/libs/jquery.min.js',
    
    # 文档处理库
    r'https://cdnjs\.cloudflare\.com/ajax/libs/pizzip/3\.1\.4/pizzip\.min\.js': '/libs/pizzip.min.js',
    r'https://cdnjs\.cloudflare\.com/ajax/libs/docxtemplater/3\.37\.11/docxtemplater\.js': '/libs/docxtemplater.js',
    r'https://cdnjs\.cloudflare\.com/ajax/libs/jszip/3\.10\.1/jszip\.min\.js': '/libs/jszip.min.js',
}

# 替换JavaScript中的CDN链接
js_replacements = {
    r'https://cdnjs\.cloudflare\.com/ajax/libs/pizzip/3\.1\.4/pizzip\.min\.js': '/libs/pizzip.min.js',
    r'https://cdnjs\.cloudflare\.com/ajax/libs/docxtemplater/3\.37\.11/docxtemplater\.js': '/libs/docxtemplater.js',
}

def replace_in_file(file_path):
    """替换文件中的CDN链接"""
    print(f"处理文件: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        original_content = content
        
        # 根据文件类型选择替换规则
        if file_path.endswith('.js'):
            for pattern, replacement in js_replacements.items():
                content = re.sub(pattern, replacement, content)
        else:
            for pattern, replacement in replacements.items():
                content = re.sub(pattern, replacement, content)
        
        # 如果内容有变更，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            print(f"  已更新 {file_path}")
        else:
            print(f"  无需更新 {file_path}")
            
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")

def main():
    """主函数"""
    print("开始将CDN链接替换为本地路径...")
    
    # 处理HTML文件
    html_files = []
    html_files.extend(glob.glob("*.html"))
    html_files.extend(glob.glob("pages/*.html"))
    html_files.extend(glob.glob("templates/*.html"))
    html_files.extend(glob.glob("templates/pages/*.html"))
    
    for html_file in html_files:
        replace_in_file(html_file)
    
    # 处理JavaScript文件中的CDN引用
    js_files = []
    js_files.extend(glob.glob("js/*.js"))
    js_files.extend(glob.glob("static/js/*.js"))
    
    for js_file in js_files:
        replace_in_file(js_file)
        
    print("CDN链接替换完成！")

if __name__ == "__main__":
    main() 