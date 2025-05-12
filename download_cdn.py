#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下载CDN资源到本地
使用方法: python download_cdn.py <cdn_url> <local_path>
例如: python download_cdn.py https://cdn.jsdelivr.net/npm/chart.js js/libs/chart.js
"""

import os
import sys
import requests
from urllib.parse import urlparse

def ensure_dir(file_path):
    """确保目录存在"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def download_file(url, local_path):
    """下载文件到本地"""
    print(f"正在下载 {url} 到 {local_path}...")
    
    try:
        # 确保目录存在
        ensure_dir(local_path)
        
        # 下载文件
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # 保存文件
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"下载完成，文件保存在 {local_path}")
        return True
    except Exception as e:
        print(f"下载失败: {e}")
        return False

def get_filename_from_url(url):
    """从URL中提取文件名"""
    parsed_url = urlparse(url)
    path = parsed_url.path
    return os.path.basename(path)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python download_cdn.py <cdn_url> [local_path]")
        print("如果不指定本地路径，将根据URL和文件类型自动确定")
        sys.exit(1)
        
    url = sys.argv[1]
    
    # 如果未指定本地路径，使用自动路径
    if len(sys.argv) < 3:
        filename = get_filename_from_url(url)
        if filename.endswith('.js'):
            if 'bootstrap' in url:
                local_path = f"js/libs/{filename}"
            else:
                local_path = f"libs/{filename}"
        elif filename.endswith('.css'):
            local_path = f"css/{filename}"
        else:
            local_path = filename
    else:
        local_path = sys.argv[2]
    
    # 下载文件
    success = download_file(url, local_path)
    
    # 提示用户如何更新代码
    if success:
        print("\n将以下行添加到您的HTML或JS文件中:")
        if local_path.endswith('.js'):
            print(f'<script src="/{local_path}"></script>')
        elif local_path.endswith('.css'):
            print(f'<link href="/{local_path}" rel="stylesheet">')
        
        print("\n别忘了使用update_cdn_to_local.py脚本替换所有CDN引用!")

if __name__ == "__main__":
    main() 