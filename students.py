#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学生管理模块，包含学生相关的API路由和功能
"""

import os
import datetime
import traceback
import sqlite3
from flask import Blueprint, request, jsonify, send_from_directory, url_for
from werkzeug.utils import secure_filename
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

# 学生蓝图
students_bp = Blueprint('students', __name__)

# 配置
UPLOAD_FOLDER = 'uploads'
TEMPLATE_FOLDER = 'templates'
DATABASE = 'students.db'

# 创建数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

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
    
    # 设置标题行
    headers = ['学号', '姓名', '性别', '班级', '身高(cm)', '体重(kg)', '胸围(cm)', '肺活量(ml)', '龋齿(个)', '视力左', '视力右']
    for i, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=i, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[get_column_letter(i)].width = 15
    
    # 添加示例数据
    example_data = ['1', '张三', '男', '三年级一班', '135', '32', '65', '1500', '0', '5.0', '5.0']
    for i, value in enumerate(example_data, 1):
        ws.cell(row=2, column=i, value=value)
    
    # 添加说明文字
    ws.cell(row=4, column=1, value="说明事项：")
    ws.cell(row=5, column=1, value="1. 请按照示例格式填写学生信息")
    ws.cell(row=6, column=1, value='2. 性别请填写"男"或"女"')
    ws.cell(row=7, column=1, value="3. 班级格式: 三年级一班")
    ws.cell(row=8, column=1, value="4. 视力格式: 5.0 或 4.8 等")
    
    # 合并说明文字的单元格
    for i in range(4, 9):
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=5)
    
    wb.save(template_path)
    print("学生Excel模板创建完成")
    return template_path

# 获取所有学生API
@students_bp.route('/api/students', methods=['GET'], strict_slashes=False)
def get_all_students():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students ORDER BY CAST(id AS INTEGER)')
    students = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'count': len(students),
        'students': students
    })

# 获取单个学生API
@students_bp.route('/api/students/<student_id>', methods=['GET'], strict_slashes=False)
def get_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    conn.close()
    
    if student:
        return jsonify({
            'status': 'ok',
            'student': dict(student)
        })
    else:
        return jsonify({'error': '未找到学生'}), 404

# 添加新学生API
@students_bp.route('/api/students', methods=['POST'], strict_slashes=False)
def add_student():
    data = request.json
    
    if not data:
        return jsonify({'error': '无效的请求数据'}), 400
    
    required_fields = ['id', 'name', 'gender']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少必要的字段: {field}'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查学生ID是否已存在
    cursor.execute('SELECT id FROM students WHERE id = ?', (data['id'],))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': f'学号 {data["id"]} 已存在'}), 400
    
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
            id, name, gender, class, height, weight,
            chest_circumference, vital_capacity, dental_caries,
            vision_left, vision_right, physical_test_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data['name'], data['gender'], data.get('class', ''),
            height, weight, 
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
        print(f"添加学生时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'添加学生时出错: {str(e)}'}), 500
    finally:
        conn.close()

# 更新学生API
@students_bp.route('/api/students/<student_id>', methods=['PUT'], strict_slashes=False)
def update_student(student_id):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"收到更新学生信息请求，学生ID: {student_id}")
    
    try:
        data = request.json
        logger.info(f"请求数据: {data}")
        
        if not data:
            logger.error("无效的请求数据")
            return jsonify({'error': '无效的请求数据'}), 400
        
        # 确保请求的ID与URL中的ID一致
        if 'id' in data and data['id'] != student_id:
            logger.error(f"URL中的ID({student_id})与请求体中的ID({data['id']})不一致")
            return jsonify({'error': '学生ID不一致'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学生是否存在
        cursor.execute('SELECT id FROM students WHERE id = ?', (student_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': f'未找到学号为 {student_id} 的学生'}), 404
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 更详细的数值处理和日志
        numeric_fields = {
            'height': 'height',
            'weight': 'weight',
            'chest_circumference': 'chest_circumference',
            'vital_capacity': 'vital_capacity',
            'vision_left': 'vision_left',
            'vision_right': 'vision_right',
        }
        
        processed_values = {}
        
        # 处理数值字段
        for field, db_field in numeric_fields.items():
            raw_value = data.get(field, None)
            logger.info(f"字段 {field} 原始值: {raw_value}, 类型: {type(raw_value).__name__}")
            
            try:
                if raw_value is None or raw_value == '' or raw_value == 'null' or raw_value == 'undefined' or raw_value == '-':
                    processed_values[db_field] = None
                    logger.info(f"字段 {field} 设为None")
                else:
                    # 如果是字符串，处理逗号等
                    if isinstance(raw_value, str):
                        # 替换逗号为点
                        raw_value = raw_value.replace(',', '.')
                        logger.info(f"字段 {field} 预处理后: {raw_value}")
                    
                    # 转换为浮点数
                    value = float(raw_value)
                    # 处理0值
                    processed_values[db_field] = 0.0 if value == 0 else value
                    logger.info(f"字段 {field} 成功转换为: {processed_values[db_field]}")
            except (ValueError, TypeError) as e:
                logger.warning(f"字段 {field} 值 '{raw_value}' 转换错误: {str(e)}")
                processed_values[db_field] = None
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(students)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"数据库表列: {existing_columns}")
        
        # 检查所需列是否存在，如不存在则添加
        required_columns = list(numeric_fields.values()) + ['dental_caries', 'physical_test_status']
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.warning(f"数据库表缺少列: {missing_columns}")
            for column in missing_columns:
                column_type = "TEXT" if column in ['dental_caries', 'physical_test_status'] else "REAL"
                logger.info(f"添加缺失的列: {column} ({column_type})")
                try:
                    cursor.execute(f"ALTER TABLE students ADD COLUMN {column} {column_type}")
                except sqlite3.Error as e:
                    logger.error(f"添加列 {column} 时出错: {str(e)}")
            
            conn.commit()
            logger.info("已添加缺失的列")
        
        # 构建更新SQL
        update_fields = []
        params = []
        
        # 基本字段
        update_fields.append("name = ?")
        params.append(data.get('name', ''))
        
        update_fields.append("gender = ?")
        params.append(data.get('gender', ''))
        
        update_fields.append("class = ?")
        params.append(data.get('class', ''))
        
        # 数值字段
        for db_field in numeric_fields.values():
            if db_field in existing_columns:
                update_fields.append(f"{db_field} = ?")
                params.append(processed_values.get(db_field))
        
        # 文本字段
        if 'dental_caries' in existing_columns:
            update_fields.append("dental_caries = ?")
            params.append(data.get('dental_caries', ''))
        
        if 'physical_test_status' in existing_columns:
            update_fields.append("physical_test_status = ?")
            params.append(data.get('physical_test_status', ''))
        
        # 更新时间
        update_fields.append("updated_at = ?")
        params.append(now)
        
        # 添加WHERE条件
        params.append(student_id)
        
        # 构建完整的SQL语句
        update_sql = f"UPDATE students SET {', '.join(update_fields)} WHERE id = ?"
        logger.info(f"更新SQL: {update_sql}")
        logger.info(f"参数: {params}")
        
        # 执行更新
        cursor.execute(update_sql, params)
        conn.commit()
        
        logger.info(f"成功更新学生信息: ID={student_id}, 名称={data.get('name', 'unknown')}")
        
        return jsonify({
            'status': 'ok',
            'message': f'成功更新学生信息: {data.get("name", student_id)}',
            'student_id': student_id
        })
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        error_msg = f"数据库错误: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        error_msg = f"更新学生信息时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
    finally:
        if conn:
            conn.close()

# 删除学生API
@students_bp.route('/api/students/<student_id>', methods=['DELETE'], strict_slashes=False)
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查学生是否存在
    cursor.execute('SELECT id, name FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return jsonify({'error': f'未找到学号为 {student_id} 的学生'}), 404
    
    student_name = student['name']
    
    try:
        cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'message': f'成功删除学生: {student_name}',
            'student_id': student_id
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'删除学生时出错: {str(e)}'}), 500
    finally:
        conn.close()

# 导入学生预览API
@students_bp.route('/api/import-students', methods=['POST'])
def import_students_preview():
    import logging
    logger = logging.getLogger(__name__)
    
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({'error': '只支持.xlsx或.xls格式的Excel文件'}), 400
    
    # 保存上传的文件
    filename = secure_filename(file.filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    saved_filename = f"{timestamp}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
    
    # 确保上传目录存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    file.save(file_path)
    
    try:
        # 导入openpyxl处理Excel
        try:
            import openpyxl
        except ImportError:
            return jsonify({'error': '服务器缺少openpyxl库，无法处理Excel文件'}), 500
            
        # 打开Excel工作簿
        try:
            wb = openpyxl.load_workbook(file_path)
            sheet = wb.active
        except Exception as e:
            logger.error(f"打开Excel文件时出错: {str(e)}")
            return jsonify({'error': f'无法打开Excel文件: {str(e)}'}), 500
            
        # 获取表头
        headers = [cell.value for cell in sheet[1] if cell.value]
        
        if not headers or len(headers) < 3:  # 至少应该有学号、姓名和性别
            return jsonify({'error': 'Excel格式不正确，第一行应包含列名（如学号、姓名、性别等）'}), 400
            
        # 验证必要的列是否存在
        required_columns = ['学号', '姓名', '性别']
        missing_columns = [col for col in required_columns if col not in headers]
        
        if missing_columns:
            return jsonify({'error': f"Excel缺少必要的列: {', '.join(missing_columns)}"}), 400
            
        # 初始化数据和统计变量
        students_data = []
        added_count = 0
        updated_count = 0
        skipped_count = 0
        error_records = []
        
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
            #'视力(左)': 'vision_left',
            #'右眼视力': 'vision_right',
            '视力右': 'vision_right',
            '体测情况': 'physical_test_status',
            #'体测状态': 'physical_test_status'
        }
        
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 从第二行开始读取数据（跳过表头）
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2), 2):
            # 检查是否为空行
            if all(cell.value is None for cell in row):
                continue
                
            # 准备学生数据
            student = {}
            
            # 遍历表头和字段映射
            for col_idx, header in enumerate(headers):
                if header in field_mapping:
                    field_name = field_mapping[header]
                    cell_value = row[col_idx].value
                    
                    # 特殊处理数值字段
                    if field_name in ['height', 'weight', 'chest_circumference', 'vital_capacity', 'vision_left', 'vision_right']:
                        try:
                            if cell_value is not None and cell_value != '' and cell_value != '-':
                                # 统一处理为浮点数
                                if isinstance(cell_value, str):
                                    # 移除单位和无用字符
                                    cell_value = cell_value.replace('cm', '').replace('kg', '')
                                    cell_value = cell_value.replace('ml', '').replace('(', '').replace(')', '')
                                    cell_value = cell_value.replace(',', '.').strip()
                                    # 如果只有'-'，设为None
                                    if cell_value == '-' or cell_value == '':
                                        student[field_name] = None
                                    else:
                                        student[field_name] = float(cell_value)
                                else:
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
            
            # 检查必填字段
            if not student.get('id') or not student.get('name'):
                error_records.append({
                    'row': row_idx,
                    'reason': '学号或姓名为空'
                })
                skipped_count += 1
                continue
                
            # 检查学生是否已存在
            cursor.execute('SELECT id FROM students WHERE id = ?', (student['id'],))
            if cursor.fetchone():
                updated_count += 1
            else:
                added_count += 1
                
            students_data.append(student)
        
        conn.close()
        
        # 如果找到有效数据，返回预览信息
        if students_data:
            return jsonify({
                'status': 'ok',
                'message': f'发现 {len(students_data)} 名学生数据，其中 {added_count} 名新增，{updated_count} 名更新，{skipped_count} 名有错误',
                'details': {
                    'added': added_count,
                    'updated': updated_count,
                    'skipped': skipped_count,
                    'errors': error_records
                },
                'students': students_data,
                'file_path': file_path
            })
        else:
            return jsonify({'error': '未在Excel文件中找到有效的学生数据'}), 400
        
    except Exception as e:
        logger.error(f"解析Excel文件时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'解析Excel文件时出错: {str(e)}'}), 500

# 确认导入学生API
@students_bp.route('/api/confirm-import', methods=['POST'])
def confirm_import():
    import logging
    logger = logging.getLogger(__name__)
    
    data = request.json
    
    # 增加详细日志记录，帮助诊断问题
    logger.info("接收到的导入确认请求数据: %s", data)
    
    if not data or 'students' not in data:
        return jsonify({'error': '无效的请求数据'}), 400
    
    students = data['students']
    
    if not students or len(students) == 0:
        return jsonify({'error': '没有学生数据可导入'}), 400
    
    # 记录第一条学生数据的结构，帮助诊断
    if students and len(students) > 0:
        logger.info("第一条学生数据样例: %s", students[0])
        logger.info("学生数据字段: %s", list(students[0].keys()))
        
        # 详细记录第一条学生的数值字段
        first_student = students[0]
        for field in ['height', 'weight', 'chest_circumference', 'vital_capacity', 'vision_left', 'vision_right']:
            if field in first_student:
                value = first_student[field]
                logger.info(f"数值字段 {field}: {value}, 类型: {type(value).__name__}")
    
    # 检查数据库表结构
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取表结构
    cursor.execute("PRAGMA table_info(students)")
    db_columns = [row[1] for row in cursor.fetchall()]
    logger.info("数据库表字段: %s", db_columns)
    
    # 字段名映射表，用于处理代码和数据库字段名不一致的情况
    field_mappings = {
        'chest_circumference': 'chest_circumference',  # 可能的映射
        'chestCircumference': 'chest_circumference',   # 前端JS中可能使用的驼峰命名
        'vital_capacity': 'vital_capacity',
        'vitalCapacity': 'vital_capacity',
        'dental_caries': 'dental_caries',
        'dentalCaries': 'dental_caries',
        'vision_left': 'vision_left',
        'visionLeft': 'vision_left',
        'vision_right': 'vision_right',
        'visionRight': 'vision_right',
        'physical_test_status': 'physical_test_status',
        'physicalTestStatus': 'physical_test_status'
    }
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 清空学生表中的所有记录 - 根据用户需求，导入时只保留当前班级的学生
    try:
        logger.info("导入前清空学生表中的所有记录")
        cursor.execute('DELETE FROM students')
        logger.info(f"已清空学生表，准备导入 {len(students)} 名新学生")
    except Exception as clear_error:
        logger.error(f"清空学生表时出错: {str(clear_error)}")
        return jsonify({
            'status': 'error',
            'message': f'清空数据库时出错: {str(clear_error)}'
        }), 500
    
    success_count = 0
    error_count = 0
    updated_count = 0
    inserted_count = 0
    error_details = []
    
    try:
        for i, student in enumerate(students):
            try:
                # 打印学生数据以便调试
                logger.info(f"准备导入的学生数据({i+1}/{len(students)}): {student}")
                
                # 添加数据验证
                if 'id' not in student or not student['id']:
                    raise ValueError(f"学生ID缺失或无效: {student}")
                if 'name' not in student or not student['name']:
                    raise ValueError(f"学生姓名缺失或无效: {student}")
                if 'gender' not in student:
                    raise ValueError(f"学生性别缺失: {student}")
                
                # 准备SQL参数，确保使用正确的字段名
                params = {
                    'id': student['id'],
                    'name': student['name'],
                    'gender': student['gender'],
                    'class': student.get('class', ''),
                    'created_at': now,
                    'updated_at': now
                }
                
                # 数值字段的特殊处理
                numeric_fields = [
                    'height', 'weight', 'chest_circumference', 
                    'vital_capacity', 'vision_left', 'vision_right'
                ]
                
                for field in numeric_fields:
                    # 获取字段值，对null、空字符串、null字符串等进行处理
                    raw_value = student.get(field)
                    if raw_value is None or raw_value == '' or raw_value == 'null' or raw_value == 'undefined' or raw_value == '-':
                        params[field] = None
                    else:
                        # 尝试转换为浮点数
                        try:
                            # 如果是字符串，处理可能的特殊格式
                            if isinstance(raw_value, str):
                                # 移除单位和无用字符
                                raw_value = raw_value.replace('cm', '').replace('kg', '')
                                raw_value = raw_value.replace('ml', '').replace('(', '').replace(')', '')
                                # 替换逗号为点号(小数点)
                                raw_value = raw_value.replace(',', '.').strip()
                                # 如果是'-'，设为None
                                if raw_value == '-' or raw_value == '':
                                    params[field] = None
                                    continue
                            
                            # 转换为浮点数
                            value = float(raw_value)
                            # 特别处理0值
                            params[field] = 0.0 if value == 0 else value
                            
                            logger.info(f"字段 {field} 原始值: {raw_value} ({type(raw_value).__name__}) -> 转换值: {params[field]} ({type(params[field]).__name__})")
                        except (ValueError, TypeError) as e:
                            params[field] = None
                            logger.warning(f"无法转换字段 {field} 的值 {raw_value}: {str(e)}")
                
                # 处理文本字段
                if 'dental_caries' in student:
                    params['dental_caries'] = student['dental_caries']
                if 'physical_test_status' in student:
                    params['physical_test_status'] = student['physical_test_status']
                
                # 处理特殊字段，确保使用正确的数据库字段名 (处理可能的命名不一致)
                for field in student:
                    if field in field_mappings and field_mappings[field] in db_columns:
                        db_field = field_mappings[field]
                        params[db_field] = student[field]
                
                # 打印最终的SQL参数
                logger.info(f"最终SQL参数: {params}")
                
                # 检查学生是否已存在
                cursor.execute('SELECT id FROM students WHERE id = ?', (student['id'],))
                existing_student = cursor.fetchone()
                
                if existing_student:
                    # 构建更新SQL - 修改为覆盖更新所有字段
                    update_fields = []
                    update_values = []
                    
                    # 遍历所有数据库列，不仅仅是导入数据中的列
                    for field in db_columns:
                        if field != 'id':  # ID不更新
                            # 如果字段在导入数据参数中，使用新值
                            # 否则设置为NULL或空字符串（根据字段类型）
                            if field in params:
                                value = params[field]
                            else:
                                # 为文本字段设空字符串，数值字段设NULL
                                is_text_field = field in ['name', 'gender', 'class', 'dental_caries', 
                                                         'physical_test_status', 'comments', 'created_at', 'updated_at']
                                value = '' if is_text_field else None
                                
                                # 特殊处理评语字段，确保清空
                                if field == 'comments':
                                    value = ''
                                    
                            update_fields.append(f"{field} = ?")
                            update_values.append(value)
                    
                    # 添加WHERE条件的参数
                    update_values.append(student['id'])
                    
                    # 执行更新
                    update_sql = f"UPDATE students SET {', '.join(update_fields)} WHERE id = ?"
                    logger.info(f"更新SQL: {update_sql}")
                    logger.info(f"更新参数: {update_values}")
                    cursor.execute(update_sql, update_values)
                    updated_count += 1
                else:
                    # 构建插入SQL - 修改为包含所有字段
                    insert_fields = []
                    insert_values = []
                    insert_placeholders = []
                    
                    # 遍历所有数据库列，不仅仅是导入数据中的列
                    for field in db_columns:
                        insert_fields.append(field)
                        
                        # 如果字段在导入数据参数中，使用新值
                        # 否则设置为NULL或空字符串（根据字段类型）
                        if field in params:
                            value = params[field]
                        else:
                            # 为文本字段设空字符串，数值字段设NULL
                            is_text_field = field in ['name', 'gender', 'class', 'dental_caries', 
                                                     'physical_test_status', 'comments', 'created_at', 'updated_at']
                            value = '' if is_text_field else None
                            
                            # 特殊处理评语字段，确保为空
                            if field == 'comments':
                                value = ''
                        
                        insert_values.append(value)
                        insert_placeholders.append('?')
                    
                    # 执行插入
                    insert_sql = f"INSERT INTO students ({', '.join(insert_fields)}) VALUES ({', '.join(insert_placeholders)})"
                    logger.info(f"插入SQL: {insert_sql}")
                    logger.info(f"插入参数: {insert_values}")
                    cursor.execute(insert_sql, insert_values)
                    inserted_count += 1
                
                success_count += 1
            except Exception as student_error:
                # 单个学生导入错误不应该影响整体事务
                error_count += 1
                error_msg = f"导入学生 {student.get('id', '未知ID')} 时出错: {str(student_error)}"
                logger.error(error_msg)
                error_details.append(error_msg)
                # 继续处理下一个学生，而不是中断整个批次
        
        # 如果至少有一个学生成功导入，提交事务
        if success_count > 0:
            conn.commit()
            logger.info(f"成功导入 {success_count} 名学生，更新 {updated_count} 名，新增 {inserted_count} 名")
        else:
            conn.rollback()
            logger.warning("没有学生成功导入，回滚事务")
    except Exception as e:
        conn.rollback()
        error_count += 1
        error_msg = f"导入学生数据时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        error_details.append(error_msg)
        return jsonify({
            'status': 'error',
            'message': error_msg,
            'error_details': error_details
        }), 500
    finally:
        conn.close()
    
    # 如果有错误但也有成功，返回部分成功的响应
    status = 'ok' if error_count == 0 else 'partial'
    return jsonify({
        'status': status,
        'message': f'成功导入{success_count}名学生（新增{inserted_count}名，更新{updated_count}名）' +
                  (f'，{error_count}名学生导入失败' if error_count > 0 else ''),
        'success_count': success_count,
        'error_count': error_count,
        'updated_count': updated_count,
        'inserted_count': inserted_count,
        'error_details': error_details if error_count > 0 else []
    })

# 下载模板API
@students_bp.route('/api/template', methods=['GET'])
def download_template():
    template_path = os.path.join(TEMPLATE_FOLDER, 'student_template.xlsx')
    if not os.path.exists(template_path):
        create_student_template()
    
    return jsonify({
        'status': 'ok',
        'template_url': f'/download/template/student_template.xlsx'
    })

# 提供模板下载
@students_bp.route('/download/template/<filename>', methods=['GET'])
def serve_template(filename):
    return send_from_directory(TEMPLATE_FOLDER, filename)

# 获取所有班级API
@students_bp.route('/api/classes', methods=['GET'])
def get_all_classes():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查询所有不同的班级
    cursor.execute('SELECT DISTINCT class FROM students WHERE class IS NOT NULL AND class != "" ORDER BY class')
    classes = [row['class'] for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'count': len(classes),
        'classes': classes
    }) 