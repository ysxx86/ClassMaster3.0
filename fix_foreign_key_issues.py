#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
外键约束违规数据修复脚本
用于修复在添加外键约束时可能发现的数据不一致问题
"""

import sqlite3
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
    return conn

def find_violations():
    """查找外键约束违规数据"""
    logger.info("开始查找外键约束违规数据")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 开启外键约束检查
    cursor.execute('PRAGMA foreign_keys=ON')
    
    # 检查外键约束违规
    cursor.execute('PRAGMA foreign_key_check')
    violations = cursor.fetchall()
    
    if not violations:
        logger.info("未发现外键约束违规数据")
        conn.close()
        return []
    
    # 解析违规信息
    violation_details = []
    for violation in violations:
        table_name = violation[0]  # 违规表名
        row_id = violation[1]      # 违规行ID
        ref_table = violation[2]   # 引用表名
        fk_id = violation[3]       # 外键ID
        
        # 获取违规记录详情
        cursor.execute(f'SELECT * FROM {table_name} WHERE rowid = ?', (row_id,))
        record = cursor.fetchone()
        
        if record:
            violation_details.append({
                'table': table_name,
                'row_id': row_id,
                'ref_table': ref_table,
                'fk_id': fk_id,
                'record': dict(record)
            })
        
    conn.close()
    
    logger.info(f"发现 {len(violation_details)} 条外键约束违规数据")
    return violation_details

def fix_violations():
    """修复外键约束违规数据"""
    violations = find_violations()
    
    if not violations:
        print("数据库中未发现外键约束违规，无需修复")
        return True
    
    print(f"发现 {len(violations)} 条外键约束违规数据，开始修复...")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 关闭外键约束
    cursor.execute('PRAGMA foreign_keys=OFF')
    
    # 开始事务
    cursor.execute('BEGIN TRANSACTION')
    
    try:
        for violation in violations:
            table = violation['table']
            row_id = violation['row_id']
            ref_table = violation['ref_table']
            
            logger.info(f"修复 {table} 表中 rowid={row_id} 的违规数据")
            
            if table == 'users':
                # 对于users表，将无效的class_id设为NULL
                if ref_table == 'classes':
                    cursor.execute('UPDATE users SET class_id = NULL WHERE rowid = ?', (row_id,))
                    logger.info(f"将users表中rowid={row_id}的class_id设为NULL")
                
            elif table == 'students':
                # 对于students表，这种情况比较复杂，因为class_id是主键的一部分
                # 需要根据业务逻辑决定处理方法
                logger.warning(f"学生表违规数据需要手动处理: rowid={row_id}")
                print(f"警告: 学生表中发现违规数据(rowid={row_id})，请手动检查并修复")
                
            elif table == 'comments':
                # 对于comments表，将无效的user_id设为NULL
                if ref_table == 'users':
                    cursor.execute('UPDATE comments SET user_id = NULL WHERE rowid = ?', (row_id,))
                    logger.info(f"将comments表中rowid={row_id}的user_id设为NULL")
                
            elif table == 'todos':
                # 对于todos表，删除违规记录
                cursor.execute('DELETE FROM todos WHERE rowid = ?', (row_id,))
                logger.info(f"删除todos表中的违规记录: rowid={row_id}")
                
            elif table == 'activities':
                # 对于activities表，根据违规字段进行修复
                if ref_table == 'users':
                    cursor.execute('UPDATE activities SET user_id = NULL WHERE rowid = ?', (row_id,))
                    logger.info(f"将activities表中rowid={row_id}的user_id设为NULL")
                elif ref_table == 'classes':
                    cursor.execute('UPDATE activities SET class_id = NULL WHERE rowid = ?', (row_id,))
                    logger.info(f"将activities表中rowid={row_id}的class_id设为NULL")
        
        # 提交事务
        conn.commit()
        logger.info("违规数据修复完成")
        
        # 验证是否还有违规
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA foreign_key_check')
        remaining_violations = cursor.fetchall()
        
        if remaining_violations:
            logger.warning(f"仍有 {len(remaining_violations)} 条违规数据未修复")
            print(f"警告: 仍有 {len(remaining_violations)} 条违规数据未修复，可能需要手动处理")
            return False
        else:
            logger.info("所有违规数据已修复")
            return True
            
    except Exception as e:
        # 出错回滚
        conn.rollback()
        logger.error(f"修复违规数据时出错: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if fix_violations():
        print("外键约束违规数据修复完成！")
    else:
        print("部分外键约束违规数据修复失败，请查看日志或手动修复。") 