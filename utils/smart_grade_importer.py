# -*- coding: utf-8 -*-
"""
智能成绩导入器
支持角色权限判断、多班级多学科智能导入、详细错误提示
"""

import sqlite3
import os
import pandas as pd
import numpy as np
from datetime import datetime
import traceback
import logging

logger = logging.getLogger(__name__)

class SmartGradeImporter:
    """智能成绩导入器"""
    
    def __init__(self, db_path="students.db"):
        self.db_path = db_path
        
        # 学科名称映射（Excel列名 -> 数据库字段名）
        self.subject_mapping = {
            '道法': 'daof',
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
            '心理': 'xinli'
        }
        
        # 允许的成绩值
        self.allowed_grades = ['优', '良', '及格', '待及格', '/']
        
        # 成绩映射表 - 将不同格式的成绩转换为标准格式
        self.grade_mapping = {
            '优秀': '优', 'A': '优', 'a': '优',
            '良好': '良', 'B': '良', 'b': '良',
            '中等': '及格', '中': '及格', 'C': '及格', 'c': '及格', '及': '及格',
            '不及格': '待及格', '差': '待及格', 'D': '待及格', 'd': '待及格', '待': '待及格',
            '无': '/', '缺': '/', '免修': '/'
        }
    
    def get_user_permissions(self, user):
        """
        获取用户的导入权限信息
        
        Returns:
            dict: {
                'role': 角色名称,
                'is_admin': 是否超级管理员,
                'accessible_classes': [可访问的班级ID列表],
                'teaching_map': {班级ID: [学科列表]},
                'can_import_all': 是否可以导入所有学科
            }
        """
        from utils.permission_checker import (
            is_super_admin, is_head_teacher, get_accessible_classes
        )
        
        permissions = {
            'role': getattr(user, 'primary_role', '科任老师'),
            'is_admin': is_super_admin(user),
            'accessible_classes': [],
            'teaching_map': {},
            'can_import_all': False
        }
        
        # 超级管理员可以导入所有班级的所有学科
        if permissions['is_admin']:
            permissions['can_import_all'] = True
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM classes ORDER BY id')
            permissions['accessible_classes'] = [row[0] for row in cursor.fetchall()]
            conn.close()
            return permissions
        
        # 正班主任可以导入自己班级的所有学科
        if is_head_teacher(user) and user.class_id:
            permissions['accessible_classes'] = [user.class_id]
            permissions['teaching_map'][str(user.class_id)] = list(self.subject_mapping.keys())
            permissions['can_import_all'] = False  # 仅限自己班级
            return permissions
        
        # 其他角色：从 teaching_assignments 表获取任教信息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT class_id, subject
            FROM teaching_assignments
            WHERE teacher_id = ?
            ORDER BY class_id
        ''', (user.id,))
        
        for row in cursor.fetchall():
            class_id = row[0]
            subject = row[1]
            
            if class_id not in permissions['accessible_classes']:
                permissions['accessible_classes'].append(class_id)
            
            if class_id not in permissions['teaching_map']:
                permissions['teaching_map'][class_id] = []
            
            permissions['teaching_map'][class_id].append(subject)
        
        conn.close()
        return permissions
    
    def validate_excel_structure(self, df):
        """
        验证Excel文件结构
        
        Returns:
            dict: {
                'valid': bool,
                'errors': [错误列表],
                'warnings': [警告列表],
                'detected_subjects': [检测到的学科列表],
                'detected_classes': [检测到的班级列表]
            }
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'detected_subjects': [],
            'detected_classes': [],
            'unrecognized_columns': []
        }
        
        # 检查必需列
        if '姓名' not in df.columns:
            result['valid'] = False
            result['errors'].append('❌ 缺少必需列：姓名')
        
        if '班级' not in df.columns:
            result['warnings'].append('⚠️ 建议添加"班级"列用于数据校验')
        
        # 检测班级列
        if '班级' in df.columns:
            classes = df['班级'].dropna().unique()
            result['detected_classes'] = [str(c).strip() for c in classes if str(c).strip()]
        
        # 检测学科列
        for col in df.columns:
            if col in ['姓名', '班级', '学号']:  # 学号可选，但如果存在就忽略
                continue
            
            if col in self.subject_mapping:
                result['detected_subjects'].append(col)
            else:
                result['unrecognized_columns'].append(col)
        
        if not result['detected_subjects']:
            result['valid'] = False
            result['errors'].append(f'❌ 未检测到任何有效的学科列。支持的学科：{", ".join(self.subject_mapping.keys())}')
        
        if result['unrecognized_columns']:
            result['warnings'].append(
                f'⚠️ 以下列无法识别，将被忽略：{", ".join(result["unrecognized_columns"])}'
            )
        
        return result
    
    def match_students_with_database(self, df, permissions):
        """
        将Excel中的学生与数据库匹配
        
        Returns:
            dict: {
                'matched': [{学生信息}],
                'errors': [错误列表],
                'warnings': [警告列表]
            }
        """
        result = {
            'matched': [],
            'errors': [],
            'warnings': []
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取数据库中的学生信息
        if permissions['can_import_all']:
            # 超级管理员：获取所有学生
            cursor.execute('''
                SELECT s.id, s.name, s.class_id, c.class_name
                FROM students s
                LEFT JOIN classes c ON s.class_id = c.id
                ORDER BY s.class_id, CAST(s.id AS INTEGER)
            ''')
        else:
            # 其他角色：只获取有权限的班级的学生
            placeholders = ','.join('?' * len(permissions['accessible_classes']))
            cursor.execute(f'''
                SELECT s.id, s.name, s.class_id, c.class_name
                FROM students s
                LEFT JOIN classes c ON s.class_id = c.id
                WHERE s.class_id IN ({placeholders})
                ORDER BY s.class_id, CAST(s.id AS INTEGER)
            ''', permissions['accessible_classes'])
        
        db_students = {}
        for row in cursor.fetchall():
            student_id = str(row[0])
            db_students[student_id] = {
                'id': student_id,
                'name': row[1],
                'class_id': int(row[2]) if row[2] else None,  # 强制转换为整数
                'class_name': row[3]
            }
        
        logger.info(f"从数据库获取了 {len(db_students)} 个学生")
        if db_students:
            first_student_id = list(db_students.keys())[0]
            logger.info(f"第一个学生ID: '{first_student_id}' (type={type(first_student_id)}), 学生信息: {db_students[first_student_id]}")
        
        conn.close()
        
        # 匹配Excel中的学生 - 使用班级+姓名匹配
        has_name_column = '姓名' in df.columns
        has_class_column = '班级' in df.columns
        
        if not has_name_column:
            result['errors'].append('❌ Excel文件缺少"姓名"列，无法匹配学生')
            return result
        
        # 建立班级+姓名的索引
        db_students_by_name = {}
        for student_id, student_info in db_students.items():
            key = f"{student_info['class_name']}_{student_info['name']}"
            db_students_by_name[key] = student_info
        
        logger.info(f"建立了 {len(db_students_by_name)} 个班级-姓名索引")
        
        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel行号（从2开始，因为第1行是标题）
            
            # 获取姓名
            excel_name = str(row['姓名']).strip() if pd.notna(row['姓名']) else ''
            if not excel_name:
                result['errors'].append(f'❌ 第{row_num}行：姓名为空')
                continue
            
            # 获取班级
            excel_class = ''
            if has_class_column:
                excel_class = str(row['班级']).strip() if pd.notna(row['班级']) else ''
            
            # 如果没有班级列，尝试从权限中推断
            if not excel_class:
                if len(permissions['accessible_classes']) == 1:
                    # 只有一个班级权限，直接使用
                    class_id = permissions['accessible_classes'][0]
                    # 查找这个班级的class_name
                    for student_info in db_students.values():
                        if student_info['class_id'] == class_id:
                            excel_class = student_info['class_name']
                            break
                else:
                    result['errors'].append(f'❌ 第{row_num}行：缺少班级信息，且您有多个班级权限，无法确定学生所属班级')
                    continue
            
            # 匹配学生
            key = f"{excel_class}_{excel_name}"
            if key not in db_students_by_name:
                result['errors'].append(f'❌ 第{row_num}行：找不到学生 {excel_class} - {excel_name}')
                continue
            
            db_student = db_students_by_name[key]
            
            # 检查权限
            if not permissions['can_import_all']:
                if db_student['class_id'] not in permissions['accessible_classes']:
                    result['errors'].append(
                        f'❌ 第{row_num}行：您没有权限导入班级 {db_student["class_name"]} 的成绩'
                    )
                    continue
            
            # 添加到匹配列表
            result['matched'].append({
                'row_num': row_num,
                'student_id': db_student['id'],
                'student_name': db_student['name'],
                'class_id': db_student['class_id'],
                'class_name': db_student['class_name'],
                'excel_row': row.to_dict()  # 转换为字典
            })
        
        return result

    
    def validate_grades_and_permissions(self, matched_students, detected_subjects, permissions):
        """
        验证成绩数据和权限
        
        Returns:
            dict: {
                'valid_records': [{有效记录}],
                'errors': [错误列表],
                'warnings': [警告列表],
                'stats': {统计信息}
            }
        """
        logger.info(f"开始验证成绩和权限 - matched_students数量: {len(matched_students)}, detected_subjects: {detected_subjects}")
        logger.info(f"permissions: {permissions}")
        
        result = {
            'valid_records': [],
            'errors': [],
            'warnings': [],
            'stats': {
                'total_rows': len(matched_students),
                'valid_rows': 0,
                'invalid_grades': 0,
                'permission_denied': 0,
                'by_class': {},
                'by_subject': {}
            }
        }
        
        for student in matched_students:
            row_num = student['row_num']
            student_id = student['student_id']
            class_id = student['class_id']
            class_name = student['class_name']
            excel_row = student['excel_row']
            
            # 初始化班级统计
            if class_name not in result['stats']['by_class']:
                result['stats']['by_class'][class_name] = {
                    'total': 0,
                    'valid': 0,
                    'subjects': {}
                }
            result['stats']['by_class'][class_name]['total'] += 1
            
            # 验证每个学科的成绩和权限
            valid_grades = {}
            has_valid_grade = False
            
            for subject_name in detected_subjects:
                db_field = self.subject_mapping[subject_name]
                
                # 初始化学科统计
                if subject_name not in result['stats']['by_subject']:
                    result['stats']['by_subject'][subject_name] = {
                        'total': 0,
                        'valid': 0,
                        'invalid': 0,
                        'no_permission': 0
                    }
                
                # 获取成绩值
                grade_value = str(excel_row[subject_name]).strip() if pd.notna(excel_row[subject_name]) else ''
                
                if not grade_value:
                    continue  # 空值跳过
                
                result['stats']['by_subject'][subject_name]['total'] += 1
                
                # 检查权限
                logger.info(f"准备检查权限 - 行{row_num}: class_id={class_id} (type={type(class_id)}), subject={subject_name}")
                logger.info(f"permissions['teaching_map'] = {permissions['teaching_map']}")
                
                if not self._check_subject_permission(permissions, class_id, subject_name):
                    result['errors'].append(
                        f'❌ 第{row_num}行：您没有权限导入班级 {class_name} 的 {subject_name} 成绩'
                    )
                    result['stats']['by_subject'][subject_name]['no_permission'] += 1
                    result['stats']['permission_denied'] += 1
                    continue
                
                # 标准化成绩值
                normalized_grade = self._normalize_grade(grade_value)
                
                # 验证成绩值
                if normalized_grade not in self.allowed_grades:
                    result['errors'].append(
                        f'❌ 第{row_num}行：{subject_name} 成绩"{grade_value}"无效。'
                        f'允许的值：{", ".join(self.allowed_grades)}'
                    )
                    result['stats']['by_subject'][subject_name]['invalid'] += 1
                    result['stats']['invalid_grades'] += 1
                    continue
                
                # 成绩有效
                valid_grades[db_field] = normalized_grade
                has_valid_grade = True
                result['stats']['by_subject'][subject_name]['valid'] += 1
                
                # 更新班级-学科统计
                if subject_name not in result['stats']['by_class'][class_name]['subjects']:
                    result['stats']['by_class'][class_name]['subjects'][subject_name] = 0
                result['stats']['by_class'][class_name]['subjects'][subject_name] += 1
            
            # 如果有有效成绩，添加到有效记录
            if has_valid_grade:
                result['valid_records'].append({
                    'student_id': student_id,
                    'student_name': student['student_name'],
                    'class_id': class_id,
                    'class_name': class_name,
                    'grades': valid_grades,
                    'row_num': row_num
                })
                result['stats']['valid_rows'] += 1
                result['stats']['by_class'][class_name]['valid'] += 1
            else:
                result['warnings'].append(
                    f'⚠️ 第{row_num}行：学号 {student_id} ({student["student_name"]}) 没有有效的成绩数据'
                )
        
        return result
    
    def _check_subject_permission(self, permissions, class_id, subject_name):
        """检查是否有权限导入指定班级的指定学科"""
        if permissions['can_import_all']:
            return True
        
        class_id_str = str(class_id)
        
        logger.info(f"检查权限: class_id={class_id}, class_id_str={class_id_str}, subject={subject_name}")
        logger.info(f"teaching_map keys: {list(permissions['teaching_map'].keys())}")
        logger.info(f"teaching_map: {permissions['teaching_map']}")
        
        if class_id_str not in permissions['teaching_map']:
            logger.warning(f"班级 {class_id_str} 不在 teaching_map 中")
            return False
        
        has_permission = subject_name in permissions['teaching_map'][class_id_str]
        logger.info(f"班级 {class_id_str} 的学科列表: {permissions['teaching_map'][class_id_str]}")
        logger.info(f"是否有 {subject_name} 权限: {has_permission}")
        
        return has_permission
    
    def _normalize_grade(self, grade_value):
        """标准化成绩值"""
        grade_value = str(grade_value).strip()
        
        # 直接匹配
        if grade_value in self.allowed_grades:
            return grade_value
        
        # 使用映射表转换
        if grade_value in self.grade_mapping:
            return self.grade_mapping[grade_value]
        
        return grade_value  # 返回原值，由调用者判断是否有效
    
    def preview_import(self, file_path, user, semester="上学期"):
        """
        预览导入 - 完整的验证和预览
        
        Returns:
            dict: {
                'status': 'ok' | 'error',
                'message': str,
                'permissions': {权限信息},
                'validation': {验证结果},
                'preview_data': {预览数据},
                'html_preview': str,
                'file_path': str
            }
        """
        try:
            # 1. 获取用户权限
            permissions = self.get_user_permissions(user)
            logger.info(f"用户 {user.username} 的权限: {permissions}")
            
            # 2. 读取Excel文件
            if not os.path.exists(file_path):
                return {
                    'status': 'error',
                    'message': f'文件不存在: {file_path}'
                }
            
            df = pd.read_excel(file_path)
            logger.info(f"读取Excel文件，共 {len(df)} 行数据")
            
            # 3. 验证Excel结构
            structure_validation = self.validate_excel_structure(df)
            if not structure_validation['valid']:
                return {
                    'status': 'error',
                    'message': '文件格式验证失败',
                    'errors': structure_validation['errors'],
                    'warnings': structure_validation['warnings']
                }
            
            # 4. 匹配学生
            student_matching = self.match_students_with_database(df, permissions)
            logger.info(f"学生匹配结果 - matched: {len(student_matching['matched'])}, errors: {len(student_matching['errors'])}, warnings: {len(student_matching['warnings'])}")
            if student_matching['errors']:
                logger.error(f"学生匹配错误列表: {student_matching['errors'][:5]}")  # 只显示前5个错误
            if student_matching['matched']:
                logger.info(f"第一个匹配的学生: {student_matching['matched'][0]}")
            
            # 5. 验证成绩和权限
            grade_validation = self.validate_grades_and_permissions(
                student_matching['matched'],
                structure_validation['detected_subjects'],
                permissions
            )
            
            # 6. 汇总所有错误和警告
            all_errors = (
                structure_validation['errors'] +
                student_matching['errors'] +
                grade_validation['errors']
            )
            
            all_warnings = (
                structure_validation['warnings'] +
                student_matching['warnings'] +
                grade_validation['warnings']
            )
            
            # 7. 生成预览HTML
            html_preview = self._generate_preview_html(
                permissions,
                structure_validation,
                grade_validation,
                all_errors,
                all_warnings
            )
            
            # 8. 生成结果消息
            stats = grade_validation['stats']
            if stats['valid_rows'] == 0:
                status = 'error'
                message = '没有可导入的有效数据'
            else:
                status = 'ok'
                message = f'检测到 {stats["valid_rows"]} 条有效记录，涉及 {len(stats["by_class"])} 个班级，{len(stats["by_subject"])} 个学科'
                if all_errors:
                    message += f'，{len(all_errors)} 个错误'
                if all_warnings:
                    message += f'，{len(all_warnings)} 个警告'
            
            return {
                'status': status,
                'message': message,
                'permissions': permissions,
                'validation': {
                    'structure': structure_validation,
                    'students': student_matching,
                    'grades': grade_validation
                },
                'preview_data': grade_validation['valid_records'],
                'errors': all_errors,
                'warnings': all_warnings,
                'stats': stats,
                'html_preview': html_preview,
                'file_path': file_path,
                'semester': semester
            }
            
        except Exception as e:
            logger.error(f"预览导入时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f'预览导入时出错: {str(e)}'
            }
    
    def _generate_preview_html(self, permissions, structure_validation, grade_validation, errors, warnings):
        """生成预览HTML"""
        html = []
        
        # 1. 用户权限信息
        html.append('<div class="alert alert-info mb-3">')
        html.append('<h5><i class="bx bx-user-circle"></i> 当前用户权限</h5>')
        html.append(f'<p><strong>角色：</strong>{permissions["role"]}</p>')
        
        if permissions['can_import_all']:
            html.append('<p><strong>权限：</strong>可以导入所有班级的所有学科</p>')
        else:
            html.append(f'<p><strong>可导入班级：</strong>{len(permissions["accessible_classes"])} 个</p>')
            html.append('<div class="mt-2">')
            for class_id in permissions['accessible_classes']:
                subjects = permissions['teaching_map'].get(str(class_id), [])
                html.append(f'<div class="mb-1">• 班级 {class_id}: {", ".join(subjects) if subjects else "所有学科"}</div>')
            html.append('</div>')
        
        html.append('</div>')
        
        # 2. 检测到的学科
        if structure_validation['detected_subjects']:
            html.append('<div class="alert alert-success mb-3">')
            html.append(f'<h5><i class="bx bx-check-circle"></i> 检测到 {len(structure_validation["detected_subjects"])} 个学科</h5>')
            html.append('<div style="display: flex; flex-wrap: wrap; gap: 8px;">')
            for subject in structure_validation['detected_subjects']:
                html.append(
                    f'<span class="badge bg-success" style="font-size: 14px; padding: 6px 12px;">{subject}</span>'
                )
            html.append('</div>')
            html.append('</div>')
        
        # 3. 统计信息
        stats = grade_validation['stats']
        if stats['valid_rows'] > 0:
            html.append('<div class="alert alert-primary mb-3">')
            html.append('<h5><i class="bx bx-bar-chart"></i> 导入统计</h5>')
            html.append(f'<p><strong>总行数：</strong>{stats["total_rows"]} 行</p>')
            html.append(f'<p><strong>有效记录：</strong>{stats["valid_rows"]} 条</p>')
            
            # 按班级统计
            if stats['by_class']:
                html.append('<p class="mt-3"><strong>按班级统计：</strong></p>')
                html.append('<table class="table table-sm table-bordered">')
                html.append('<thead><tr><th>班级</th><th>学生数</th><th>学科</th></tr></thead>')
                html.append('<tbody>')
                for class_name, class_stats in stats['by_class'].items():
                    if class_stats['valid'] > 0:
                        subjects_str = ', '.join([
                            f'{subj}({count})' 
                            for subj, count in class_stats['subjects'].items()
                        ])
                        html.append(f'<tr><td>{class_name}</td><td>{class_stats["valid"]}</td><td>{subjects_str}</td></tr>')
                html.append('</tbody></table>')
            
            html.append('</div>')
        
        # 4. 错误信息
        if errors:
            html.append('<div class="alert alert-danger mb-3">')
            html.append(f'<h5><i class="bx bx-error-circle"></i> 发现 {len(errors)} 个错误</h5>')
            html.append('<ul class="mb-0">')
            for error in errors[:20]:  # 最多显示20个错误
                html.append(f'<li>{error}</li>')
            if len(errors) > 20:
                html.append(f'<li>...还有 {len(errors) - 20} 个错误未显示</li>')
            html.append('</ul>')
            html.append('</div>')
        
        # 5. 警告信息
        if warnings:
            html.append('<div class="alert alert-warning mb-3">')
            html.append(f'<h5><i class="bx bx-error"></i> {len(warnings)} 个警告</h5>')
            html.append('<ul class="mb-0">')
            for warning in warnings[:10]:  # 最多显示10个警告
                html.append(f'<li>{warning}</li>')
            if len(warnings) > 10:
                html.append(f'<li>...还有 {len(warnings) - 10} 个警告未显示</li>')
            html.append('</ul>')
            html.append('</div>')
        
        # 6. 预览数据表格
        if grade_validation['valid_records']:
            html.append('<div class="table-responsive">')
            html.append('<table class="table table-striped table-hover table-sm">')
            html.append('<thead><tr>')
            html.append('<th>行号</th><th>学号</th><th>姓名</th><th>班级</th>')
            
            # 动态添加学科列
            for subject in structure_validation['detected_subjects']:
                html.append(f'<th>{subject}</th>')
            
            html.append('</tr></thead><tbody>')
            
            # 最多显示50条记录
            for record in grade_validation['valid_records'][:50]:
                html.append('<tr>')
                html.append(f'<td>{record["row_num"]}</td>')
                html.append(f'<td>{record["student_id"]}</td>')
                html.append(f'<td>{record["student_name"]}</td>')
                html.append(f'<td>{record["class_name"]}</td>')
                
                for subject in structure_validation['detected_subjects']:
                    db_field = self.subject_mapping[subject]
                    grade = record['grades'].get(db_field, '-')
                    html.append(f'<td>{grade}</td>')
                
                html.append('</tr>')
            
            if len(grade_validation['valid_records']) > 50:
                html.append(f'<tr><td colspan="{4 + len(structure_validation["detected_subjects"])}" class="text-center">')
                html.append(f'...还有 {len(grade_validation["valid_records"]) - 50} 条记录未显示')
                html.append('</td></tr>')
            
            html.append('</tbody></table>')
            html.append('</div>')
        
        return '\n'.join(html)
    
    def confirm_import(self, preview_result):
        """
        确认导入 - 将预览的数据写入数据库
        
        Args:
            preview_result: preview_import 返回的结果
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if preview_result['status'] != 'ok':
                return False, '预览数据无效，无法导入'
            
            # 兼容两种格式：新版使用preview_data，旧版使用grades
            valid_records = preview_result.get('preview_data') or preview_result.get('grades')
            
            if not valid_records:
                return False, '没有可导入的数据'
            
            semester = preview_result.get('semester', '上学期')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            success_count = 0
            fail_count = 0
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for record in valid_records:
                try:
                    student_id = record['student_id']
                    class_id = record['class_id']
                    
                    # 获取成绩数据
                    grades = record.get('grades', {})
                    
                    if not grades:
                        logger.warning(f"学生 {student_id} 没有成绩数据")
                        continue
                    
                    # 构建UPDATE语句
                    set_clauses = ['semester = ?', 'updated_at = ?']
                    values = [semester, now]
                    
                    for db_field, grade_value in grades.items():
                        set_clauses.append(f'{db_field} = ?')
                        values.append(grade_value)
                    
                    values.extend([student_id, class_id])
                    
                    query = f'''
                        UPDATE students 
                        SET {', '.join(set_clauses)}
                        WHERE id = ? AND class_id = ?
                    '''
                    
                    cursor.execute(query, values)
                    
                    if cursor.rowcount > 0:
                        success_count += 1
                    else:
                        fail_count += 1
                        logger.warning(f"更新学生 {student_id} 失败：未找到记录")
                
                except Exception as e:
                    fail_count += 1
                    logger.error(f"导入学生 {student_id} 的成绩时出错: {str(e)}")
            
            conn.commit()
            conn.close()
            
            # 删除临时文件
            try:
                file_path = preview_result.get('file_path')
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {str(e)}")
            
            # 生成结果消息
            message = f'成功导入 {success_count} 条成绩记录'
            
            # 尝试从stats获取统计信息（新版格式）
            stats = preview_result.get('stats')
            if stats and stats.get('by_class'):
                class_summary = ', '.join([
                    f'{name}({info["valid"]}人)'
                    for name, info in stats['by_class'].items()
                    if info['valid'] > 0
                ])
                if class_summary:
                    message += f'，涉及班级：{class_summary}'
            
            if stats and stats.get('by_subject'):
                subject_summary = ', '.join([
                    f'{name}({info["valid"]}条)'
                    for name, info in stats['by_subject'].items()
                    if info['valid'] > 0
                ])
                if subject_summary:
                    message += f'，涉及学科：{subject_summary}'
            
            if fail_count > 0:
                message += f'，{fail_count} 条失败'
            
            return True, message
            
        except Exception as e:
            logger.error(f"确认导入时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return False, f'导入失败: {str(e)}'
