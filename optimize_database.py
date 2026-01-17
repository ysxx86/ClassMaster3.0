# -*- coding: utf-8 -*-
"""
数据库性能优化脚本
添加索引、优化查询性能
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE = 'students.db'

def optimize_database():
    """优化数据库性能"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        logger.info("开始优化数据库...")
        
        # 1. 为students表添加索引
        logger.info("为students表添加索引...")
        
        # 班级ID索引 - 用于按班级查询
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_class_id ON students(class_id)')
            logger.info("✓ 创建索引: idx_students_class_id")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败: idx_students_class_id - {e}")
        
        # 学号索引 - 用于快速查找学生
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_id ON students(id)')
            logger.info("✓ 创建索引: idx_students_id")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败: idx_students_id - {e}")
        
        # 更新时间索引 - 用于检查数据变更
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_updated_at ON students(updated_at)')
            logger.info("✓ 创建索引: idx_students_updated_at")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败: idx_students_updated_at - {e}")
        
        # 2. 为grades表添加索引
        logger.info("为grades表添加索引...")
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_grades_student_id ON grades(student_id)')
            logger.info("✓ 创建索引: idx_grades_student_id")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败: idx_grades_student_id - {e}")
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_grades_semester ON grades(semester)')
            logger.info("✓ 创建索引: idx_grades_semester")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败: idx_grades_semester - {e}")
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_grades_updated_at ON grades(updated_at)')
            logger.info("✓ 创建索引: idx_grades_updated_at")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败: idx_grades_updated_at - {e}")
        
        # 3. 为users表添加索引
        logger.info("为users表添加索引...")
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            logger.info("✓ 创建索引: idx_users_username")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败: idx_users_username - {e}")
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_class_id ON users(class_id)')
            logger.info("✓ 创建索引: idx_users_class_id")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败: idx_users_class_id - {e}")
        
        # 4. 为classes表添加索引
        logger.info("为classes表添加索引...")
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_classes_class_name ON classes(class_name)')
            logger.info("✓ 创建索引: idx_classes_class_name")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败: idx_classes_class_name - {e}")
        
        # 5. 优化数据库
        logger.info("执行VACUUM优化...")
        cursor.execute('VACUUM')
        logger.info("✓ VACUUM完成")
        
        logger.info("执行ANALYZE分析...")
        cursor.execute('ANALYZE')
        logger.info("✓ ANALYZE完成")
        
        # 提交更改
        conn.commit()
        conn.close()
        
        logger.info("=" * 50)
        logger.info("数据库优化完成!")
        logger.info("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"数据库优化失败: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    optimize_database()
