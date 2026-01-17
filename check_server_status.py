#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查服务器状态和API响应
"""

import requests
import json
import sqlite3

def check_database():
    """检查数据库中的数据"""
    print("=" * 60)
    print("1. 检查数据库")
    print("=" * 60)
    
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查询正班主任
    cursor.execute('''
        SELECT u.id, u.username, c.class_name, u.role, u.is_admin
        FROM users u
        LEFT JOIN classes c ON u.class_id = c.id
        WHERE u.role = '正班主任' AND u.is_admin = 0
        ORDER BY c.class_name, u.username
        LIMIT 10
    ''')
    
    teachers = cursor.fetchall()
    print(f"\n✅ 数据库中的正班主任（前10位）: {len(teachers)}位")
    for i, t in enumerate(teachers, 1):
        print(f"   {i}. {t['username']} ({t['class_name'] or '无班级'})")
    
    # 查询非正班主任
    cursor.execute('''
        SELECT u.username, u.role
        FROM users u
        WHERE u.role != '正班主任' OR u.is_admin = 1
        ORDER BY u.username
        LIMIT 5
    ''')
    
    non_teachers = cursor.fetchall()
    print(f"\n❌ 非正班主任（前5位）: {len(non_teachers)}位")
    for t in non_teachers:
        print(f"   - {t['username']} ({t['role']})")
    
    conn.close()

def check_api():
    """检查API响应"""
    print("\n" + "=" * 60)
    print("2. 检查API响应")
    print("=" * 60)
    
    try:
        # 测试API
        response = requests.get('http://localhost:5000/api/performance/scores/2024-2025-1', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                teachers = data.get('teachers', [])
                print(f"\n✅ API返回的教师数量: {len(teachers)}位")
                
                if len(teachers) > 0:
                    print(f"\n前10位教师:")
                    for i, t in enumerate(teachers[:10], 1):
                        print(f"   {i}. {t['username']} ({t.get('class_name', '无班级')})")
                    
                    # 检查是否有非正班主任
                    print(f"\n检查是否有非正班主任...")
                    non_teachers = ['刘莹莹', '吴鎏颖', '唐兴兰', '庄建辉', 'admin', '肖昆明']
                    found_non_teachers = [t['username'] for t in teachers if t['username'] in non_teachers]
                    
                    if found_non_teachers:
                        print(f"   ❌ 发现非正班主任: {', '.join(found_non_teachers)}")
                        print(f"   ⚠️  API返回了不应该出现的用户！")
                    else:
                        print(f"   ✅ 没有发现非正班主任")
                else:
                    print("   ⚠️  API返回的教师列表为空")
            else:
                print(f"   ❌ API返回错误: {data.get('message', '未知错误')}")
        else:
            print(f"   ❌ API请求失败，状态码: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ 无法连接到服务器")
        print("   提示: 请确保服务器正在运行 (python3 server.py)")
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")

def check_performance_py():
    """检查performance.py文件内容"""
    print("\n" + "=" * 60)
    print("3. 检查performance.py代码")
    print("=" * 60)
    
    try:
        with open('performance.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查关键代码
        if "WHERE u.role = '正班主任' AND u.is_admin = 0" in content:
            print("   ✅ 代码包含正确的过滤条件")
        elif "WHERE u.role = '正班主任'" in content:
            print("   ⚠️  代码只过滤了角色，没有排除管理员")
        else:
            print("   ❌ 代码没有正确的过滤条件")
            
    except Exception as e:
        print(f"   ❌ 读取文件失败: {str(e)}")

def main():
    print("\n" + "=" * 60)
    print("绩效考核系统诊断工具")
    print("=" * 60)
    
    check_database()
    check_api()
    check_performance_py()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)
    
    print("\n如果API返回了非正班主任:")
    print("1. 确认服务器已重启: 停止服务器(Ctrl+C)，然后重新运行 python3 server.py")
    print("2. 清除浏览器缓存: Ctrl+Shift+R (Windows) 或 Cmd+Shift+R (Mac)")
    print("3. 检查服务器日志: tail -50 logs/server.log")
    print("4. 使用无痕模式测试: Ctrl+Shift+N (Chrome) 或 Ctrl+Shift+P (Firefox)")

if __name__ == '__main__':
    main()
