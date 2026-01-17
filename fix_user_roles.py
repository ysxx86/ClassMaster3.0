#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复用户角色 - 将非正班主任的用户角色改为正确的值
"""

import sqlite3

def fix_roles():
    """修复用户角色"""
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("修复用户角色")
    print("=" * 60)
    
    # 根据您之前的测试结果，这些用户应该是副班主任
    vice_teachers = [
        '刘莹莹', '吴鎏颖', '唐兴兰', '康雪白', 
        '张亚闽', '李怡平', '林婕钊', '郭雪娟', '黄楷蓉'
    ]
    
    # 其他角色
    other_roles = {
        '庄建辉': '行政',
        '测试号': '校级领导',
        '肖昆明': '超级管理员'
    }
    
    print("\n1. 将以下用户设置为副班主任:")
    for username in vice_teachers:
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            old_role = row['role']
            cursor.execute('UPDATE users SET role = ? WHERE username = ?', ('副班主任', username))
            print(f"   ✅ {username}: {old_role} → 副班主任")
        else:
            print(f"   ⚠️  未找到用户: {username}")
    
    print("\n2. 设置其他角色:")
    for username, new_role in other_roles.items():
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            old_role = row['role']
            cursor.execute('UPDATE users SET role = ? WHERE username = ?', (new_role, username))
            print(f"   ✅ {username}: {old_role} → {new_role}")
        else:
            print(f"   ⚠️  未找到用户: {username}")
    
    conn.commit()
    
    # 验证修改
    print("\n3. 验证修改结果:")
    cursor.execute('''
        SELECT role, COUNT(*) as count
        FROM users
        WHERE is_admin = 0
        GROUP BY role
    ''')
    
    print("\n   角色分布:")
    for row in cursor.fetchall():
        print(f"   - {row['role']}: {row['count']}人")
    
    # 显示正班主任列表
    print("\n4. 正班主任列表（前10位）:")
    cursor.execute('''
        SELECT u.username, c.class_name
        FROM users u
        LEFT JOIN classes c ON u.class_id = c.id
        WHERE u.role = '正班主任' AND u.is_admin = 0
        ORDER BY c.class_name, u.username
        LIMIT 10
    ''')
    
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"   {i}. {row['username']} ({row['class_name'] or '无班级'})")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 修复完成")
    print("=" * 60)
    print("\n下一步:")
    print("1. 重启服务器: python3 server.py")
    print("2. 清除浏览器缓存: Ctrl+Shift+R")
    print("3. 刷新绩效考核页面")

if __name__ == '__main__':
    # 确认操作
    print("\n⚠️  警告: 此脚本将修改数据库中的用户角色")
    print("\n将要修改:")
    print("- 9位用户 → 副班主任")
    print("- 庄建辉 → 行政")
    print("- 测试号 → 校级领导")
    print("- 肖昆明 → 超级管理员")
    
    confirm = input("\n确认执行? (输入 yes 继续): ")
    
    if confirm.lower() == 'yes':
        fix_roles()
    else:
        print("已取消操作")
