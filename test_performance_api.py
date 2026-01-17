#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试绩效考核API - 验证只返回正班主任
"""

import sqlite3

def test_performance_query():
    """测试绩效考核查询"""
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("测试绩效考核API - 只显示正班主任")
    print("=" * 60)
    
    # 1. 查看所有用户的角色分布
    print("\n1. 用户角色分布:")
    cursor.execute('''
        SELECT primary_role, COUNT(*) as count
        FROM users
        WHERE is_admin = 0
        GROUP BY primary_role
    ''')
    for row in cursor.fetchall():
        print(f"   {row['primary_role']}: {row['count']}人")
    
    # 2. 查询正班主任（这是API使用的查询 - 排除管理员）
    print("\n2. 正班主任列表（API返回的数据 - 排除管理员）:")
    cursor.execute('''
        SELECT u.id, u.username, c.class_name, u.primary_role
        FROM users u
        LEFT JOIN classes c ON u.class_id = c.id
        WHERE u.primary_role = '正班主任' AND u.is_admin = 0
        ORDER BY c.class_name, u.username
    ''')
    
    teachers = cursor.fetchall()
    print(f"   共 {len(teachers)} 位正班主任:")
    for i, row in enumerate(teachers, 1):
        class_info = row['class_name'] if row['class_name'] else '无班级'
        print(f"   {i}. {row['username']} ({class_info}) - 角色: {row['primary_role']}")
    
    # 3. 查询非正班主任（不应该出现在考核页面）
    print("\n3. 非正班主任用户（不应出现在考核页面）:")
    cursor.execute('''
        SELECT u.id, u.username, u.primary_role
        FROM users u
        WHERE (u.primary_role != '正班主任' OR u.is_admin = 1)
        ORDER BY u.primary_role, u.username
    ''')
    
    non_teachers = cursor.fetchall()
    if non_teachers:
        print(f"   共 {len(non_teachers)} 位非正班主任:")
        for row in non_teachers:
            print(f"   - {row['username']} (角色: {row['primary_role']})")
    else:
        print("   无非正班主任用户")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    print("\n结论:")
    print(f"- 绩效考核页面应该只显示 {len(teachers)} 位正班主任")
    print(f"- 不应该显示 {len(non_teachers)} 位其他角色的用户（包括管理员）")
    print("\n如果页面显示了其他角色的用户，请:")
    print("1. 清除浏览器缓存 (Ctrl+Shift+R 或 Cmd+Shift+R)")
    print("2. 重启服务器")
    print("3. 检查前端JavaScript是否正确调用了API")
    print("\n验证方法:")
    print("- 打开浏览器开发者工具 (F12)")
    print("- 切换到Network标签")
    print("- 刷新绩效考核页面")
    print("- 查看 /api/performance/scores/ 请求的响应")
    print(f"- 应该只返回 {len(teachers)} 位教师")

if __name__ == '__main__':
    test_performance_query()
