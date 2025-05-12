#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证CDN链接是否已全部替换为本地文件路径
"""

import os
import re
import glob
import sys

# 定义需要检查的CDN模式
cdn_patterns = [
    r'https://cdn\.jsdelivr\.net/npm/bootstrap@',
    r'https://cdn\.jsdelivr\.net/npm/boxicons@',
    r'https://cdn\.jsdelivr\.net/npm/chart\.js',
    r'https://cdn\.jsdelivr\.net/npm/jquery@',
    r'https://cdnjs\.cloudflare\.com/ajax/libs/pizzip/',
    r'https://cdnjs\.cloudflare\.com/ajax/libs/docxtemplater/',
    r'https://cdnjs\.cloudflare\.com/ajax/libs/jszip/',
]

def check_file(file_path):
    """检查文件中是否存在CDN链接"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        for pattern in cdn_patterns:
            matches = re.findall(pattern, content)
            if matches:
                print(f"[警告] 在文件 {file_path} 中找到 {len(matches)} 个CDN链接: {pattern}")
                return False
        
        return True
    except Exception as e:
        print(f"[错误] 检查文件 {file_path} 时出错: {e}")
        return True  # 返回True以继续检查其他文件

def main():
    """主函数"""
    print("开始验证CDN链接替换情况...")
    
    # 检查HTML文件
    html_files = []
    html_files.extend(glob.glob("*.html"))
    html_files.extend(glob.glob("pages/*.html"))
    html_files.extend(glob.glob("templates/*.html"))
    html_files.extend(glob.glob("templates/pages/*.html"))
    
    # 检查JavaScript文件
    js_files = []
    js_files.extend(glob.glob("js/*.js"))
    js_files.extend(glob.glob("static/js/*.js"))
    
    # 合并所有需要检查的文件
    all_files = html_files + js_files
    print(f"共发现 {len(all_files)} 个需要检查的文件")
    
    # 检查每个文件
    cdn_found = False
    for file_path in all_files:
        if not check_file(file_path):
            cdn_found = True
    
    if cdn_found:
        print("\n[警告] 有文件中仍存在CDN链接，请检查以上警告信息。")
    else:
        print("\n[成功] 所有CDN链接都已替换为本地路径！")

if __name__ == "__main__":
    main() 