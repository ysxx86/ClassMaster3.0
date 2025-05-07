#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
import requests

# DeepSeek API密钥
API_KEY = "sk-04f7d75638d044ed8a707d7aadf46782"

# 数据库路径
DATABASE = 'students.db'

# 尝试通过API设置
def set_via_api():
    print("正在通过API设置DeepSeek API密钥...")
    try:
        response = requests.post(
            "http://localhost:8080/api/settings/deepseek",
            json={"api_key": API_KEY},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "ok":
                print("✓ API设置成功")
                return True
            else:
                print(f"✗ API设置失败: {result.get('message', '未知错误')}")
        else:
            print(f"✗ API请求失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"✗ API请求异常: {str(e)}")
    
    return False

# 尝试修改utils/deepseek_api.py文件
def update_deepseek_api_file():
    print("正在更新DeepSeek API文件...")
    api_file = "utils/deepseek_api.py"
    
    if not os.path.exists(api_file):
        print(f"✗ 文件不存在: {api_file}")
        return False
    
    try:
        with open(api_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 替换默认API密钥
        if "default_api_key =" in content:
            new_content = content.replace(
                'default_api_key = "sk-04f7d75638d044ed8a707d7aadf46782"', 
                f'default_api_key = "{API_KEY}"'
            )
            
            with open(api_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            print(f"✓ 已更新 {api_file} 中的默认API密钥")
            return True
        else:
            print(f"✗ 无法在 {api_file} 中找到默认API密钥行")
    except Exception as e:
        print(f"✗ 更新文件时出错: {str(e)}")
    
    return False

# 方法3: 设置环境变量
def set_env_variable():
    print("正在设置环境变量...")
    try:
        os.environ["DEEPSEEK_API_KEY"] = API_KEY
        print("✓ 已设置环境变量 DEEPSEEK_API_KEY (注意: 这只在当前进程有效)")
        return True
    except Exception as e:
        print(f"✗ 设置环境变量失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("===== DeepSeek API密钥设置工具 =====")
    print(f"API密钥: {API_KEY}")
    print("正在尝试多种方式设置API密钥...\n")
    
    # 尝试所有方法
    api_success = set_via_api()
    file_success = update_deepseek_api_file()
    env_success = set_env_variable()
    
    print("\n===== 设置结果 =====")
    print(f"API设置: {'成功' if api_success else '失败'}")
    print(f"文件更新: {'成功' if file_success else '失败'}")
    print(f"环境变量: {'成功' if env_success else '失败'}")
    
    if api_success or file_success or env_success:
        print("\n✓ API密钥已通过至少一种方式设置成功")
        print("请重启服务器以使更改生效")
    else:
        print("\n✗ 所有设置方法均失败") 