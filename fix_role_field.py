#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复角色字段问题
- 将旧的role字段数据迁移到primary_role
- 删除旧的role字段
"""

import sqlite3
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE = 'students.db'

def fix_role_field():
    """修复角色字段"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # 1. 检查表结构
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        logger.info(f"当前users表的列: {column_names}")
        
        has_role = 'role' in column_names
        has_primary_role = 'primary_role' in column_names
        
        if not has_role and not has_primary_role:
            logger.error("users表中既没有role字段也没有primary_role字段！")
            return False
        
        # 2. 如果只有role字段，重命名为primary_role
        if has_role and not has_primary_role:
            logger.info("只有role字段，将其重命名为primary_role")
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
            INSERT INTO users_new (id, username, password_hash, is_admin, primary_role, class_id, reset_password, created_at, updated_at)
            SELECT id, username, password_hash, is_admin, role, class_id, reset_password, created_at, updated_at
            FROM users
            ''')
            
            cursor.execute('DROP TABLE users')
            cursor.execute('ALTER TABLE users_new RENAME TO users')
            
            logger.info("✅ 成功将role字段重命名为primary_role")
        
        # 3. 如果两个字段都存在，将role的数据复制到primary_role，然后删除role
        elif has_role and has_primary_role:
            logger.info("同时存在role和primary_role字段")
            
            # 先将role字段的非空数据复制到primary_role
            cursor.execute('''
            UPDATE users 
            SET primary_role = role 
            WHERE role IS NOT NULL AND role != '' AND (primary_role IS NULL OR primary_role = '')
            ''')
            updated_count = cursor.rowcount
            logger.info(f"从role复制到primary_role的记录数: {updated_count}")
            
            # 重建表以删除role字段
            logger.info("重建表以删除旧的role字段")
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
            INSERT INTO users_new (id, username, password_hash, is_admin, primary_role, class_id, reset_password, created_at, updated_at)
            SELECT id, username, password_hash, is_admin, primary_role, class_id, reset_password, created_at, updated_at
            FROM users
            ''')
            
            cursor.execute('DROP TABLE users')
            cursor.execute('ALTER TABLE users_new RENAME TO users')
            
            logger.info("✅ 成功删除旧的role字段")
        
        # 4. 如果只有primary_role字段，不需要做任何事
        elif not has_role and has_primary_role:
            logger.info("✅ 只有primary_role字段，无需修复")
        
        # 5. 确保所有用户都有primary_role值
        cursor.execute('''
        UPDATE users 
        SET primary_role = '科任老师' 
        WHERE primary_role IS NULL OR primary_role = ''
        ''')
        default_count = cursor.rowcount
        if default_count > 0:
            logger.info(f"为{default_count}个用户设置了默认角色'科任老师'")
        
        # 6. 提交更改
        conn.commit()
        
        # 7. 验证结果
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        logger.info(f"修复后users表的列: {column_names}")
        
        # 8. 显示角色统计
        cursor.execute('SELECT primary_role, COUNT(*) as count FROM users GROUP BY primary_role')
        role_stats = cursor.fetchall()
        logger.info("角色统计:")
        for role, count in role_stats:
            logger.info(f"  {role}: {count}人")
        
        conn.close()
        
        logger.info("=" * 50)
        logger.info("✅ 角色字段修复完成！")
        logger.info("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"修复角色字段时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    print("开始修复角色字段...")
    print("=" * 50)
    
    success = fix_role_field()
    
    if success:
        print("\n✅ 修复成功！")
        print("\n请重启服务器以使更改生效：")
        print("  pkill -f 'python.*server.py'")
        print("  python3 server.py")
    else:
        print("\n❌ 修复失败，请查看日志")
