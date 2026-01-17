#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色更新功能自动诊断脚本
"""

import os
import subprocess
import sqlite3

def check_files():
    """检查文件是否包含必要的代码"""
    print("\n" + "=" * 60)
    print("1. 检查文件完整性")
    print("=" * 60)
    
    checks = {
        'js/admin.js': ['editUserRole', 'const role ='],
        'pages/admin.html': ['editUserRole', 'id="editUserRole"'],
        'users.py': ['角色更新', "if 'role' in data"]
    }
    
    all_ok = True
    for file, keywords in checks.items():
        if not os.path.exists(file):
            print(f"✗ {file}: 文件不存在")
            all_ok = False
            continue
        
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for keyword in keywords:
            if keyword in content:
                print(f"✓ {file}: 找到 '{keyword}'")
            else:
                print(f"✗ {file}: 未找到 '{keyword}'")
                all_ok = False
    
    return all_ok

def check_database():
    """检查数据库结构和数据"""
    print("\n" + "=" * 60)
    print("2. 检查数据库")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('students.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查role字段是否存在
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'role' in columns:
            print("✓ users表包含role字段")
        else:
            print("✗ users表缺少role字段")
            conn.close()
            return False
        
        # 查看角色分布
        cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
        print("\n角色分布:")
        for row in cursor.fetchall():
            print(f"  {row['role']}: {row['count']}人")
        
        # 查看示例用户
        cursor.execute("SELECT id, username, role FROM users LIMIT 5")
        print("\n示例用户:")
        for row in cursor.fetchall():
            print(f"  ID={row['id']}, 用户名={row['username']}, 角色={row['role']}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ 数据库检查失败: {str(e)}")
        return False

def test_update():
    """测试更新功能"""
    print("\n" + "=" * 60)
    print("3. 测试更新功能")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('students.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 找一个测试用户
        cursor.execute("SELECT id, username, role FROM users WHERE id = 5")
        user = cursor.fetchone()
        
        if not user:
            print("✗ 找不到测试用户 (ID=5)")
            conn.close()
            return False
        
        original_role = user['role']
        print(f"测试用户: ID={user['id']}, 用户名={user['username']}, 当前角色={original_role}")
        
        # 更新为不同的角色
        test_role = '副班主任' if original_role != '副班主任' else '科任老师'
        print(f"尝试更新角色为: {test_role}")
        
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (test_role, 5))
        conn.commit()
        
        # 验证更新
        cursor.execute("SELECT role FROM users WHERE id = 5")
        new_role = cursor.fetchone()['role']
        
        if new_role == test_role:
            print(f"✓ 角色更新成功: {original_role} → {new_role}")
            
            # 恢复原来的角色
            cursor.execute("UPDATE users SET role = ? WHERE id = ?", (original_role, 5))
            conn.commit()
            print(f"✓ 已恢复原角色: {original_role}")
            
            conn.close()
            return True
        else:
            print(f"✗ 角色更新失败: 期望={test_role}, 实际={new_role}")
            conn.close()
            return False
            
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        return False

def check_server_log():
    """检查服务器日志"""
    print("\n" + "=" * 60)
    print("4. 检查服务器日志")
    print("=" * 60)
    
    log_file = 'logs/server.log'
    if not os.path.exists(log_file):
        print(f"✗ 日志文件不存在: {log_file}")
        return False
    
    try:
        # 读取最后50行
        result = subprocess.run(['tail', '-50', log_file], 
                              capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        # 查找role相关的日志
        role_logs = [line for line in lines if 'role' in line.lower() or '角色' in line]
        
        if role_logs:
            print(f"找到 {len(role_logs)} 条角色相关日志:")
            for log in role_logs[-5:]:  # 只显示最后5条
                print(f"  {log}")
        else:
            print("未找到角色相关日志")
        
        return True
        
    except Exception as e:
        print(f"✗ 读取日志失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("角色更新功能自动诊断")
    print("=" * 60)
    
    results = []
    
    # 运行所有检查
    results.append(("文件完整性", check_files()))
    results.append(("数据库结构", check_database()))
    results.append(("更新功能", test_update()))
    results.append(("服务器日志", check_server_log()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("诊断结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 项检查通过")
    print("=" * 60)
    
    if passed == total:
        print("\n✓ 所有检查通过！")
        print("\n如果前端仍然无法更新角色，请尝试：")
        print("1. 按 Ctrl + Shift + R 强制刷新浏览器")
        print("2. 清除浏览器缓存")
        print("3. 使用无痕模式打开")
        print("4. 重启服务器")
    else:
        print("\n✗ 发现问题，请检查失败的项目")
    
    print("\n详细诊断指南请查看: diagnose_role_issue.md")

if __name__ == '__main__':
    main()
