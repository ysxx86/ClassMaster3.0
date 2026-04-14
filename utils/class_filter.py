# -*- coding: utf-8 -*-
from flask_login import current_user
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def class_filter(func):
    """
    装饰器：根据当前用户权限过滤数据库查询结果
    
    用法示例:
    @class_filter
    def get_all_students():
        # 原有查询代码
        return students_data
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 如果用户未登录，则直接执行原函数
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            return func(*args, **kwargs)
        
        # 如果是管理员，不进行过滤
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            logger.debug(f"管理员访问，不过滤班级数据")
            return func(*args, **kwargs)
        
        # 如果是班主任，过滤数据
        if hasattr(current_user, 'class_id') and current_user.class_id:
            logger.debug(f"班主任访问，班级ID: {current_user.class_id}, 应用班级过滤")
            
            # 添加班级ID过滤参数
            if 'class_id' not in kwargs:
                kwargs['class_id'] = current_user.class_id
                
            result = func(*args, **kwargs)
            
            # 对返回的列表数据进行过滤（适用于返回字典或对象列表的情况）
            if isinstance(result, list):
                filtered_result = []
                for item in result:
                    # 如果是字典，检查class_id
                    if isinstance(item, dict) and 'class_id' in item:
                        if item['class_id'] == current_user.class_id:
                            filtered_result.append(item)
                    # 如果是对象，检查class_id属性
                    elif hasattr(item, 'class_id'):
                        if item.class_id == current_user.class_id:
                            filtered_result.append(item)
                    # 如果没有班级信息，默认不显示
                    else:
                        continue
                return filtered_result
            
            return result
        
        # 默认情况，直接调用原函数
        return func(*args, **kwargs)
    
    return wrapper

def user_can_access(student_id):
    """
    检查当前用户是否有权限访问指定学生的数据
    
    用法示例:
    if user_can_access(student_id):
        # 执行访问操作
    else:
        # 返回权限不足错误
    """
    # 如果是管理员，可以访问所有学生
    if hasattr(current_user, 'is_admin') and current_user.is_admin:
        return True
    
    # 如果没有班级ID，不允许访问
    if not hasattr(current_user, 'class_id') or not current_user.class_id:
        return False
    
    # 查询学生所属班级
    import sqlite3
    
    try:
        # 避免循环导入问题
        DATABASE = 'students.db'
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT class_id FROM students WHERE id = ?', (student_id,))
        student = cursor.fetchone()
        conn.close()
        
        if not student:
            return False
        
        # 检查学生班级是否与用户负责的班级匹配
        return student[0] == current_user.class_id
    except Exception as e:
        logger.error(f"检查学生访问权限时出错: {str(e)}")
        return False 