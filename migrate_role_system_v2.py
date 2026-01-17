#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
角色系统V2.0迁移脚本
- 统一管理员为超级管理员
- 创建任课分配表
- 更新角色定义
"""

import sqlite3
import datetime

def migrate_role_system_v2():
    """迁移到角色系统V2.0"""
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("角色系统V2.0迁移")
    print("=" * 60)
    
    try:
        # 步骤1：检查并重命名role字段为primary_role（如果需要）
        print("\n步骤1：检查字段名称...")
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        if 'role' in columns and 'primary_role' not in columns:
            print("   需要重命名 role → primary_role")
            # SQLite不支持直接重命名列，需要重建表
            cursor.execute('''
                CREATE TABLE users_new (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    primary_role TEXT DEFAULT '科任老师',
                    class_id TEXT,
                    reset_password TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT INTO users_new 
                SELECT id, username, password_hash, is_admin, role, class_id, 
                       reset_password, created_at, updated_at
                FROM users
            ''')
            
            cursor.execute('DROP TABLE users')
            cursor.execute('ALTER TABLE users_new RENAME TO users')
            print("   ✅ 字段已重命名")
        elif 'primary_role' in columns:
            print("   ✅ primary_role 字段已存在")
        else:
            # 添加primary_role字段
            print("   添加 primary_role 字段")
            cursor.execute('ALTER TABLE users ADD COLUMN primary_role TEXT DEFAULT "科任老师"')
            print("   ✅ 字段已添加")
        
        # 步骤2：更新超级管理员角色
        print("\n步骤2：更新超级管理员角色...")
        cursor.execute('''
            UPDATE users 
            SET primary_role = '超级管理员' 
            WHERE is_admin = 1
        ''')
        affected = cursor.rowcount
        print(f"   ✅ 已更新 {affected} 个超级管理员")
        
        # 步骤3：创建任课分配表
        print("\n步骤3：创建任课分配表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teaching_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id TEXT NOT NULL,
                class_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                UNIQUE(teacher_id, class_id, subject)
            )
        ''')
        print("   ✅ teaching_assignments 表已创建")
        
        # 步骤4：验证数据
        print("\n步骤4：验证数据...")
        
        # 4.1 检查角色分布
        cursor.execute('''
            SELECT primary_role, COUNT(*) as count
            FROM users
            GROUP BY primary_role
        ''')
        print("\n   角色分布:")
        for row in cursor.fetchall():
            print(f"   - {row['primary_role']}: {row['count']}人")
        
        # 4.2 检查班级正副班主任
        print("\n   检查班级管理:")
        cursor.execute('''
            SELECT c.class_name, 
                   u1.username as head_teacher,
                   u2.username as vice_teacher
            FROM classes c
            LEFT JOIN users u1 ON c.id = u1.class_id AND u1.primary_role = '正班主任'
            LEFT JOIN users u2 ON c.id = u2.class_id AND u2.primary_role = '副班主任'
            WHERE u1.username IS NOT NULL OR u2.username IS NOT NULL
            ORDER BY c.class_name
            LIMIT 10
        ''')
        
        for row in cursor.fetchall():
            head = row['head_teacher'] or '无'
            vice = row['vice_teacher'] or '无'
            print(f"   - {row['class_name']}: 正班={head}, 副班={vice}")
        
        # 4.3 检查班级唯一性冲突
        print("\n   检查班级唯一性冲突:")
        cursor.execute('''
            SELECT class_id, primary_role, COUNT(*) as count
            FROM users
            WHERE class_id IS NOT NULL 
              AND primary_role IN ('正班主任', '副班主任')
            GROUP BY class_id, primary_role
            HAVING count > 1
        ''')
        
        conflicts = cursor.fetchall()
        if conflicts:
            print("   ⚠️  发现冲突:")
            for row in conflicts:
                print(f"   - 班级 {row['class_id']} 有 {row['count']} 个{row['primary_role']}")
        else:
            print("   ✅ 无冲突")
        
        # 提交更改
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ 迁移完成")
        print("=" * 60)
        
        # 显示摘要
        print("\n摘要:")
        cursor.execute('SELECT COUNT(*) FROM users WHERE primary_role = "超级管理员"')
        admin_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users WHERE primary_role = "正班主任"')
        head_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users WHERE primary_role = "副班主任"')
        vice_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM teaching_assignments')
        teaching_count = cursor.fetchone()[0]
        
        print(f"- 超级管理员: {admin_count}人")
        print(f"- 正班主任: {head_count}人")
        print(f"- 副班主任: {vice_count}人")
        print(f"- 任课分配: {teaching_count}条")
        
        print("\n下一步:")
        print("1. 重启服务器: python3 server.py")
        print("2. 清除浏览器缓存: Ctrl+Shift+R")
        print("3. 测试后台管理功能")
        print("4. 测试绩效考核功能")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    print("\n⚠️  警告: 此脚本将修改数据库结构")
    print("\n将要执行:")
    print("1. 重命名 role → primary_role（如果需要）")
    print("2. 更新超级管理员角色")
    print("3. 创建任课分配表")
    print("4. 验证数据完整性")
    
    confirm = input("\n确认执行? (输入 yes 继续): ")
    
    if confirm.lower() == 'yes':
        migrate_role_system_v2()
    else:
        print("已取消操作")
