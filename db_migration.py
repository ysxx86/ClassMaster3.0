#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 将当前数据模型升级到三表关系模型
包括：创建班级表，修改学生表和用户表以引用班级ID
"""

import os
import sqlite3
import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库路径
DATABASE = 'students.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

def backup_database():
    """备份当前数据库"""
    backup_name = f"students_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        if os.path.exists(DATABASE):
            import shutil
            shutil.copy2(DATABASE, backup_name)
            logger.info(f"已创建数据库备份: {backup_name}")
            return True
        else:
            logger.warning(f"数据库文件不存在，无法备份")
            return False
    except Exception as e:
        logger.error(f"备份数据库失败: {e}")
        return False

def create_classes_table(conn):
    """创建班级表"""
    cursor = conn.cursor()
    
    # 获取现有的不同班级列表
    cursor.execute("SELECT DISTINCT class FROM students WHERE class IS NOT NULL AND class != ''")
    existing_classes = [row['class'] for row in cursor.fetchall()]
    
    # 创建班级表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_name TEXT NOT NULL,
        grade TEXT,
        school_year TEXT,
        description TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    
    # 插入现有的班级
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for class_name in existing_classes:
        # 尝试提取年级信息
        grade = None
        if '年级' in class_name:
            parts = class_name.split('年级')
            if len(parts) > 0:
                grade = parts[0] + '年级'
        
        cursor.execute('''
        INSERT INTO classes (class_name, grade, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ''', (class_name, grade, now, now))
    
    conn.commit()
    logger.info(f"创建班级表并添加了 {len(existing_classes)} 个班级记录")
    
    # 返回班级ID映射，用于后续更新学生和用户表
    cursor.execute("SELECT id, class_name FROM classes")
    class_map = {row['class_name']: row['id'] for row in cursor.fetchall()}
    return class_map

def update_students_table(conn, class_map):
    """更新学生表，添加引用班级表的外键"""
    cursor = conn.cursor()
    
    # 检查students_new表是否存在，如果存在则删除
    cursor.execute("DROP TABLE IF EXISTS students_new")
    conn.commit()
    logger.info("删除students_new表（如果存在）")
    
    # 检查students表是否存在class_id列
    cursor.execute("PRAGMA table_info(students)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # 如果已经有class_id列，先获取现有数据
    students_data = []
    cursor.execute("SELECT id, class FROM students")
    students_data = [(row['id'], row['class']) for row in cursor.fetchall()]
    
    # 创建新的students表
    cursor.execute('''
    CREATE TABLE students_new (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        gender TEXT NOT NULL,
        class TEXT,
        class_id INTEGER,
        height REAL,
        weight REAL,
        chest_circumference REAL,
        vital_capacity REAL,
        dental_caries TEXT,
        vision_left REAL,
        vision_right REAL,
        physical_test_status TEXT,
        comments TEXT,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY (class_id) REFERENCES classes(id)
    )
    ''')
    
    # 获取students表的所有列名
    cursor.execute("PRAGMA table_info(students)")
    all_columns = [row[1] for row in cursor.fetchall()]
    logger.info(f"现有表列: {all_columns}")
    
    # 确保要复制的列都存在
    expected_columns = ['id', 'name', 'gender', 'class', 'height', 'weight', 
                        'chest_circumference', 'vital_capacity', 'dental_caries',
                        'vision_left', 'vision_right', 'physical_test_status',
                        'created_at', 'updated_at']
    
    # 确定实际可以复制的列
    columns_to_copy = [col for col in expected_columns if col in all_columns]
    columns_str = ", ".join(columns_to_copy)
    logger.info(f"将复制以下列: {columns_str}")
    
    try:
        # 复制所有现有数据到新表
        cursor.execute(f'''
        INSERT INTO students_new 
           ({columns_str}, class_id)
        SELECT {columns_str}, NULL
        FROM students
        ''')
        logger.info("成功复制学生数据到新表")
    except sqlite3.IntegrityError as e:
        logger.error(f"复制数据时出错: {e}")
        # 尝试逐行插入
        logger.info("尝试逐行插入数据...")
        cursor.execute(f"SELECT {columns_str} FROM students")
        rows = cursor.fetchall()
        inserted = 0
        
        for row in rows:
            try:
                values = [row[col] for col in columns_to_copy]
                values_str = ", ".join(["?" for _ in values])
                cursor.execute(f'''
                INSERT INTO students_new ({columns_str}, class_id)
                VALUES ({values_str}, NULL)
                ''', values)
                inserted += 1
            except sqlite3.Error as e2:
                logger.warning(f"插入记录 {row['id']} 失败: {e2}")
        
        logger.info(f"逐行插入完成，成功插入 {inserted}/{len(rows)} 条记录")
    
    # 更新class_id字段
    for student_id, class_name in students_data:
        if class_name in class_map:
            try:
                cursor.execute('''
                UPDATE students_new 
                SET class_id = ? 
                WHERE id = ?
                ''', (class_map[class_name], student_id))
            except sqlite3.Error as e:
                logger.warning(f"更新学生 {student_id} 的班级ID时出错: {e}")
    
    # 替换旧表
    cursor.execute("DROP TABLE students")
    cursor.execute("ALTER TABLE students_new RENAME TO students")
    
    conn.commit()
    logger.info(f"已更新学生表，为学生记录设置了班级ID")

def update_users_table(conn, class_map):
    """更新用户表，添加引用班级表的外键"""
    cursor = conn.cursor()
    
    # 检查users_new表是否存在，如果存在则删除
    cursor.execute("DROP TABLE IF EXISTS users_new")
    conn.commit()
    logger.info("删除users_new表（如果存在）")
    
    # 检查users表是否存在class_id列
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    logger.info(f"用户表现有列: {columns}")
    
    # 获取所有用户信息
    cursor.execute("SELECT id, username, class_id FROM users")
    users_data = [(row['id'], row['username'], row['class_id']) for row in cursor.fetchall()]
    
    # 创建新的users表
    cursor.execute('''
    CREATE TABLE users_new (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        class_id INTEGER,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY (class_id) REFERENCES classes(id)
    )
    ''')
    
    # 获取表的所有列名
    cursor.execute("PRAGMA table_info(users)")
    all_columns = [row[1] for row in cursor.fetchall()]
    
    # 确保要复制的列都存在
    expected_columns = ['id', 'username', 'password_hash', 'is_admin', 'created_at', 'updated_at']
    
    # 确定实际可以复制的列
    columns_to_copy = [col for col in expected_columns if col in all_columns]
    columns_str = ", ".join(columns_to_copy)
    logger.info(f"将复制以下列: {columns_str}")
    
    try:
        # 复制所有现有数据到新表
        cursor.execute(f'''
        INSERT INTO users_new 
        ({columns_str}, class_id)
        SELECT {columns_str}, NULL
        FROM users
        ''')
        logger.info("成功复制用户数据到新表")
    except sqlite3.IntegrityError as e:
        logger.error(f"复制数据时出错: {e}")
        # 尝试逐行插入
        logger.info("尝试逐行插入数据...")
        cursor.execute(f"SELECT {columns_str} FROM users")
        rows = cursor.fetchall()
        inserted = 0
        
        for row in rows:
            try:
                values = [row[col] for col in columns_to_copy]
                values_str = ", ".join(["?" for _ in values])
                cursor.execute(f'''
                INSERT INTO users_new ({columns_str}, class_id)
                VALUES ({values_str}, NULL)
                ''', values)
                inserted += 1
            except sqlite3.Error as e2:
                logger.warning(f"插入记录 {row['id']} 失败: {e2}")
        
        logger.info(f"逐行插入完成，成功插入 {inserted}/{len(rows)} 条记录")
    
    # 更新class_id字段 - 这里假设users表中现有的class_id存储的是班级名称
    for user_id, username, old_class_id in users_data:
        if old_class_id and old_class_id in class_map:
            try:
                cursor.execute('''
                UPDATE users_new 
                SET class_id = ? 
                WHERE id = ?
                ''', (class_map[old_class_id], user_id))
                logger.info(f"用户 {username}(ID:{user_id}) 的班级ID已更新为 {class_map[old_class_id]}")
            except sqlite3.Error as e:
                logger.warning(f"更新用户 {user_id} 的班级ID时出错: {e}")
        else:
            # 如果找不到对应的班级ID，尝试根据用户名推断
            # 这里假设用户名可能包含班级信息
            potential_classes = [c for c in class_map.keys() if c in username]
            if potential_classes:
                try:
                    cursor.execute('''
                    UPDATE users_new 
                    SET class_id = ? 
                    WHERE id = ?
                    ''', (class_map[potential_classes[0]], user_id))
                    logger.info(f"根据用户名 '{username}' 推断班级为 '{potential_classes[0]}'，班级ID为 {class_map[potential_classes[0]]}")
                except sqlite3.Error as e:
                    logger.warning(f"更新用户 {user_id} 的班级ID时出错: {e}")
    
    # 替换旧表
    cursor.execute("DROP TABLE users")
    cursor.execute("ALTER TABLE users_new RENAME TO users")
    
    conn.commit()
    logger.info("已更新用户表，重设了班级ID关联")

def update_auth_logic():
    """创建一个权限检查的实现示例"""
    code_sample = """
# 权限检查示例 - 用于学生API
def check_student_access(student_id, current_user):
    # 管理员可以访问所有学生
    if current_user.is_admin:
        return True
        
    # 获取学生的班级ID
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT class_id FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    
    if not student:
        return False
        
    # 班主任只能访问自己班级的学生
    student_class_id = student['class_id']
    return student_class_id == current_user.class_id
"""
    
    print("\n===== 权限检查示例代码 =====")
    print(code_sample)
    print("========================\n")

def migrate_database():
    """执行完整的数据库迁移过程"""
    
    # 备份数据库
    if not backup_database():
        logger.error("无法继续迁移，备份失败")
        return False
    
    try:
        conn = get_db_connection()
        
        # 创建班级表并获取班级ID映射
        class_map = create_classes_table(conn)
        if not class_map:
            logger.warning("未找到班级数据，创建了空的班级表")
        
        # 更新学生表
        update_students_table(conn, class_map)
        
        # 更新用户表
        update_users_table(conn, class_map)
        
        conn.close()
        
        # 输出权限逻辑示例
        update_auth_logic()
        
        logger.info("数据库迁移完成!")
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("====== ClassMaster 2.0 数据库迁移工具 ======")
    print("本工具将更新数据库结构，创建班级表并重构学生和用户表。")
    print("执行前会自动创建数据库备份。")
    
    confirm = input("是否继续执行迁移? (y/n): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        exit(0)
    
    success = migrate_database()
    
    if success:
        print("\n数据库迁移已成功完成!")
        print("下一步: 修改 server.py 中的权限检查逻辑，使用新的数据模型。")
    else:
        print("\n数据库迁移过程中出现错误，请检查日志。")
        print("您可以使用自动创建的备份文件恢复数据库。") 