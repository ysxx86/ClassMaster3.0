#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复学生表主键约束的迁移脚本
将students表的主键从单一id改为(id, class_id)组合
"""

import sqlite3
import logging
import datetime
import shutil
import os

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
    return conn

def fix_student_id_constraint():
    """修复学生表的主键约束"""
    logger.info("开始修复学生表主键约束")
    
    # 创建数据库备份
    backup_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"students_backup_{backup_date}.db"
    
    try:
        shutil.copy2(DATABASE, backup_file)
        logger.info(f"已创建数据库备份: {backup_file}")
    except Exception as e:
        logger.error(f"创建数据库备份失败: {str(e)}")
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取当前表结构
    cursor.execute('PRAGMA table_info(students)')
    columns = cursor.fetchall()
    
    # 临时关闭外键约束
    cursor.execute('PRAGMA foreign_keys=OFF')
    
    # 开始事务
    cursor.execute('BEGIN TRANSACTION')
    
    try:
        # 1. 创建新表，使用复合主键
        logger.info("创建新的students表结构")
        
        # 构建CREATE TABLE语句
        create_table_sql = "CREATE TABLE students_new (\n"
        
        # 添加所有列定义
        for i, col in enumerate(columns):
            col_name = col['name']
            col_type = col['type']
            not_null = "NOT NULL" if col['notnull'] == 1 else ""
            default_value = f"DEFAULT '{col['dflt_value']}'" if col['dflt_value'] is not None else ""
            
            # 跳过PRIMARY KEY约束，我们将在最后添加
            if col_name == 'id':
                create_table_sql += f"    {col_name} {col_type} {not_null},\n"
            else:
                create_table_sql += f"    {col_name} {col_type} {not_null} {default_value},\n"
        
        # 添加主键和外键约束
        create_table_sql += "    PRIMARY KEY (id, class_id),\n"
        create_table_sql += "    FOREIGN KEY (class_id) REFERENCES classes(id)\n"
        create_table_sql += "        ON UPDATE CASCADE\n"
        create_table_sql += "        ON DELETE RESTRICT\n"
        create_table_sql += ")"
        
        # 创建新表
        logger.info(f"执行创建表SQL: {create_table_sql}")
        cursor.execute(create_table_sql)
        
        # 2. 复制现有数据
        logger.info("复制现有数据到新表")
        
        # 获取所有列名
        column_names = [col['name'] for col in columns]
        columns_str = ', '.join(column_names)
        
        # 构建INSERT语句
        insert_sql = f"INSERT INTO students_new ({columns_str}) SELECT {columns_str} FROM students"
        logger.info(f"执行数据复制SQL: {insert_sql}")
        cursor.execute(insert_sql)
        
        # 3. 更新没有class_id的记录
        logger.info("更新缺少class_id的记录")
        cursor.execute("UPDATE students_new SET class_id = '1' WHERE class_id IS NULL OR class_id = ''")
        
        # 4. 删除旧表
        logger.info("删除旧表")
        cursor.execute('DROP TABLE students')
        
        # 5. 重命名新表
        logger.info("重命名新表")
        cursor.execute('ALTER TABLE students_new RENAME TO students')
        
        # 6. 提交事务
        conn.commit()
        logger.info("学生表主键约束修复完成")
        
        # 7. 开启外键约束
        cursor.execute('PRAGMA foreign_keys=ON')
        
        # 8. 验证外键约束
        cursor.execute('PRAGMA foreign_key_check')
        violations = cursor.fetchall()
        if violations:
            logger.warning(f"检测到外键约束违规: {violations}")
            logger.warning("您可能需要清理这些违规数据")
        else:
            logger.info("未检测到外键约束违规，所有数据符合完整性要求")
        
        return True
        
    except Exception as e:
        # 出错回滚
        conn.rollback()
        logger.error(f"修复学生表主键约束失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("====== 修复学生表主键约束 ======")
    print("本工具将修改students表的主键约束，使其支持相同学号不同班级的学生。")
    print("执行前会自动创建数据库备份。")
    
    # 确保uploads目录存在
    os.makedirs('uploads', exist_ok=True)
    
    confirm = input("是否继续执行修复? (y/n): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        exit(0)
    
    if fix_student_id_constraint():
        print("\n学生表主键约束修复成功！")
        print("现在可以导入相同学号但不同班级的学生了。")
    else:
        print("\n修复过程中出现错误，请检查日志。")
        print("您可以使用自动创建的备份文件恢复数据库。") 