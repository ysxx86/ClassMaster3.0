#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试更新用户角色功能
"""

import sqlite3
import json

def test_update_role():
    """测试更新角色"""
    print("=" * 60)
    print("测试更新用户角色功能")
    print("=" * 60)
    
    # 连接数据库
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. 查看当前用户5的角色
    cursor.execute("SELECT id, username, role FROM users WHERE id = 5")
    user = cursor.fetchone()
    print(f"\n当前用户信息:")
    print(f"  ID: {user['id']}")
    print(f"  用户名: {user['username']}")
    print(f"  角色: {user['role']}")
    
    # 2. 更新角色为"副班主任"
    print(f"\n更新角色为: 副班主任")
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", ('副班主任', 5))
    conn.commit()
    
    # 3. 验证更新
    cursor.execute("SELECT id, username, role FROM users WHERE id = 5")
    user = cursor.fetchone()
    print(f"\n更新后用户信息:")
    print(f"  ID: {user['id']}")
    print(f"  用户名: {user['username']}")
    print(f"  角色: {user['role']}")
    
    if user['role'] == '副班主任':
        print("\n✓ 角色更新成功！")
    else:
        print(f"\n✗ 角色更新失败！期望: 副班主任, 实际: {user['role']}")
    
    # 4. 恢复原来的角色
    print(f"\n恢复角色为: 正班主任")
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", ('正班主任', 5))
    conn.commit()
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    test_update_role()
