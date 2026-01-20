#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学生管理模块，包含学生相关的API路由和功能
"""

import os
import datetime
import traceback
import sqlite3
from flask import Blueprint, request, jsonify, send_from_directory, url_for, send_file
from werkzeug.utils import secure_filename
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from flask_login import login_required, current_user
from utils.class_filter import class_filter, user_can_access
from utils.permission_checker import can_access_students, get_accessible_classes, require_head_teacher
import logging
import openpyxl
from io import BytesIO

# 配置日志
logger = logging.getLogger(__name__)

# 学生蓝图
students_bp = Blueprint('students', __name__)

# 配置
UPLOAD_FOLDER = 'uploads'
TEMPLATE_FOLDER = 'templates'
DATABASE = 'students.db'

# 常量定义
VALID_GRADES = ['优', '良', '及格', '待及格', '/']  # 使用列表而不是集合，兼容性更好

DEYU_SCORE_LIMITS = {
    'pinzhi': 30,    # 品德修养
    'xuexi': 20,     # 学习素养
    'jiankang': 20,  # 身心健康
    'shenmei': 10,   # 审美素养
    'shijian': 10,   # 实践创新
    'shenghuo': 10   # 生活素养
}

DEYU_TOTAL_LIMIT = 100

# 创建数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

def normalize_class_name(class_name_input):
    """
    将各种格式的班级名称标准化为数据库格式
    
    支持的输入格式：
    - 204 -> 二年级4班
    - 二年级4班 -> 二年级4班
    - 二年4班 -> 二年级4班
    - 二年级四班 -> 二年级4班
    - 二年四班 -> 二年级4班
    - 2024级4班 -> 二年级4班
    - 小学2024级4班 -> 二年级4班
    
    返回: (标准班级名称, 是否成功匹配)
    """
    if not class_name_input:
        return None, False
    
    import re
    
    # 去除空格和特殊字符
    class_name = str(class_name_input).strip().replace(' ', '').replace('　', '')
    
    # 中文数字到阿拉伯数字的映射
    chinese_to_num = {
        '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
        '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'
    }
    
    # 年级映射（处理2024级这种格式）
    current_year = 2026  # 当前年份
    
    # 模式1: 纯数字格式 "204" -> "二年级4班"
    match = re.match(r'^(\d)0?(\d{1,2})$', class_name)
    if match:
        grade_num = match.group(1)
        class_num = match.group(2).lstrip('0') or '0'  # 去除前导0
        grade_map = {'1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六'}
        if grade_num in grade_map:
            return f"{grade_map[grade_num]}年级{class_num}班", True
    
    # 模式2: "2024级4班" 或 "小学2024级4班" -> "二年级4班"
    match = re.search(r'(\d{4})级(\d+)班', class_name)
    if match:
        year = int(match.group(1))
        class_num = match.group(2)
        # 计算年级：
        # 2024年9月入学 -> 2024-2025学年一年级 -> 2025-2026学年二年级
        # 当前是2026年1月，正在读二年级上学期
        # 所以：当前年份(2026) - 入学年份(2024) = 2年级
        grade = current_year - year
        if 1 <= grade <= 6:
            grade_map = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六'}
            return f"{grade_map[grade]}年级{class_num}班", True
    
    # 模式3: "二年4班" -> "二年级4班"
    match = re.match(r'^([一二三四五六])年(\d+)班$', class_name)
    if match:
        grade_chinese = match.group(1)
        class_num = match.group(2)
        return f"{grade_chinese}年级{class_num}班", True
    
    # 模式4: "二年级四班" -> "二年级4班"
    match = re.match(r'^([一二三四五六])年级([一二三四五六七八九十]+)班$', class_name)
    if match:
        grade_chinese = match.group(1)
        class_chinese = match.group(2)
        # 转换班级数字
        class_num = chinese_to_num.get(class_chinese, class_chinese)
        return f"{grade_chinese}年级{class_num}班", True
    
    # 模式5: "二年四班" -> "二年级4班"
    match = re.match(r'^([一二三四五六])年([一二三四五六七八九十]+)班$', class_name)
    if match:
        grade_chinese = match.group(1)
        class_chinese = match.group(2)
        class_num = chinese_to_num.get(class_chinese, class_chinese)
        return f"{grade_chinese}年级{class_num}班", True
    
    # 模式6: 已经是标准格式 "二年级4班"
    match = re.match(r'^([一二三四五六])年级(\d+)班$', class_name)
    if match:
        return class_name, True
    
    # 无法识别的格式
    return None, False

def find_class_id_by_name(cursor, class_name_input):
    """
    根据班级名称查找班级ID，支持模糊匹配
    
    返回: (class_id, normalized_name, error_message)
    """
    # 先尝试标准化班级名称
    normalized_name, success = normalize_class_name(class_name_input)
    
    if success and normalized_name:
        # 使用标准化后的名称查询
        cursor.execute('SELECT id, class_name FROM classes WHERE class_name = ?', (normalized_name,))
        result = cursor.fetchone()
        if result:
            return result['id'], normalized_name, None
    
    # 如果标准化后仍然找不到，尝试直接查询原始名称
    cursor.execute('SELECT id, class_name FROM classes WHERE class_name = ?', (class_name_input,))
    result = cursor.fetchone()
    if result:
        return result['id'], result['class_name'], None
    
    # 获取所有班级列表，用于错误提示
    cursor.execute('SELECT class_name FROM classes ORDER BY class_name')
    all_classes = [row['class_name'] for row in cursor.fetchall()]
    
    # 生成错误提示
    if normalized_name:
        error_msg = f'班级 "{class_name_input}" 标准化为 "{normalized_name}" 后仍未找到。'
    else:
        error_msg = f'无法识别班级格式 "{class_name_input}"。'
    
    error_msg += f'\n\n可用的班级有：{", ".join(all_classes)}'
    error_msg += f'\n\n支持的格式示例：'
    error_msg += f'\n  - 标准格式：二年级4班'
    error_msg += f'\n  - 简写格式：二年4班'
    error_msg += f'\n  - 数字格式：204（2表示二年级，04表示4班）'
    error_msg += f'\n  - 年份格式：2024级4班（自动计算年级）'
    error_msg += f'\n  - 中文数字：二年级四班'
    
    return None, normalized_name, error_msg

# 创建学生导入模板
def create_student_template():
    template_dir = 'templates'
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    template_path = os.path.join(template_dir, 'student_template.xlsx')
    
    # 如果文件存在且被占用，则跳过创建
    if os.path.exists(template_path):
        try:
            # 尝试打开文件，如果可以打开就先删除
            with open(template_path, 'a'):
                pass
            os.remove(template_path)
        except:
            print("学生模板文件被占用，跳过创建")
            return template_path
    
    wb = Workbook()
    ws = wb.active
    ws.title = "学生信息"
    
    # 设置标题行 - 与导出功能保持一致的完整30个字段
    headers = ['学号', '姓名', '性别', '班级', '身高(cm)', '体重(kg)', 
              '胸围(cm)', '肺活量(ml)', '龋齿(个)', '视力左', '视力右', '体测情况',
              '语文', '数学', '英语', '劳动', '体育', '音乐', '美术', 
              '科学', '综合', '信息', '书法', '心理',
              '品质', '学习', '健康', '审美', '实践', '生活',
              '评语']
    for i, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=i, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        # 为评语列设置更宽的列宽
        if header == '评语':
            ws.column_dimensions[get_column_letter(i)].width = 40
        else:
            ws.column_dimensions[get_column_letter(i)].width = 15
    
    # 添加示例数据 - 包含所有31个字段的示例
    example_data = [
        '1', '张三', '男', '三年级一班', '135', '32', '65', '1500', '0', '5.0', '5.0', '健康',  # 基础信息
        '优秀', '良好', '优秀', '良好', '优秀', '良好', '优秀', '良好', '优秀', '良好', '优秀', '良好',  # 学科成绩
        '25', '18', '18', '8', '8', '8',  # 德育维度
        '该学生表现优秀，德智体美劳全面发展。'  # 评语
    ]
    for i, value in enumerate(example_data, 1):
        ws.cell(row=2, column=i, value=value)
    
    # 添加说明文字
    ws.cell(row=4, column=1, value="说明事项：")
    ws.cell(row=5, column=1, value="1. 请按照示例格式填写学生信息")
    ws.cell(row=6, column=1, value='2. 性别请填写"男"或"女"')
    ws.cell(row=7, column=1, value="3. 班级格式: 三年级一班")
    ws.cell(row=8, column=1, value="4. 视力格式: 5.0 或 4.8 等")
    ws.cell(row=9, column=1, value="5. 学科成绩请填写: 优秀、良好、一般、待改进 中的一个")
    ws.cell(row=10, column=1, value="6. 体测情况请填写: 健康、肥胖、营养不良 中的一个")
    ws.cell(row=11, column=1, value="7. 德育维度分数: 品质(0-30)、学习(0-20)、健康(0-20)、审美(0-10)、实践(0-10)、生活(0-10)")
    ws.cell(row=12, column=1, value="8. 评语不能超过260个字")
    ws.cell(row=13, column=1, value="9. 班主任导入学生数据时，班级必须与当前所管理的班级一致，否则无法导入")
    
    # 合并说明文字的单元格
    for i in range(4, 14):
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=8)
    
    wb.save(template_path)
    print("学生Excel模板创建完成")
    return template_path

# 获取所有学生API - 支持分页和按需加载
@students_bp.route('/api/students', methods=['GET'], strict_slashes=False)
@login_required
def get_all_students():
    # 获取分页参数
    page = request.args.get('page', type=int, default=1)
    page_size = request.args.get('page_size', type=int, default=100)
    class_filter = request.args.get('class_id', type=str, default=None)
    
    # 获取用户有权限访问的班级列表
    accessible_classes = get_accessible_classes(current_user)
    
    if not accessible_classes:
        logger.warning(f"用户 {current_user.username} 没有权限访问任何班级")
        return jsonify({
            'status': 'ok',
            'count': 0,
            'total': 0,
            'page': page,
            'page_size': page_size,
            'students': [],
            'message': '您没有权限查看任何班级的学生'
        })
    
    # 如果指定了班级筛选，验证权限
    if class_filter and class_filter not in [str(c) for c in accessible_classes]:
        return jsonify({
            'status': 'error',
            'message': '您没有权限访问该班级'
        }), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 构建查询条件
        if class_filter:
            where_clause = 'WHERE s.class_id = ?'
            params = [class_filter]
        else:
            placeholders = ','.join('?' * len(accessible_classes))
            where_clause = f'WHERE s.class_id IN ({placeholders})'
            params = accessible_classes
        
        # 先获取总数
        cursor.execute(f'''
            SELECT COUNT(*) as total
            FROM students s
            {where_clause}
        ''', params)
        total = cursor.fetchone()['total']
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 分页查询，返回完整的学生信息
        logger.info(f"用户 {current_user.username} 查询第{page}页，每页{page_size}条")
        cursor.execute(f'''
            SELECT 
                s.rowid AS rowid,
                s.id,
                s.name,
                s.gender,
                s.class_id,
                s.height,
                s.weight,
                s.chest_circumference,
                s.vital_capacity,
                s.vision_left,
                s.vision_right,
                s.dental_caries,
                s.physical_test_status,
                s.comments,
                s.updated_at,
                c.class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            {where_clause}
            ORDER BY c.class_name, CAST(s.id AS INTEGER)
            LIMIT ? OFFSET ?
        ''', params + [page_size, offset])
            
        students = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'status': 'ok',
            'count': len(students),
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'students': students
        })
    except Exception as e:
        logger.error(f"获取学生列表时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'获取学生列表失败: {str(e)}'}), 500
    finally:
        conn.close()

# 获取单个学生API
@students_bp.route('/api/student/<student_id>', methods=['GET'])
@login_required
def get_student(student_id):
    """获取学生详情"""
    try:
        # 获取班级ID
        class_id = request.args.get('class_id')
        if not class_id:
            return jsonify({'error': '缺少班级ID'}), 400
            
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 使用复合主键查询
        cursor.execute('''
            SELECT s.*, c.class_name 
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.id = ? AND s.class_id = ?
        ''', (student_id, class_id))
        
        student = cursor.fetchone()
        if not student:
            return jsonify({'error': '未找到该学生'}), 404
            
        # 转换为字典
        student_dict = dict(student)
        
        # 处理数值字段
        numeric_fields = ['height', 'weight', 'chest_circumference', 'vital_capacity', 
                         'vision_left', 'vision_right']
        for field in numeric_fields:
            if field in student_dict and student_dict[field] is not None:
                student_dict[field] = float(student_dict[field])
        
        return jsonify(student_dict)
        
    except Exception as e:
        logger.error(f"获取学生详情时出错: {str(e)}")
        return jsonify({'error': f'获取学生详情失败: {str(e)}'}), 500
    finally:
        conn.close()

# 添加新学生API
@students_bp.route('/api/students', methods=['POST'], strict_slashes=False)
@login_required
def add_student():
    data = request.json
    
    if not data:
        return jsonify({'error': '无效的请求数据'}), 400
    
    required_fields = ['id', 'name', 'gender']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少必要的字段: {field}'}), 400
    
    # 检查是否有权限添加学生
    if not can_access_students(current_user):
        return jsonify({'error': '您没有权限添加学生'}), 403
    
    # 如果是正班主任，自动设置班级ID
    if not current_user.is_admin and current_user.class_id:
        # 检查是否已提供了class_id，如果是，确保与班主任的class_id一致
        if 'class_id' in data and data['class_id'] != current_user.class_id:
            return jsonify({'error': '正班主任只能添加本班学生'}), 403
        
        # 设置班级ID
        data['class_id'] = current_user.class_id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查学生ID是否在当前班级已存在
    cursor.execute('SELECT id FROM students WHERE id = ? AND class_id = ?', (data['id'], data['class_id']))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': f'学号 {data["id"]} 在当前班级已存在'}), 400
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 确保数值类型字段的正确处理
    height = data.get('height')
    weight = data.get('weight')
    chest_circumference = data.get('chest_circumference')
    vital_capacity = data.get('vital_capacity')
    vision_left = data.get('vision_left')
    vision_right = data.get('vision_right')
    
    try:
        cursor.execute('''
        INSERT INTO students (
            id, name, gender, class_id, height, weight,
            chest_circumference, vital_capacity, dental_caries,
            vision_left, vision_right, physical_test_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data['name'], data['gender'],
            data.get('class_id'), height, weight, 
            chest_circumference, vital_capacity, data.get('dental_caries', ''),
            vision_left, vision_right, data.get('physical_test_status', ''),
            now, now
        ))
        
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'message': f'成功添加学生: {data["name"]}',
            'student_id': data['id']
        })
    except Exception as e:
        conn.rollback()
        logger.error(f"添加学生时出错: {str(e)}")
        return jsonify({'error': f'添加学生时出错: {str(e)}'}), 500
    finally:
        conn.close()

# 更新学生API
@students_bp.route('/api/student/<student_id>', methods=['PUT'])
@login_required
def update_student(student_id):
    """更新学生信息"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': '没有提供更新数据'}), 400
        
        # 获取班级ID
        class_id = data.get('class_id')
        if not class_id:
            return jsonify({'error': '缺少班级ID'}), 400
        
        # 检查是否有权限访问该班级的学生
        if not can_access_students(current_user, class_id):
            return jsonify({'error': '您没有权限更新该班级的学生信息'}), 403
            
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学生是否存在
        cursor.execute('SELECT id FROM students WHERE id = ? AND class_id = ?', 
                      (student_id, class_id))
        if not cursor.fetchone():
            return jsonify({'error': '未找到该学生'}), 404
        
        # 准备更新数据
        update_fields = []
        update_values = []
        
        # 处理数值字段
        numeric_fields = ['height', 'weight', 'chest_circumference', 'vital_capacity', 
                         'vision_left', 'vision_right']
        for field in numeric_fields:
            if field in data:
                try:
                    value = float(data[field]) if data[field] is not None else None
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
                except (ValueError, TypeError):
                    return jsonify({'error': f'字段 {field} 的值无效'}), 400
        
        # 处理其他字段，忽略前端可能提交的 'class' 字段（数据库中使用 'class_id'）
        for field, value in data.items():
            # 不允许更新主键 'id'，也忽略前端可能提交的 'class' 字段（数据库中使用 'class_id'）
            if field in numeric_fields or field in ('class_id', 'class', 'id'):
                continue
            update_fields.append(f"{field} = ?")
            update_values.append(value)
        
        # 添加更新时间
        update_fields.append("updated_at = ?")
        update_values.append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # 添加WHERE条件
        update_values.extend([student_id, class_id])
        
        # 构建并执行更新SQL
        update_sql = f"""
            UPDATE students 
            SET {', '.join(update_fields)}
            WHERE id = ? AND class_id = ?
        """
        logger.debug(f"update_sql: {update_sql}")
        logger.debug(f"update_fields: {update_fields}")
        logger.debug(f"update_values: {update_values}")

        cursor.execute(update_sql, update_values)
        conn.commit()
        
        return jsonify({'message': '学生信息更新成功'})
        
    except Exception as e:
        logger.exception(f"更新学生信息时出错: {str(e)}")
        return jsonify({'error': f'更新学生信息失败: {str(e)}'}), 500
    finally:
        conn.close()

@students_bp.route('/api/student/<student_id>/comments', methods=['PUT'])
@login_required
def update_student_comments(student_id):
    """更新学生评语"""
    try:
        data = request.json
        if not data or 'comments' not in data:
            return jsonify({'error': '没有提供评语内容'}), 400
            
        # 获取班级ID
        class_id = data.get('class_id')
        if not class_id:
            return jsonify({'error': '缺少班级ID'}), 400
            
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学生是否存在
        cursor.execute('SELECT id FROM students WHERE id = ? AND class_id = ?', 
                      (student_id, class_id))
        if not cursor.fetchone():
            return jsonify({'error': '未找到该学生'}), 404
        
        # 更新评语
        cursor.execute('''
            UPDATE students 
            SET comments = ?, updated_at = ?
            WHERE id = ? AND class_id = ?
        ''', (data['comments'], 
              datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              student_id, class_id))
        
        conn.commit()
        return jsonify({'message': '评语更新成功'})
        
    except Exception as e:
        logger.error(f"更新学生评语时出错: {str(e)}")
        return jsonify({'error': f'更新评语失败: {str(e)}'}), 500
    finally:
        conn.close()

@students_bp.route('/api/student/<student_id>', methods=['DELETE'])
@login_required
def delete_student(student_id):
    """删除学生"""
    try:
        # 获取班级ID
        class_id = request.args.get('class_id')
        if not class_id:
            return jsonify({'error': '缺少班级ID'}), 400
        
        # 检查是否有权限删除该班级的学生
        if not can_access_students(current_user, class_id):
            return jsonify({'error': '您没有权限删除该班级的学生'}), 403
            
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学生是否存在
        cursor.execute('SELECT id FROM students WHERE id = ? AND class_id = ?', 
                      (student_id, class_id))
        if not cursor.fetchone():
            return jsonify({'error': '未找到该学生'}), 404
        # 记录调试信息：学生与班级，comments 计数与示例，以及 students 表的外键定义
        try:
            logger.debug(f"尝试删除学生，student_id={student_id}, class_id={class_id}")
            cursor.execute('SELECT COUNT(*) as cnt FROM comments WHERE student_id = ?', (student_id,))
            cnt_row = cursor.fetchone()
            cnt = cnt_row[0] if cnt_row else 0
            logger.debug(f"comments 中匹配该 student_id 的记录数: {cnt}")
            # 取少量示例行以便查看 student_id 的存储形式
            cursor.execute('SELECT rowid, student_id, class_id, comment FROM comments WHERE student_id = ? LIMIT 5', (student_id,))
            sample_comments = cursor.fetchall()
            logger.debug(f"comments 示例: {sample_comments}")
            # 查看 students 表的外键定义，帮助确认 foreign key 的目标列
            try:
                cursor.execute("PRAGMA foreign_key_list('students')")
                fk_list = cursor.fetchall()
                logger.debug(f"students 表的 foreign_key_list: {fk_list}")
            except Exception as fk_e:
                logger.debug(f"获取 students 表外键信息时出错: {fk_e}")

            # 先删除与学生相关的评语以避免外键约束冲突
            try:
                cursor.execute('DELETE FROM comments WHERE student_id = ?', (student_id,))
            except Exception as e:
                # 记录但不阻止删除操作，后续删除仍尝试执行
                logger.warning(f"删除相关评语时出错（继续尝试删除学生）: {str(e)}")
        except Exception as dbg_e:
            logger.exception(f"删除学生前的调试查询出错: {dbg_e}")

        # 删除学生
        try:
            # 为了应对数据库中外键定义不一致导致的 foreign key mismatch，
            # 在删除操作时短暂关闭 foreign key 检查（先删除 comments 后再删 students）
            logger.debug("短暂关闭 PRAGMA foreign_keys 以执行删除操作")
            cursor.execute('PRAGMA foreign_keys = OFF')
            cursor.execute('DELETE FROM students WHERE id = ? AND class_id = ?', 
                          (student_id, class_id))
            conn.commit()
        finally:
            try:
                cursor.execute('PRAGMA foreign_keys = ON')
                logger.debug('已重新启用 PRAGMA foreign_keys')
            except Exception:
                logger.warning('重新启用 PRAGMA foreign_keys 时出错')
        return jsonify({
            'message': '学生删除成功',
            'data_changed': True,  # 添加数据更改标志，用于通知前端刷新
            'timestamp': datetime.datetime.now().timestamp()
        })
        
    except Exception as e:
        logger.exception(f"删除学生时出错: {str(e)}")
        return jsonify({'error': f'删除学生失败: {str(e)}'}), 500
    finally:
        conn.close()


@students_bp.route('/api/student-by-rowid/<int:rowid>', methods=['DELETE'])
@login_required
def delete_student_by_rowid(rowid):
    """根据 SQLite 的 rowid 删除学生（用于那些没有学号的异常记录）。"""
    try:
        # 获取班级ID
        class_id = request.args.get('class_id')
        if not class_id:
            return jsonify({'error': '缺少班级ID'}), 400

        # 如果是班主任且没有分配班级，不允许删除学生
        if not current_user.is_admin and not current_user.class_id:
            logger.warning(f"班主任 {current_user.username} 未分配班级，不能删除学生")
            return jsonify({'error': '您尚未被分配班级，无法删除学生'}), 403

        # 班主任只能删除自己班级的学生
        if not current_user.is_admin and str(current_user.class_id) != str(class_id):
            return jsonify({'error': '您只能删除自己班级的学生'}), 403

        conn = get_db_connection()
        cursor = conn.cursor()

        # 查询该 rowid 对应的学生并验证班级
        cursor.execute('SELECT id, class_id FROM students WHERE rowid = ?', (rowid,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': '未找到该学生'}), 404

        db_id = row['id'] if 'id' in row.keys() else None
        db_class = row['class_id'] if 'class_id' in row.keys() else None

        if str(db_class) != str(class_id):
            conn.close()
            return jsonify({'error': '班级ID不匹配，无法删除'}), 403

        # 尝试删除关联评论
        try:
            # 如果学生有 id 值则用之，否则删除 student_id 为空或 NULL 的评论（可能与该记录相关）
            if db_id:
                cursor.execute('DELETE FROM comments WHERE student_id = ?', (db_id,))
            else:
                cursor.execute("DELETE FROM comments WHERE student_id IS NULL OR student_id = ''")
        except Exception as e:
            logger.warning(f"删除相关评语时出错（继续尝试删除学生）: {str(e)}")

        # 删除学生记录（使用 rowid）
        try:
            cursor.execute('PRAGMA foreign_keys = OFF')
            cursor.execute('DELETE FROM students WHERE rowid = ?', (rowid,))
            conn.commit()
        finally:
            try:
                cursor.execute('PRAGMA foreign_keys = ON')
            except Exception:
                logger.warning('重新启用 PRAGMA foreign_keys 时出错')

        conn.close()
        return jsonify({'message': '学生删除成功', 'data_changed': True, 'timestamp': datetime.datetime.now().timestamp()})

    except Exception as e:
        logger.exception(f"根据 rowid 删除学生时出错: {str(e)}")
        try:
            if 'conn' in locals() and conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return jsonify({'error': f'删除学生失败: {str(e)}'}), 500


@students_bp.route('/api/student-by-rowid/<int:rowid>', methods=['GET'])
@login_required
def get_student_by_rowid(rowid):
    """根据 rowid 获取学生详情（用于处理无学号的记录）。"""
    try:
        class_id = request.args.get('class_id')
        if not class_id:
            return jsonify({'error': '缺少班级ID'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT rowid, s.*, c.class_name FROM students s LEFT JOIN classes c ON s.class_id = c.id WHERE rowid = ? AND s.class_id = ?', (rowid, class_id))
        student = cursor.fetchone()
        if not student:
            conn.close()
            return jsonify({'error': '未找到该学生'}), 404

        student_dict = dict(student)

        # 处理数值字段
        numeric_fields = ['height', 'weight', 'chest_circumference', 'vital_capacity', 'vision_left', 'vision_right']
        for field in numeric_fields:
            if field in student_dict and student_dict[field] is not None:
                try:
                    student_dict[field] = float(student_dict[field])
                except Exception:
                    pass

        conn.close()
        return jsonify(student_dict)
    except Exception as e:
        logger.exception(f"根据 rowid 获取学生详情时出错: {str(e)}")
        try:
            if 'conn' in locals() and conn:
                conn.close()
        except Exception:
            pass
        return jsonify({'error': f'获取学生详情失败: {str(e)}'}), 500

# 定义成绩等级和德育维度分数限制
VALID_GRADES = ['优', '良', '及格', '待及格', '/']

DEYU_SCORE_LIMITS = {
    'pinzhi': 30,    # 品德修养
    'xuexi': 20,     # 学习素养
    'jiankang': 20,  # 身心健康
    'shenmei': 10,   # 审美素养
    'shijian': 10,   # 实践创新
    'shenghuo': 10   # 生活素养
}
DEYU_TOTAL_LIMIT = 100

def validate_grade(value):
    """验证成绩等级"""
    if not value:
        return True, None  # 允许为空
    if value not in VALID_GRADES:
        return False, f"成绩必须是：{', '.join(VALID_GRADES)}中的一个"
    return True, None

def validate_deyu_score(field, value):
    """验证德育维度分数"""
    # 数据库字段名到显示名称的映射
    field_display_names = {
        'pinzhi': '品质',
        'xuexi': '学习',
        'jiankang': '健康',
        'shenmei': '审美',
        'shijian': '实践',
        'shenghuo': '生活'
    }
    
    display_name = field_display_names.get(field, field)
    
    if not value and value != 0:
        return True, None  # 允许德育分数为空
    try:
        score = int(value)
        if score < 0:
            return False, f"{display_name}分数不能为负"
        if score > DEYU_SCORE_LIMITS[field]:
            return False, f"{display_name}分数不能超过{DEYU_SCORE_LIMITS[field]}"
        return True, None
    except (ValueError, TypeError):
        return False, f"{display_name}分数必须是整数"

def validate_deyu_total(scores):
    """验证德育维度总分"""
    total = sum(int(score) for score in scores.values() if score)
    if total > DEYU_TOTAL_LIMIT:
        return False, f"德育维度总分不能超过{DEYU_TOTAL_LIMIT}分，当前总分：{total}"
    return True, None

def validate_comment(value):
    """验证评语"""
    if not value:
        return True, None  # 允许评语为空
    if len(value) > 260:
        return False, "评语不能超过260个字"
    return True, None

def get_field_changes(existing_data, new_data):
    """获取字段更改信息"""
    changes = []
    for field, new_value in new_data.items():
        if field in existing_data:
            old_value = existing_data[field]
            if (old_value != new_value and 
                (old_value is not None or new_value is not None)):  # 处理NULL值的比较
                changes.append({
                    'field': field,
                    'old_value': old_value,
                    'new_value': new_value
                })
    return changes

# 导入学生预览API
@students_bp.route('/api/import-students', methods=['POST'])
@login_required
def import_students_preview():
    """预览导入学生数据"""
    try:
        # 如果是班主任且没有分配班级，不允许导入学生
        if not current_user.is_admin and not current_user.class_id:
            logger.warning(f"班主任 {current_user.username} 未分配班级，不能导入学生")
            return jsonify({'error': '您尚未被分配班级，无法导入学生'}), 403
            
        # 获取上传的文件
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
            
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': '请上传Excel文件'}), 400
        
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 如果是班主任，获取对应的班级信息用于验证
        teacher_class_name = None
        if not current_user.is_admin and current_user.class_id:
            cursor.execute('SELECT class_name FROM classes WHERE id = ?', (current_user.class_id,))
            teacher_class_result = cursor.fetchone()
            teacher_class_name = teacher_class_result['class_name'] if teacher_class_result else None
            
            if not teacher_class_name:
                return jsonify({'error': '无法获取您负责的班级信息，请联系管理员'}), 400
            
        # 保存文件
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 确保上传目录存在
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # 尝试保存文件
        try:
            file.save(file_path)
            logger.info(f"文件已保存到: {file_path}")
        except Exception as e:
            logger.error(f"保存文件时出错: {str(e)}")
            return jsonify({'error': f'保存文件失败: {str(e)}'}), 500
        
        # 读取Excel文件
        try:
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active
        except Exception as e:
            logger.error(f"读取Excel文件时出错: {str(e)}")
            return jsonify({'error': f'读取Excel文件失败: {str(e)}'}), 500
        
        # 获取表头
        headers = [cell.value for cell in ws[1]]
        
        # 准备数据
        students_data = []
        error_records = []
        skipped_count = 0
        updated_count = 0
        added_count = 0
        class_mismatch_count = 0
        all_classes_match = True  # 标记是否所有班级都匹配
        
        # 字段映射表，Excel列名 -> 数据库字段名
        field_mapping = {
            '学号': 'id',
            '姓名': 'name',
            '性别': 'gender',
            '班级': 'class',
            '身高(cm)': 'height',
            '身高': 'height',
            '体重(kg)': 'weight',
            '体重': 'weight',
            '胸围(cm)': 'chest_circumference',
            '胸围': 'chest_circumference',
            '肺活量(ml)': 'vital_capacity',
            '肺活量': 'vital_capacity',
            '龋齿(个)': 'dental_caries',
            '龋齿': 'dental_caries',
            '视力左': 'vision_left',
            '视力右': 'vision_right',
            '体测情况': 'physical_test_status',
            # 学科成绩
            '语文': 'yuwen',
            '数学': 'shuxue',
            '英语': 'yingyu',
            '劳动': 'laodong',
            '体育': 'tiyu',
            '音乐': 'yinyue',
            '美术': 'meishu',
            '科学': 'kexue',
            '综合': 'zonghe',
            '信息': 'xinxi',
            '书法': 'shufa',
            '心理': 'xinli',
            # 德育维度
            '品质': 'pinzhi',
            '学习': 'xuexi',
            '健康': 'jiankang',
            '审美': 'shenmei',
            '实践': 'shijian',
            '生活': 'shenghuo',
            # 其他
            '评语': 'comments'
        }
        
        # 处理每一行数据
        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            student = {}
            
            # 处理每个单元格
            deyu_scores = {}  # 用于存储德育维度分数
            validation_errors = []  # 用于存储验证错误
            
            for header, cell in zip(headers, row):
                cell_value = cell.value
                field_name = field_mapping.get(header)
                
                if field_name:
                    # 验证成绩格式
                    if field_name in ['yuwen', 'shuxue', 'yingyu', 'laodong', 'tiyu', 
                                    'yinyue', 'meishu', 'kexue', 'zonghe', 'xinxi', 
                                    'shufa', 'xinli']:
                        is_valid, error = validate_grade(cell_value)
                        if not is_valid:
                            validation_errors.append(f"{header}: {error}")
                            continue
                            
                    # 验证德育维度分数
                    elif field_name in ['pinzhi', 'xuexi', 'jiankang', 'shenmei', 
                                      'shijian', 'shenghuo']:
                        is_valid, error = validate_deyu_score(field_name, cell_value)
                        if not is_valid:
                            validation_errors.append(f"{header}: {error}")
                            continue
                        deyu_scores[field_name] = cell_value
                        
                    # 验证评语
                    elif field_name == 'comments':
                        is_valid, error = validate_comment(cell_value)
                        if not is_valid:
                            validation_errors.append(f"{header}: {error}")
                            continue
                            
                    # 数值字段处理
                    if field_name in ['height', 'weight', 'chest_circumference', 'vital_capacity', 
                                    'vision_left', 'vision_right']:
                        try:
                            if cell_value is not None and cell_value != '' and cell_value != '-':
                                student[field_name] = float(cell_value)
                            else:
                                student[field_name] = None
                        except (ValueError, TypeError):
                            student[field_name] = None
                            logger.warning(f"行 {row_idx}: '{header}' 值 '{cell_value}' 无法转换为数值")
                    else:
                        # 文本字段处理
                        if cell_value is not None and cell_value != '' and cell_value != '-':
                            student[field_name] = str(cell_value)
                        else:
                            student[field_name] = None
            
            # 检查必填字段 - 只需要姓名和班级
            if not student.get('name'):
                error_records.append({
                    'row': row_idx,
                    'reason': '姓名为空'
                })
                skipped_count += 1
                continue
            
            # 如果是班主任，检查Excel中的班级字段是否与班主任的班级匹配（支持智能匹配）
            if not current_user.is_admin and current_user.class_id:
                # 检查Excel中的班级字段是否与班主任的班级一致
                excel_class_name = student.get('class')
                
                if excel_class_name:
                    # 尝试标准化Excel中的班级名称
                    normalized_excel_class, success = normalize_class_name(excel_class_name)
                    
                    # 记录标准化信息
                    if success and normalized_excel_class != excel_class_name:
                        logger.info(f"行 {row_idx}: 班级名称 '{excel_class_name}' 已标准化为 '{normalized_excel_class}'")
                        student['class_normalized'] = normalized_excel_class
                        student['class_original'] = excel_class_name
                    
                    # 使用标准化后的名称进行比较
                    compare_class_name = normalized_excel_class if success else excel_class_name
                    
                    if teacher_class_name and compare_class_name != teacher_class_name:
                        # 班级不匹配
                        student['class_mismatch'] = True
                        student['teacher_class'] = teacher_class_name
                        if success and normalized_excel_class != excel_class_name:
                            student['error_reason'] = f'班级不匹配: Excel中为"{excel_class_name}"（标准化为"{normalized_excel_class}"），您的班级是"{teacher_class_name}"'
                        else:
                            student['error_reason'] = f'班级不匹配: Excel中为"{excel_class_name}", 您的班级是"{teacher_class_name}"'
                        # 记录错误信息
                        error_records.append({
                            'row': row_idx,
                            'reason': student['error_reason']
                        })
                        # 增加不匹配计数
                        class_mismatch_count += 1
                        # 标记整体状态为不匹配
                        all_classes_match = False
                        skipped_count += 1
                        continue
                    else:
                        # 班级匹配，更新student中的class为标准化后的名称
                        if success and normalized_excel_class:
                            student['class'] = normalized_excel_class
                else:
                    # Excel中没有班级信息，使用班主任的班级
                    student['class'] = teacher_class_name
                
                student['class_id'] = current_user.class_id
            else:
                # 管理员模式：根据班级名称查找班级ID（支持智能匹配）
                if student.get('class'):
                    class_id, normalized_name, error_msg = find_class_id_by_name(cursor, student['class'])
                    
                    if class_id:
                        student['class_id'] = class_id
                        # 如果班级名称被标准化了，记录下来
                        if normalized_name != student['class']:
                            student['class_normalized'] = normalized_name
                            student['class_original'] = student['class']
                            logger.info(f"班级名称 '{student['class']}' 已标准化为 '{normalized_name}'")
                    else:
                        error_records.append({
                            'row': row_idx,
                            'reason': error_msg
                        })
                        skipped_count += 1
                        continue
                else:
                    error_records.append({
                        'row': row_idx,
                        'reason': '班级信息缺失'
                    })
                    skipped_count += 1
                    continue
            
            # 检查学生是否已存在（使用姓名+班级ID匹配）
            cursor.execute('SELECT id, name FROM students WHERE name = ? AND class_id = ?', 
                          (student['name'], student['class_id']))
            existing_student_record = cursor.fetchone()
            
            if existing_student_record:
                # 学生已存在，记录数据库中的学号
                db_student_id = existing_student_record['id']
                
                # 如果Excel中有学号，使用Excel的学号；否则使用数据库的学号
                if student.get('id'):
                    student['final_id'] = student['id']
                    student['id_changed'] = (student['id'] != db_student_id)
                else:
                    student['final_id'] = db_student_id
                    student['id'] = db_student_id
                    student['id_changed'] = False
                
                updated_count += 1
                
                # 查询数据库中已有的学生信息，用于字段比对
                cursor.execute('''
                    SELECT id, name, gender, height, weight, chest_circumference, vital_capacity, 
                           vision_left, vision_right, dental_caries, physical_test_status,
                           yuwen, shuxue, yingyu, laodong, tiyu, yinyue, meishu, kexue,
                           zonghe, xinxi, shufa, xinli,
                           pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo,
                           comments
                    FROM students 
                    WHERE name = ? AND class_id = ?
                ''', (student['name'], student['class_id']))
                existing_data = cursor.fetchone()
                
                if existing_data:
                    # 转换为字典
                    existing_student = dict(existing_data)
                    
                    # 添加需要更新的字段信息
                    student['fields_to_update'] = []
                    student['fields_unchanged'] = []
                    
                    # 比对各个字段
                    fields_to_compare = [
                        ('id', '学号'),
                        ('name', '姓名'),
                        ('gender', '性别'),
                        ('height', '身高'), 
                        ('weight', '体重'), 
                        ('chest_circumference', '胸围'), 
                        ('vital_capacity', '肺活量'),
                        ('vision_left', '视力左'), 
                        ('vision_right', '视力右'), 
                        ('dental_caries', '龋齿'),
                        # 学科成绩
                        ('yuwen', '语文'),
                        ('shuxue', '数学'),
                        ('yingyu', '英语'),
                        ('laodong', '劳动'),
                        ('tiyu', '体育'),
                        ('yinyue', '音乐'),
                        ('meishu', '美术'),
                        ('kexue', '科学'),
                        ('zonghe', '综合'),
                        ('xinxi', '信息'),
                        ('shufa', '书法'),
                        ('xinli', '心理'),
                        # 德育维度
                        ('pinzhi', '品质'),
                        ('xuexi', '学习'),
                        ('jiankang', '健康'),
                        ('shenmei', '审美'),
                        ('shijian', '实践'),
                        ('shenghuo', '生活'),
                        # 其他
                        ('comments', '评语'),
                        ('physical_test_status', '体测情况')
                    ]
                    
                    for field, display_name in fields_to_compare:
                        # 只比对Excel中有值的字段
                        if field in student and student[field] is not None:
                            # 数值字段比较
                            if field in ['height', 'weight', 'chest_circumference', 'vital_capacity', 
                                      'vision_left', 'vision_right']:
                                # 获取数据库中的值，确保是浮点数
                                db_value = existing_student.get(field)
                                if db_value is not None:
                                    try:
                                        db_value = float(db_value)
                                    except (ValueError, TypeError):
                                        db_value = None
                                
                                # 比较值
                                if db_value != student[field]:
                                    student['fields_to_update'].append({
                                        'field': field,
                                        'display_name': display_name,
                                        'old_value': db_value,
                                        'new_value': student[field]
                                    })
                                else:
                                    student['fields_unchanged'].append({
                                        'field': field,
                                        'display_name': display_name,
                                        'value': student[field]
                                    })
                            else:
                                # 非数值字段比较
                                db_value = existing_student.get(field)
                                # 特殊处理学号字段
                                if field == 'id':
                                    # 如果Excel中有学号且与数据库不同，标记为更新
                                    if student.get('id') and student['id'] != db_value:
                                        student['fields_to_update'].append({
                                            'field': field,
                                            'display_name': display_name,
                                            'old_value': db_value,
                                            'new_value': student['id']
                                        })
                                    else:
                                        student['fields_unchanged'].append({
                                            'field': field,
                                            'display_name': display_name,
                                            'value': db_value
                                        })
                                elif db_value != student[field]:
                                    student['fields_to_update'].append({
                                        'field': field,
                                        'display_name': display_name,
                                        'old_value': db_value,
                                        'new_value': student[field]
                                    })
                                else:
                                    student['fields_unchanged'].append({
                                        'field': field,
                                        'display_name': display_name,
                                        'value': student[field]
                                    })
            else:
                # 新增学生
                added_count += 1
                # 如果Excel中没有学号，需要生成一个
                if not student.get('id'):
                    # 查询该班级最大的学号
                    cursor.execute('SELECT MAX(CAST(id AS INTEGER)) as max_id FROM students WHERE class_id = ?', 
                                 (student['class_id'],))
                    max_id_result = cursor.fetchone()
                    max_id = max_id_result['max_id'] if max_id_result and max_id_result['max_id'] else 0
                    student['id'] = str(max_id + 1)
                    student['final_id'] = student['id']
                    student['id_auto_generated'] = True
                else:
                    student['final_id'] = student['id']
                    student['id_auto_generated'] = False
                
            students_data.append(student)
        
        # 成功读取数据后，不删除文件，确保导入过程中文件可用
        # 注意: 稍后需要在确认导入后或一段时间后清理这些文件
        
        logger.info(f"成功解析Excel文件，发现 {len(students_data)} 条有效学生记录")
        
        if class_mismatch_count > 0:
            logger.warning(f"Excel中有 {class_mismatch_count} 条班级不匹配记录")
        
        return jsonify({
            'status': 'ok',
            'message': f'成功读取 {len(students_data)} 条学生记录',
            'preview': {
                'total': len(students_data),
                'added': added_count,
                'updated': updated_count,
                'skipped': skipped_count,
                'class_mismatch_count': class_mismatch_count,
                'errors': error_records,
                'all_classes_match': all_classes_match,  # 添加标志表示是否所有班级都匹配
                'validation_rule': '严格验证：当Excel中存在任何班级不匹配的记录时，整个Excel都无法导入。' # 添加验证规则说明
            },
            'students': students_data,
            'file_path': file_path  # 返回文件路径以供后续使用
        })
        
    except Exception as e:
        logger.error(f"导入学生预览时出错: {str(e)}")
        return jsonify({'error': f'导入预览失败: {str(e)}'}), 500

@students_bp.route('/api/confirm-import', methods=['POST'])
@login_required
def confirm_import():
    """确认导入学生数据"""
    try:
        # 如果是班主任且没有分配班级，不允许导入学生
        if not current_user.is_admin and not current_user.class_id:
            logger.warning(f"班主任 {current_user.username} 未分配班级，不能确认导入学生")
            return jsonify({'error': '您尚未被分配班级，无法导入学生'}), 403
            
        # 获取JSON数据
        data = request.get_json()
        if not data or 'students' not in data:
            return jsonify({'error': '无效的数据格式'}), 400
            
        students = data['students']
        if not students:
            return jsonify({'error': '没有要导入的学生数据'}), 400
            
        # 检查是否存在班级不匹配的记录 - 严格规则：存在任何不匹配就拒绝整个导入
        if not current_user.is_admin:
            class_mismatch_found = any(student.get('class_mismatch', False) for student in students)
            if class_mismatch_found:
                mismatch_count = sum(1 for student in students if student.get('class_mismatch', False))
                logger.warning(f"拒绝导入：检测到 {mismatch_count} 条班级不匹配的记录")
                return jsonify({
                    'status': 'error',
                    'message': f'拒绝导入：Excel中存在 {mismatch_count} 条班级不匹配的记录。',
                    'class_mismatch_count': mismatch_count
                }), 400
            
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取当前时间
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 获取数据库列名
        cursor.execute("PRAGMA table_info(students)")
        db_columns = [row[1] for row in cursor.fetchall()]
        
        # 准备统计
        inserted_count = 0
        updated_count = 0
        error_count = 0
        error_details = []
        class_mismatch_count = 0
        
        # 遍历学生数据，执行插入或更新
        for student in students:
            try:
                # 提取班级ID和学生ID
                class_id = student.get('class_id')
                student_id = student.get('id')
                
                if not class_id or not student_id:
                    error_count += 1
                    error_details.append(f"学生 {student.get('name', '未知')} (ID: {student_id or '未知'}) 缺少班级ID或学生ID")
                    continue
                
                # 检查班级不匹配的情况（针对班主任）
                if not current_user.is_admin and 'class_mismatch' in student and student['class_mismatch']:
                    error_count += 1
                    class_mismatch_count += 1
                    error_details.append(f"学生 {student.get('name', '未知')} (ID: {student_id}) {student.get('error_reason', '班级不匹配')}")
                    continue
                
                # 检查该学生是否已存在（使用姓名+班级ID匹配）
                student_name = student.get('name')
                if not student_name:
                    error_count += 1
                    error_details.append(f"学生 (ID: {student_id}) 缺少姓名")
                    continue
                
                cursor.execute('SELECT id FROM students WHERE name = ? AND class_id = ?', 
                            (student_name, class_id))
                existing_student = cursor.fetchone()
                
                # 如果学生已存在，使用数据库中的学号（除非Excel中提供了新学号）
                if existing_student:
                    db_student_id = existing_student['id']
                    # 如果Excel中有学号且与数据库不同，使用Excel的学号
                    if student_id and student_id != db_student_id:
                        # 需要更新学号
                        final_student_id = student_id
                    else:
                        # 使用数据库的学号
                        final_student_id = db_student_id
                else:
                    # 新学生，使用Excel的学号或生成新学号
                    if not student_id:
                        # 生成新学号
                        cursor.execute('SELECT MAX(CAST(id AS INTEGER)) as max_id FROM students WHERE class_id = ?', 
                                     (class_id,))
                        max_id_result = cursor.fetchone()
                        max_id = max_id_result['max_id'] if max_id_result and max_id_result['max_id'] else 0
                        final_student_id = str(max_id + 1)
                    else:
                        final_student_id = student_id
                
                # 更新student字典中的id
                student['id'] = final_student_id
                
                # 准备数据，只包含数据库存在的列
                db_fields = []
                db_values = []
                update_pairs = []
                
                for key, value in student.items():
                    if key in db_columns:
                        db_fields.append(key)
                        db_values.append(value)
                        update_pairs.append(f"{key} = ?")
                
                # 添加创建和更新时间
                if 'created_at' in db_columns and not existing_student:
                    db_fields.append('created_at')
                    db_values.append(now)
                
                if 'updated_at' in db_columns:
                    db_fields.append('updated_at')
                    db_values.append(now)
                
                # 执行SQL
                if existing_student:
                    # 更新现有学生
                    # 只更新与数据库中不一致的字段
                    if 'fields_to_update' in student and student['fields_to_update']:
                        # 如果有需要更新的字段，只更新那些字段
                        update_fields = []
                        update_values = []
                        
                        for field_info in student['fields_to_update']:
                            field_name = field_info['field']
                            if field_name in db_columns:
                                update_fields.append(f"{field_name} = ?")
                                update_values.append(student[field_name])
                        
                        # 添加更新时间
                        if 'updated_at' in db_columns:
                            update_fields.append('updated_at = ?')
                            update_values.append(now)
                        
                        # 如果有需要更新的字段，执行更新
                        if update_fields:
                            query = f"UPDATE students SET {', '.join(update_fields)} WHERE id = ? AND class_id = ?"
                            cursor.execute(query, update_values + [student_id, class_id])
                            updated_count += 1
                        else:
                            # 如果没有需要更新的字段，跳过更新
                            logger.info(f"学生 {student_id} 无需更新任何字段")
                    else:
                        # 向后兼容，如果没有fields_to_update字段，执行原有逻辑
                        query = f"UPDATE students SET {', '.join(update_pairs)} WHERE id = ? AND class_id = ?"
                        cursor.execute(query, db_values + [student_id, class_id])
                        updated_count += 1
                else:
                    # 插入新学生
                    placeholders = ', '.join(['?'] * len(db_fields))
                    query = f"INSERT INTO students ({', '.join(db_fields)}) VALUES ({placeholders})"
                    cursor.execute(query, db_values)
                    inserted_count += 1
                
            except Exception as e:
                logger.error(f"导入学生 {student.get('id', '未知')} 时出错: {str(e)}")
                error_count += 1
                error_details.append(f"学生 {student.get('name', '未知')} (ID: {student.get('id', '未知')}) 导入失败: {str(e)}")
        
        # 提交事务
        conn.commit()
        conn.close()
        
        # 清理临时文件（可选）
        # 注意：这里不再尝试删除可能不存在的文件
        
        # 生成响应
        success_count = inserted_count + updated_count
        status = 'ok' if error_count == 0 else 'partial' if success_count > 0 else 'error'
        
        logger.info(f"导入完成: 成功 {success_count} 条 (新增 {inserted_count}, 更新 {updated_count}), 失败 {error_count} 条")
        
        if class_mismatch_count > 0:
            logger.warning(f"跳过了 {class_mismatch_count} 条班级不匹配的记录")
        
        return jsonify({
            'status': status,
            'message': f'完成导入 {success_count} 条记录',
            'success_count': success_count,
            'inserted_count': inserted_count,
            'updated_count': updated_count,
            'error_count': error_count,
            'class_mismatch_count': class_mismatch_count,
            'error_details': error_details
        })
        
    except Exception as e:
        logger.error(f"确认导入学生时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'确认导入失败: {str(e)}'}), 500

# 下载模板API
@students_bp.route('/api/template', methods=['GET'])
def download_template():
    # 检查是否是班主任
    is_teacher = not current_user.is_admin and current_user.class_id
    
    if is_teacher:
        # 为班主任生成班级特定的模板
        from create_student_template import create_custom_template
        
        try:
            # 获取班级ID
            class_id = current_user.class_id
            
            # 创建自定义模板
            template_path = create_custom_template(class_id)
            
            if template_path:
                # 获取文件名
                template_filename = os.path.basename(template_path)
                return jsonify({
                    'status': 'ok',
                    'message': '已生成您班级专用的导入模板',
                    'template_url': f'/download/template/{template_filename}'
                })
            else:
                # 如果自定义模板创建失败，回退到标准模板
                logger.warning(f"班主任 {current_user.username} 的自定义模板创建失败，使用标准模板")
        except Exception as e:
            logger.error(f"创建自定义模板时出错: {str(e)}")
    
    # 通用模板（管理员或自定义模板失败的情况）
    template_path = os.path.join(TEMPLATE_FOLDER, 'student_template.xlsx')
    if not os.path.exists(template_path):
        create_student_template()
    
    return jsonify({
        'status': 'ok',
        'message': '已生成通用导入模板',
        'template_url': f'/download/template/student_template.xlsx'
    })

# 提供模板下载
@students_bp.route('/download/template/<filename>', methods=['GET'])
def serve_template(filename):
    return send_from_directory(TEMPLATE_FOLDER, filename)

@students_bp.route('/api/students/<student_id>/update-subject', methods=['POST'])
@login_required
def update_student_subject(student_id):
    """更新学生的单个或多个学科成绩"""
    try:
        # 获取JSON数据
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '无效的数据格式'})
        
        logger.info(f"正在更新学生ID={student_id}的学科成绩: {data}")
        
        # 获取当前用户班级ID
        user_class_id = current_user.class_id if not current_user.is_admin else None
        
        # 如果是班主任且没有分配班级，不允许更新学生成绩
        if not current_user.is_admin and not user_class_id:
            logger.warning(f"班主任 {current_user.username} 未分配班级，不能更新学生成绩")
            return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法更新学生成绩'})
        
        # 检查学生是否存在，并验证班级ID
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询学生时需要同时检查学生ID和班级ID
        if user_class_id:
            # 班主任只能修改自己班级的学生
            cursor.execute('SELECT * FROM students WHERE id = ? AND class_id = ?', (student_id, user_class_id))
        else:
            # 管理员可以修改任意学生，但仍需要查询该学生
            cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
            
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            if user_class_id:
                # 如果是班主任，提示可能是权限问题
                return jsonify({
                    'status': 'error', 
                    'message': f'找不到ID为{student_id}的学生，或该学生不在您负责的班级中'
                })
            else:
                return jsonify({'status': 'error', 'message': f'找不到ID为{student_id}的学生'})
        
        # 支持的学科列表
        subjects = ['daof', 'yuwen', 'shuxue', 'yingyu', 'laodong', 'tiyu', 
                   'yinyue', 'meishu', 'kexue', 'zonghe', 'xinxi', 'shufa']
        
        # 学科到显示名称的映射，用于日志
        subject_display_names = {
            'daof': '道法', 'yuwen': '语文', 'shuxue': '数学', 'yingyu': '英语',
            'laodong': '劳动', 'tiyu': '体育', 'yinyue': '音乐', 'meishu': '美术',
            'kexue': '科学', 'zonghe': '综合', 'xinxi': '信息技术', 'shufa': '书法'
        }
        
        # 验证有效的成绩等级
        valid_grades = ['优', '良', '及格', '待及格', '']
        
        # 记录更新了多少个学科
        updated_count = 0
        
        # 遍历提交的数据，更新各个学科的成绩
        for subject, value in data.items():
            if subject in subjects:
                # 验证成绩值是否有效
                if value not in valid_grades:
                    logger.warning(f"尝试设置无效的成绩值: subject={subject}, value={value}")
                    continue
                
                # 更新数据库中的成绩，同时确保只更新特定班级的学生
                try:
                    if user_class_id:
                        # 班主任：使用ID和班级ID的组合查询条件
                        cursor.execute(f"UPDATE students SET {subject} = ? WHERE id = ? AND class_id = ?", 
                                      (value, student_id, user_class_id))
                    else:
                        # 管理员：仅使用ID查询条件
                        cursor.execute(f"UPDATE students SET {subject} = ? WHERE id = ?", 
                                      (value, student_id))
                                      
                    updated_count += 1
                    logger.info(f"已更新学生{student_id}的{subject_display_names.get(subject, subject)}成绩为: {value}")
                except Exception as e:
                    logger.error(f"更新科目成绩出错: {str(e)}")
        
        # 保存更改
        if updated_count > 0:
            # 更新修改时间，同样需要确保只更新特定班级的学生
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if user_class_id:
                cursor.execute('UPDATE students SET updated_at = ? WHERE id = ? AND class_id = ?', 
                              (now, student_id, user_class_id))
            else:
                cursor.execute('UPDATE students SET updated_at = ? WHERE id = ?', 
                              (now, student_id))
                              
            conn.commit()
            logger.info(f"成功保存学生{student_id}的{updated_count}个学科成绩")
            return jsonify({'status': 'ok', 'message': f'成功更新{updated_count}个学科成绩'})
        else:
            conn.close()
            return jsonify({'status': 'warning', 'message': '没有发现要更新的学科成绩'})
    
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
        error_msg = f"更新学生学科成绩时出错: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({'status': 'error', 'message': error_msg})

@students_bp.route('/api/students', methods=['GET'])
@login_required
def get_students():
    """获取学生列表，支持按班级筛选"""
    try:
        # 获取请求参数
        class_id = request.args.get('class_id')
        with_grades = request.args.get('with_grades', 'false').lower() == 'true'
        
        # 获取当前用户信息
        current_user_id = current_user.id
        current_user_class_id = current_user.class_id
        is_admin = current_user.is_admin
        
        # 记录日志
        logger.info(f"获取学生列表请求: user={current_user.username}, class_id参数={class_id}, 用户班级={current_user_class_id}")
        
        # 非管理员且未分配班级的班主任不能看到任何学生
        if not is_admin and not current_user_class_id:
            logger.warning(f"班主任 {current_user.username} 未分配班级，不能查看任何学生")
            return jsonify({
                'status': 'ok',
                'students': [],
                'total': 0,
                'message': '您尚未被分配班级，无法查看学生信息'
            })
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 非管理员只能查看自己负责班级的学生
        if not is_admin and current_user_class_id:
            logger.info(f"班主任查询自己班级 {current_user_class_id} 的学生")
            cursor.execute('''
                SELECT s.rowid AS rowid, s.*, c.class_name 
                FROM students s 
                LEFT JOIN classes c ON s.class_id = c.id 
                WHERE s.class_id = ? 
                ORDER BY CAST(s.id AS INTEGER)
            ''', (current_user_class_id,))
        # 如果指定了班级ID，则按班级筛选
        elif class_id:
            # 尝试处理整数或字符串的班级ID
            try:
                # 尝试转为整数
                int_class_id = int(class_id)
                logger.info(f"以数字形式查询班级ID: {int_class_id}")
                cursor.execute('''
                    SELECT s.rowid AS rowid, s.*, c.class_name 
                    FROM students s 
                    LEFT JOIN classes c ON s.class_id = c.id 
                    WHERE s.class_id = ? 
                    ORDER BY CAST(s.id AS INTEGER)
                ''', (int_class_id,))
            except (ValueError, TypeError):
                # 如果无法转为整数，尝试按班级名称查询
                logger.info(f"尝试以班级名称查询: {class_id}")
                cursor.execute('''
                    SELECT s.rowid AS rowid, s.*, c.class_name 
                    FROM students s 
                    LEFT JOIN classes c ON s.class_id = c.id 
                    WHERE s.class_id = ? 
                    ORDER BY CAST(s.id AS INTEGER)
                ''', (class_id,))
            
            # 检查结果数量
            students = cursor.fetchall()
            if not students:
                # 不再支持模糊匹配，因为数据库中没有class字段
                logger.info(f"未找到班级ID: {class_id}，返回空结果")
                students = []
            else:
                # 重置游标位置
                cursor.execute('''
                    SELECT s.rowid AS rowid, s.*, c.class_name 
                    FROM students s 
                    LEFT JOIN classes c ON s.class_id = c.id 
                    WHERE s.class_id = ? 
                    ORDER BY CAST(s.id AS INTEGER)
                ''', (int_class_id,))
        else:
            logger.info("管理员查询所有学生")
            cursor.execute('''
                SELECT s.rowid AS rowid, s.*, c.class_name 
                FROM students s 
                LEFT JOIN classes c ON s.class_id = c.id 
                ORDER BY CAST(s.id AS INTEGER)
            ''')
        
        students = [dict(row) for row in cursor.fetchall()]
        logger.info(f"查询结果: 找到 {len(students)} 名学生")
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'students': students,
            'total': len(students)
        })
        
    except Exception as e:
        logger.error(f"获取学生列表时出错: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'获取学生列表失败: {str(e)}'}) 

# 清除学生名单API
@students_bp.route('/api/clear-students', methods=['DELETE'], strict_slashes=False)
@login_required
def clear_all_students():
    """清除班级所有学生数据"""
    try:
        # 从请求中获取班级ID
        data = request.json
        class_id = data.get('class_id') if data else None
        
        # 班主任只能清除自己班级的学生
        if not current_user.is_admin:
            # 如果班主任没有被分配班级，则返回错误
            if not current_user.class_id:
                logger.warning(f"班主任 {current_user.username} 未分配班级，无法清除学生名单")
                return jsonify({
                    'status': 'error',
                    'message': '您尚未被分配班级，无法清除学生名单'
                }), 403
            
            # 使用班主任的班级ID，忽略请求中的班级ID
            class_id = current_user.class_id
        
        # 如果是管理员且没有提供班级ID，则返回错误
        if current_user.is_admin and not class_id:
            return jsonify({
                'status': 'error',
                'message': '管理员必须指定要清除的班级ID'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 开始事务
            conn.execute('BEGIN TRANSACTION')
            
            # 记录操作前的学生数量
            cursor.execute('SELECT COUNT(*) FROM students WHERE class_id = ?', (class_id,))
            student_count_before = cursor.fetchone()[0]
            
            if student_count_before == 0:
                return jsonify({
                    'status': 'ok',
                    'message': '班级中没有学生，无需清除',
                    'count': 0
                })
            
            # 先删除依赖表中的相关数据以避免外键冲突（例如 comments 表）
            try:
                cursor.execute('DELETE FROM comments WHERE student_id IN (SELECT id FROM students WHERE class_id = ?)', (class_id,))
                logger.debug('已删除该班级关联的 comments 记录')
            except Exception as e:
                # 记录警告但继续尝试删除学生（有时外键定义不一致）
                logger.warning(f"删除关联 comments 记录时出错: {e}")

            # 删除指定班级的所有学生
            # 为了应对可能的 foreign key mismatch 问题，短暂关闭外键检查再执行删除
            try:
                cursor.execute('PRAGMA foreign_keys = OFF')
            except Exception:
                logger.warning('无法关闭 PRAGMA foreign_keys')

            cursor.execute('DELETE FROM students WHERE class_id = ?', (class_id,))
            try:
                cursor.execute('PRAGMA foreign_keys = ON')
            except Exception:
                logger.warning('无法重新启用 PRAGMA foreign_keys')
            
            # 提交事务
            conn.commit()
            
            logger.info(f"成功清除班级 {class_id} 的所有学生数据，共删除 {student_count_before} 条记录")
            
            return jsonify({
                'status': 'ok',
                'message': f'成功清除班级所有学生数据，共删除 {student_count_before} 条记录',
                'count': student_count_before
            })
            
        except Exception as e:
            # 回滚事务
            conn.rollback()
            logger.error(f"清除学生名单时出错: {str(e)}")
            return jsonify({'status': 'error', 'message': f'清除学生名单失败: {str(e)}'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"清除学生名单API出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'清除学生名单失败: {str(e)}'}), 500 


@students_bp.route('/api/cleanup-students', methods=['POST'])
@login_required
def cleanup_students():
    """删除某个班级中没有学号（id 为空或 NULL）的学生记录，并尝试删除相关评论。"""
    try:
        data = request.get_json()
        class_id = data.get('class_id') if data else None

        # 班主任只能操作自己班级
        if not current_user.is_admin:
            if not current_user.class_id:
                return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法执行清理'}), 403
            class_id = current_user.class_id

        if current_user.is_admin and not class_id:
            return jsonify({'status': 'error', 'message': '管理员必须提供要清理的班级ID (class_id)'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 统计待删除记录数
        cursor.execute("SELECT COUNT(*) FROM students WHERE (id IS NULL OR id = '') AND class_id = ?", (class_id,))
        row = cursor.fetchone()
        to_delete = row[0] if row else 0

        if to_delete == 0:
            conn.close()
            return jsonify({'status': 'ok', 'message': '没有需要清理的学生', 'deleted': 0})

        # 删除相关 comments（以 students.id 为关联字段）
        try:
            cursor.execute("DELETE FROM comments WHERE student_id IN (SELECT id FROM students WHERE (id IS NULL OR id = '') AND class_id = ?)", (class_id,))
        except Exception as e:
            logger.warning(f"清理 comments 时出错: {e}")

        # 删除 students 中 id 为空或 NULL 的记录
        try:
            cursor.execute('BEGIN')
        except Exception:
            pass

        cursor.execute("DELETE FROM students WHERE (id IS NULL OR id = '') AND class_id = ?", (class_id,))
        deleted = cursor.rowcount if hasattr(cursor, 'rowcount') else to_delete

        conn.commit()
        conn.close()

        logger.info(f"已清理班级 {class_id} 中 {deleted} 条无学号的学生记录")
        return jsonify({'status': 'ok', 'message': f'已删除 {deleted} 条无学号学生', 'deleted': deleted})

    except Exception as e:
        logger.exception(f"清理无学号学生时出错: {str(e)}")
        try:
            if 'conn' in locals() and conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return jsonify({'status': 'error', 'message': f'清理失败: {str(e)}'}), 500

# 导出学生数据到Excel
@students_bp.route('/api/students/export-excel', methods=['GET'])
@login_required
def export_students_excel():
    """导出学生数据到Excel文件"""
    try:
        class_id = request.args.get('class_id')
        
        # 班主任只能导出自己班级的学生
        if not current_user.is_admin:
            if not current_user.class_id:
                return jsonify({
                    'status': 'error',
                    'message': '您尚未被分配班级，无法导出学生数据'
                }), 403
            class_id = current_user.class_id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取学生数据
            if class_id:
                cursor.execute('''
                    SELECT s.*, c.class_name 
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    WHERE s.class_id = ?
                    ORDER BY CAST(s.id AS INTEGER)
                ''', (class_id,))
            else:
                cursor.execute('''
                    SELECT s.*, c.class_name 
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    ORDER BY c.class_name, CAST(s.id AS INTEGER)
                ''')
            
            students = cursor.fetchall()
            
            # 创建Excel工作簿
            wb = Workbook()
            ws = wb.active
            ws.title = "学生信息"
            
            # 设置表头
            headers = ['学号', '姓名', '性别', '班级', '身高(cm)', '体重(kg)', 
                      '胸围(cm)', '肺活量(ml)', '龋齿(个)', '视力左', '视力右',
                      '语文', '数学', '英语', '劳动', '体育', '音乐', '美术', 
                      '科学', '综合', '信息', '书法', '心理',
                      '品质', '学习', '健康', '审美', '实践', '生活',
                      '评语']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')
                # 为评语列设置更宽的列宽
                if header == '评语':
                    ws.column_dimensions[get_column_letter(col)].width = 40
                else:
                    ws.column_dimensions[get_column_letter(col)].width = 15
            
            # 写入数据
            for row, student in enumerate(students, 2):
                ws.cell(row=row, column=1, value=student['id'])
                ws.cell(row=row, column=2, value=student['name'])
                ws.cell(row=row, column=3, value=student['gender'])
                ws.cell(row=row, column=4, value=student['class_name'])
                ws.cell(row=row, column=5, value=student['height'])
                ws.cell(row=row, column=6, value=student['weight'])
                ws.cell(row=row, column=7, value=student['chest_circumference'])
                ws.cell(row=row, column=8, value=student['vital_capacity'])
                ws.cell(row=row, column=9, value=student['dental_caries'])
                ws.cell(row=row, column=10, value=student['vision_left'])
                ws.cell(row=row, column=11, value=student['vision_right'])
                
                # 学科成绩
                ws.cell(row=row, column=12, value=student['yuwen'])
                ws.cell(row=row, column=13, value=student['shuxue'])
                ws.cell(row=row, column=14, value=student['yingyu'])
                ws.cell(row=row, column=15, value=student['laodong'])
                ws.cell(row=row, column=16, value=student['tiyu'])
                ws.cell(row=row, column=17, value=student['yinyue'])
                ws.cell(row=row, column=18, value=student['meishu'])
                ws.cell(row=row, column=19, value=student['kexue'])
                ws.cell(row=row, column=20, value=student['zonghe'])
                ws.cell(row=row, column=21, value=student['xinxi'])
                ws.cell(row=row, column=22, value=student['shufa'])
                ws.cell(row=row, column=23, value=student['xinli'])
                
                # 德育维度
                ws.cell(row=row, column=24, value=student['pinzhi'])
                ws.cell(row=row, column=25, value=student['xuexi'])
                ws.cell(row=row, column=26, value=student['jiankang'])
                ws.cell(row=row, column=27, value=student['shenmei'])
                ws.cell(row=row, column=28, value=student['shijian'])
                ws.cell(row=row, column=29, value=student['shenghuo'])
                
                # 评语
                comments_cell = ws.cell(row=row, column=30, value=student['comments'])
                comments_cell.alignment = Alignment(wrapText=True)  # 允许评语自动换行
                ws.cell(row=row, column=9, value=student['dental_caries'])
                ws.cell(row=row, column=10, value=student['vision_left'])
                ws.cell(row=row, column=11, value=student['vision_right'])
            
            # 将Excel保存到字节流
            excel_file = BytesIO()
            wb.save(excel_file)
            excel_file.seek(0)
            
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'学生数据_{current_time}.xlsx'
            
            return send_file(
                excel_file,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"导出学生数据时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'导出学生数据失败: {str(e)}'}), 500


@students_bp.route('/api/students/export-basic-info', methods=['GET'])
@login_required
def export_students_basic_info():
    """导出学生基本信息到Excel文件（学号、姓名、性别、班级）"""
    try:
        class_id = request.args.get('class_id')
        
        # 班主任只能导出自己班级的学生
        if not current_user.is_admin:
            if not current_user.class_id:
                return jsonify({
                    'status': 'error',
                    'message': '您尚未被分配班级，无法导出学生数据'
                }), 403
            class_id = current_user.class_id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取班级信息用于文件命名
            class_name = None
            if class_id:
                cursor.execute('SELECT class_name FROM classes WHERE id = ?', (class_id,))
                class_info = cursor.fetchone()
                if class_info:
                    class_name = class_info['class_name']
            
            # 获取学生基本数据
            if class_id:
                cursor.execute('''
                    SELECT s.id, s.name, s.gender, c.class_name 
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    WHERE s.class_id = ?
                    ORDER BY CAST(s.id AS INTEGER)
                ''', (class_id,))
            else:
                cursor.execute('''
                    SELECT s.id, s.name, s.gender, c.class_name 
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    ORDER BY c.class_name, CAST(s.id AS INTEGER)
                ''')
            
            students = cursor.fetchall()
            
            if not students:
                return jsonify({
                    'status': 'error',
                    'message': '没有找到学生数据'
                }), 404
            
            # 创建Excel工作簿
            wb = Workbook()
            ws = wb.active
            ws.title = "学生基本信息"
            
            # 设置表头
            headers = ['学号', '姓名', '性别', '班级']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color='E6F3FF', end_color='E6F3FF', fill_type='solid')
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # 填充数据
            for row, student in enumerate(students, 2):
                ws.cell(row=row, column=1, value=student['id'])
                ws.cell(row=row, column=2, value=student['name'])
                ws.cell(row=row, column=3, value=student['gender'])
                ws.cell(row=row, column=4, value=student['class_name'] or '未分配')
            
            # 调整列宽
            ws.column_dimensions['A'].width = 12  # 学号
            ws.column_dimensions['B'].width = 15  # 姓名
            ws.column_dimensions['C'].width = 8   # 性别
            ws.column_dimensions['D'].width = 20  # 班级
            
            # 将Excel保存到字节流
            excel_file = BytesIO()
            wb.save(excel_file)
            excel_file.seek(0)
            
            # 根据用户类型和班级信息设置文件名
            if not current_user.is_admin and class_name:
                # 班主任：使用"班级名+学生名单.xlsx"格式
                filename = f'{class_name}学生名单.xlsx'
            elif class_name:
                # 管理员选择特定班级
                filename = f'{class_name}学生名单.xlsx'
            else:
                # 管理员导出全校
                current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'全校学生名单_{current_time}.xlsx'
            
            return send_file(
                excel_file,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"导出学生基本信息时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'导出学生基本信息失败: {str(e)}'}), 500