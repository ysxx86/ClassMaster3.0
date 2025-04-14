#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
登录并测试班级API
"""

import requests
import json

# 服务器URL
SERVER_URL = 'http://localhost:8080'

# 会话
session = requests.Session()

def login(username, password):
    """登录系统"""
    login_url = f"{SERVER_URL}/login"
    login_data = {
        "username": username,
        "password": password
    }
    
    response = session.post(login_url, data=login_data, allow_redirects=True)
    print(f"登录状态码: {response.status_code}")
    print(f"登录响应: {response.text[:100]}...")  # 只打印前100个字符
    
    return response.status_code == 200

def test_classes_api():
    """测试班级API"""
    classes_url = f"{SERVER_URL}/api/classes"
    
    response = session.get(classes_url)
    print(f"班级API状态码: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"API响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            print(f"非JSON响应: {response.text[:200]}...")  # 只打印前200个字符
    
    return response

if __name__ == "__main__":
    # 使用默认的管理员账户
    username = "admin"
    password = "admin"
    
    if login(username, password):
        print("登录成功，测试班级API...")
        test_classes_api()
    else:
        print("登录失败，无法测试API") 