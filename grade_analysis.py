#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
成绩分析模块，包含成绩分析相关的API路由和功能
"""

import os
import json
import sqlite3
import traceback
import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app as app, session, send_file, send_from_directory
import openpyxl
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from utils.class_filter import class_filter, user_can_access
import logging
import pandas as pd
import numpy as np
import io
import time
from markupsafe import escape

# 配置日志
logger = logging.getLogger(__name__)

# 成绩分析蓝图
grade_analysis_bp = Blueprint('grade_analysis', __name__)

# 配置
UPLOAD_FOLDER = 'uploads/exams'
DATABASE = 'students.db'

# 初始化成绩分析模块
def init_grade_analysis(app):
    """初始化成绩分析模块"""
    logger.info("初始化成绩分析模块")
    
    # 创建上传目录
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 创建考试信息表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_name TEXT NOT NULL,
        exam_date TEXT NOT NULL,
        class_id INTEGER NOT NULL,
        subjects TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    ''')
    
    # 创建考试成绩表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exam_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        student_id TEXT NOT NULL,
        student_name TEXT NOT NULL,
        class_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        score REAL NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
        UNIQUE (exam_id, student_id, subject)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("成绩分析模块初始化完成")

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # 启用外键约束
    return conn

# 获取所有考试列表
@grade_analysis_bp.route('/api/exams', methods=['GET'])
@login_required
def get_exams():
    try:
        class_id = request.args.get('class_id')
        
        # 班主任自动使用自己的班级ID
        if not current_user.is_admin:
            if not current_user.class_id:
                return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法查看考试数据'}), 403
            class_id = current_user.class_id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询条件
        params = []
        query = "SELECT * FROM exams"
        
        if class_id:
            query += " WHERE class_id = ?"
            params.append(class_id)
        
        query += " ORDER BY exam_date DESC"
        
        cursor.execute(query, params)
        exams = [dict(row) for row in cursor.fetchall()]
        
        # 解析subjects字段为列表
        for exam in exams:
            exam['subjects'] = json.loads(exam['subjects'])
        
        return jsonify({
            'status': 'ok',
            'exams': exams
        })
    except Exception as e:
        logger.error(f"获取考试列表时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取考试列表失败: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 创建考试
@grade_analysis_bp.route('/api/exams', methods=['POST'])
@login_required
def create_exam():
    try:
        data = request.json
        
        # 验证必填字段
        required_fields = ['exam_name', 'exam_date', 'subjects']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'缺少字段: {field}'}), 400
        
        # 班主任使用自己的班级ID
        if not current_user.is_admin:
            if not current_user.class_id:
                return jsonify({'status': 'error', 'message': '您尚未被分配班级，无法创建考试'}), 403
            class_id = current_user.class_id
        else:
            class_id = data.get('class_id')
            if not class_id:
                return jsonify({'status': 'error', 'message': '管理员需提供班级ID参数'}), 400
        
        # 准备保存数据
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 序列化subjects字段
        subjects_json = json.dumps(data['subjects'], ensure_ascii=False)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 插入考试数据
        cursor.execute('''
        INSERT INTO exams (exam_name, exam_date, class_id, subjects, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['exam_name'], data['exam_date'], class_id, subjects_json, now, now))
        
        # 获取新创建的考试ID
        exam_id = cursor.lastrowid
        
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'message': '考试创建成功',
            'exam_id': exam_id
        })
    except Exception as e:
        logger.error(f"创建考试时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'创建考试失败: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 获取考试详情
@grade_analysis_bp.route('/api/exams/<int:exam_id>', methods=['GET'])
@login_required
def get_exam_detail(exam_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取考试信息
        cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
        exam = cursor.fetchone()
        
        if not exam:
            return jsonify({'status': 'error', 'message': '考试不存在'}), 404
        
        exam_dict = dict(exam)
        exam_dict['subjects'] = json.loads(exam_dict['subjects'])
        
        # 检查权限
        if not current_user.is_admin and current_user.class_id != exam_dict['class_id']:
            return jsonify({'status': 'error', 'message': '您无权查看此考试'}), 403
            
        # 获取班级信息
        class_id = exam_dict['class_id']
        cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
        class_info = cursor.fetchone()
        class_name = class_info['class_name'] if class_info else f"班级ID: {class_id}"
        
        # 获取班级所有学生数量
        cursor.execute("SELECT COUNT(*) as count FROM students WHERE class_id = ?", (class_id,))
        class_student_count = cursor.fetchone()['count']
        logger.info(f"班级 {class_name}(ID:{class_id}) 的实际学生总数: {class_student_count}")
        
        # 获取参加此次考试的所有记录
        cursor.execute('''
        SELECT s.*, students.name as student_name, students.class as class_name
        FROM exam_scores s
        LEFT JOIN students ON s.student_id = students.id
        WHERE s.exam_id = ? AND s.class_id = ?
        ORDER BY s.student_id, s.subject
        ''', (exam_id, class_id))
        
        all_scores = [dict(row) for row in cursor.fetchall()]
        total_score_records = len(all_scores)
        logger.info(f"考试ID: {exam_id}, 班级ID: {class_id} 的总成绩记录数: {total_score_records}")
        
        # 获取参加考试的学生ID集合
        student_ids = set(score['student_id'] for score in all_scores)
        actual_student_count = len(student_ids)
        logger.info(f"实际参加考试的学生数: {actual_student_count}, 学生ID列表: {student_ids}")
        
        # 按学科组织成绩数据
        scores_by_subject = {}
        for score in all_scores:
            subject = score['subject']
            if subject not in scores_by_subject:
                scores_by_subject[subject] = []
            scores_by_subject[subject].append(score)
        
        # 记录每个学科的记录数
        logger.info(f"共有 {len(scores_by_subject)} 个学科的成绩")
        for subject, subject_scores in scores_by_subject.items():
            subject_student_ids = [s['student_id'] for s in subject_scores]
            unique_student_ids = set(subject_student_ids)
            logger.info(f"学科: {subject}, 记录数: {len(subject_scores)}, 去重后学生数: {len(unique_student_ids)}")
            
            if len(subject_student_ids) != len(unique_student_ids):
                # 发现重复记录，需要处理
                logger.warning(f"⚠️ {subject}科目中存在重复学生记录！总记录数: {len(subject_scores)}, 去重后: {len(unique_student_ids)}")
                # 按学生ID分组，保留最新的成绩记录
                unique_scores = {}
                for score in subject_scores:
                    student_id = score['student_id']
                    if student_id not in unique_scores or score['updated_at'] > unique_scores[student_id]['updated_at']:
                        unique_scores[student_id] = score
                
                # 更新为去重后的成绩列表
                scores_by_subject[subject] = list(unique_scores.values())
                logger.info(f"去重后 {subject} 科目的记录数: {len(scores_by_subject[subject])}")
        
        # 计算每个学科的统计信息
        stats = {}
        for subject, subject_scores in scores_by_subject.items():
            # 提取分数列表 - 确保每个学生只计算一次
            subject_student_ids = set()
            valid_scores = []
            
            for score in subject_scores:
                student_id = score['student_id']
                if student_id in subject_student_ids:
                    continue  # 跳过已经计算过的学生
                
                subject_student_ids.add(student_id)
                score_value = score['score']
                
                # 验证分数是否有效
                if 0 <= score_value <= 100:
                    valid_scores.append(score_value)
                else:
                    logger.warning(f"⚠️ 发现无效分数: 科目 {subject}, 学生 {score['student_name']}(ID:{student_id}), 分数: {score_value}")
            
            # 获取该科目的学生总数 (去重后)
            total_students = len(valid_scores)
            logger.info(f"科目 {subject} 的有效成绩总数: {total_students}")
            
            # 检查有效学生人数
            if total_students == 0:
                logger.warning(f"⚠️ 科目 {subject} 没有有效成绩！")
                # 设置默认统计数据
                stats[subject] = {
                    'average': 0,
                    'max': 0,
                    'min': 0,
                    'excellent_rate': 0,
                    'pass_rate': 0,
                    'excellent_threshold': 90,
                    'score_distribution': {'0-59': 0, '60-69': 0, '70-79': 0, '80-89': 0, '90-100': 0},
                    'total_students': 0,
                    'class_student_count': class_student_count
                }
                continue
            
            # 判断年级
            class_name = class_name if class_name else ""
            
            # 根据年级确定优秀标准
            excellent_threshold = 90  # 默认优秀标准
            if "一年级" in class_name or "二年级" in class_name:
                excellent_threshold = 90
            elif "三年级" in class_name or "四年级" in class_name:
                excellent_threshold = 85
            elif "五年级" in class_name or "六年级" in class_name:
                excellent_threshold = 80
            
            # 计算各分数段人数 - 确保不会超过班级总人数
            below_60 = min(sum(1 for s in valid_scores if s < 60), class_student_count)
            from_60_to_69 = min(sum(1 for s in valid_scores if 60 <= s < 70), class_student_count)
            from_70_to_79 = min(sum(1 for s in valid_scores if 70 <= s < 80), class_student_count)
            from_80_to_89 = min(sum(1 for s in valid_scores if 80 <= s < 90), class_student_count)
            from_90_to_100 = min(sum(1 for s in valid_scores if s >= 90), class_student_count)
            
            # 记录详细的分段信息用于调试
            # 计算各分数段人数
            below_60 = sum(1 for s in valid_scores if s < 60)
            from_60_to_69 = sum(1 for s in valid_scores if 60 <= s < 70)
            from_70_to_79 = sum(1 for s in valid_scores if 70 <= s < 80)
            from_80_to_89 = sum(1 for s in valid_scores if 80 <= s < 90)
            from_90_to_100 = sum(1 for s in valid_scores if s >= 90)
            
            # 记录详细的分段信息用于调试
            logger.info(f"科目: {subject}, 总人数: {total_students}")
            logger.info(f"  0-59分: {below_60}人")
            logger.info(f"  60-69分: {from_60_to_69}人")
            logger.info(f"  70-79分: {from_70_to_79}人")
            logger.info(f"  80-89分: {from_80_to_89}人")
            logger.info(f"  90-100分: {from_90_to_100}人")
            
            # 验证总和是否等于学生总数
            total_count = below_60 + from_60_to_69 + from_70_to_79 + from_80_to_89 + from_90_to_100
            if total_count != total_students:
                logger.error(f"❌ 分数段统计总人数({total_count})与有效成绩总数({total_students})不匹配！科目: {subject}")
            
            # 计算及格率和优秀率
            pass_count = from_60_to_69 + from_70_to_79 + from_80_to_89 + from_90_to_100
            pass_rate = round(pass_count / total_students * 100, 2) if total_students > 0 else 0
            
            # 根据不同年级的优秀标准计算优秀人数
            excellent_count = 0
            if excellent_threshold == 90:
                excellent_count = from_90_to_100  # 90分及以上
            elif excellent_threshold == 85:
                # 85分及以上，即部分80-89分段和全部90-100分段
                excellent_count = from_90_to_100 + sum(1 for s in valid_scores if 85 <= s < 90)
            elif excellent_threshold == 80:
                # 80分及以上，即全部80-89分段和全部90-100分段
                excellent_count = from_80_to_89 + from_90_to_100
            
            excellent_rate = round(excellent_count / total_students * 100, 2) if total_students > 0 else 0
            
            # 检查统计数据的合理性
            if total_students > class_student_count:
                logger.error(f"❌ 科目 {subject} 的学生人数({total_students})超过了班级总人数({class_student_count})！")
                # 可能需要做进一步处理，例如限制最大人数
            
            # 计算统计数据
            stats[subject] = {
                'average': round(sum(valid_scores) / total_students, 2) if total_students > 0 else 0,
                'max': max(valid_scores) if valid_scores else 0,
                'min': min(valid_scores) if valid_scores else 0,
                'excellent_rate': excellent_rate,
                'pass_rate': pass_rate,
                'excellent_threshold': excellent_threshold,
                'score_distribution': {
                    '0-59': below_60,
                    '60-69': from_60_to_69,
                    '70-79': from_70_to_79,
                    '80-89': from_80_to_89,
                    '90-100': from_90_to_100
                },
                'total_students': total_students,
                'class_student_count': class_student_count  # 添加班级总人数用于前端展示
            }
        
        return jsonify({
            'status': 'ok',
            'exam': exam_dict,
            'scores': all_scores,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"获取考试详情时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'获取考试详情失败: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 上传考试成绩
@grade_analysis_bp.route('/api/exams/<int:exam_id>/scores', methods=['POST'])
@login_required
def upload_scores(exam_id):
    try:
        # 检查文件是否存在
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': '没有上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择文件'}), 400
        
        # 检查文件格式
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'status': 'error', 'message': '只支持Excel文件(.xlsx, .xls)'}), 400
        
        # 获取考试信息
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
        exam = cursor.fetchone()
        
        if not exam:
            return jsonify({'status': 'error', 'message': '考试不存在'}), 404
        
        exam_dict = dict(exam)
        
        # 检查权限
        if not current_user.is_admin and current_user.class_id != exam_dict['class_id']:
            return jsonify({'status': 'error', 'message': '您无权上传此考试成绩'}), 403
        
        # 保存文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 确保上传目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file.save(file_path)
        
        # 解析Excel文件
        df = pd.read_excel(file_path)
        
        # 检查必要的列是否存在
        required_columns = ['学号', '姓名']
        subjects_list = json.loads(exam_dict['subjects'])
        
        for col in required_columns:
            if col not in df.columns:
                return jsonify({'status': 'error', 'message': f'缺少必要的列: {col}'}), 400
        
        # 检查学科列是否存在
        missing_subjects = [subject for subject in subjects_list if subject not in df.columns]
        if missing_subjects:
            return jsonify({'status': 'error', 'message': f'缺少学科列: {", ".join(missing_subjects)}'}), 400
        
        # 准备批量插入数据
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows_to_insert = []
        
        for _, row in df.iterrows():
            student_id = str(row['学号'])
            student_name = row['姓名']
            
            # 检查学生是否属于该班级
            cursor.execute("SELECT id FROM students WHERE id = ? AND class_id = ?", 
                          (student_id, exam_dict['class_id']))
            student = cursor.fetchone()
            
            if not student:
                continue  # 跳过不属于该班级的学生
            
            # 为每个学科添加一条记录
            for subject in subjects_list:
                if pd.notna(row[subject]):  # 检查成绩是否有效
                    score = float(row[subject])
                    rows_to_insert.append((
                        exam_id, student_id, student_name, exam_dict['class_id'],
                        subject, score, now, now
                    ))
        
        # 批量插入成绩
        cursor.executemany('''
        INSERT OR REPLACE INTO exam_scores 
        (exam_id, student_id, student_name, class_id, subject, score, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', rows_to_insert)
        
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'message': '成绩上传成功',
            'records_count': len(rows_to_insert)
        })
    except Exception as e:
        logger.error(f"上传考试成绩时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'上传考试成绩失败: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 预览考试成绩Excel
@grade_analysis_bp.route('/api/exams/preview', methods=['POST'])
@login_required
def preview_scores():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': '没有上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择文件'}), 400
        
        # 检查文件格式
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'status': 'error', 'message': '只支持Excel文件(.xlsx, .xls)'}), 400
        
        # 保存文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 确保上传目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file.save(file_path)
        
        # 解析Excel文件
        df = pd.read_excel(file_path)
        
        # 检查必要的列是否存在
        required_columns = ['学号', '姓名']
        for col in required_columns:
            if col not in df.columns:
                return jsonify({'status': 'error', 'message': f'缺少必要的列: {col}'}), 400
        
        # 提取学科列(除了学号和姓名)
        subject_columns = [col for col in df.columns if col not in required_columns]
        
        # 构建预览数据
        preview_data = []
        for _, row in df.iterrows():
            student_data = {
                'student_id': str(row['学号']),
                'student_name': row['姓名'],
                'scores': {}
            }
            
            for subject in subject_columns:
                if pd.notna(row[subject]):
                    student_data['scores'][subject] = float(row[subject])
                else:
                    student_data['scores'][subject] = None
            
            preview_data.append(student_data)
        
        return jsonify({
            'status': 'ok',
            'preview': preview_data,
            'subjects': subject_columns,
            'file_path': file_path
        })
    except Exception as e:
        logger.error(f"预览考试成绩时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'预览考试成绩失败: {str(e)}'
        }), 500
    finally:
        pass  # 不关闭连接，因为没有使用数据库

# 下载成绩模板
@grade_analysis_bp.route('/api/exams/template', methods=['GET'])
@login_required
def download_template():
    try:
        # 获取班级ID
        class_id = request.args.get('class_id')
        subjects = request.args.get('subjects', '').split(',')
        
        if not class_id:
            if not current_user.is_admin:
                if not current_user.class_id:
                    return jsonify({'status': 'error', 'message': '您尚未被分配班级'}), 403
                class_id = current_user.class_id
            else:
                return jsonify({'status': 'error', 'message': '管理员需提供班级ID参数'}), 400
        
        # 获取班级学生信息
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM students WHERE class_id = ?", (class_id,))
        students = cursor.fetchall()
        
        # 创建Excel模板
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "成绩导入模板"
        
        # 添加标题行
        headers = ['学号', '姓名'] + subjects
        for i, header in enumerate(headers, 1):
            ws.cell(row=1, column=i, value=header)
        
        # 添加学生数据
        for i, student in enumerate(students, 2):
            ws.cell(row=i, column=1, value=student['id'])
            ws.cell(row=i, column=2, value=student['name'])
        
        # 保存到内存
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # 返回文件
        return send_file(
            output,
            as_attachment=True,
            download_name=f"成绩导入模板_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"下载成绩模板时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'下载成绩模板失败: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 获取班级学生列表
@grade_analysis_bp.route('/api/exams/students', methods=['GET'])
@login_required
def get_class_students():
    try:
        class_id = request.args.get('class_id')
        
        if not class_id:
            if not current_user.is_admin:
                if not current_user.class_id:
                    return jsonify({'status': 'error', 'message': '您尚未被分配班级'}), 403
                class_id = current_user.class_id
            else:
                return jsonify({'status': 'error', 'message': '管理员需提供班级ID参数'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM students WHERE class_id = ? ORDER BY id", (class_id,))
        students = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'status': 'ok',
            'students': students
        })
    except Exception as e:
        logger.error(f"获取班级学生列表时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取班级学生列表失败: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 删除考试
@grade_analysis_bp.route('/api/exams/<int:exam_id>', methods=['DELETE'])
@login_required
def delete_exam(exam_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取考试信息
        cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
        exam = cursor.fetchone()
        
        if not exam:
            return jsonify({'status': 'error', 'message': '考试不存在'}), 404
        
        # 检查权限
        if not current_user.is_admin and current_user.class_id != exam['class_id']:
            return jsonify({'status': 'error', 'message': '您无权删除此考试'}), 403
        
        # 删除考试及相关成绩
        cursor.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
        
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'message': '考试删除成功'
        })
    except Exception as e:
        logger.error(f"删除考试时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'删除考试失败: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 更新考试
@grade_analysis_bp.route('/api/exams/<int:exam_id>', methods=['PUT'])
@login_required
def update_exam(exam_id):
    try:
        data = request.json
        
        # 验证必填字段
        required_fields = ['exam_name', 'exam_date', 'subjects']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'缺少字段: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取考试信息
        cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
        exam = cursor.fetchone()
        
        if not exam:
            return jsonify({'status': 'error', 'message': '考试不存在'}), 404
        
        # 检查权限
        if not current_user.is_admin and current_user.class_id != exam['class_id']:
            return jsonify({'status': 'error', 'message': '您无权修改此考试'}), 403
        
        # 准备更新数据
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 序列化subjects字段
        subjects_json = json.dumps(data['subjects'], ensure_ascii=False)
        
        # 更新考试数据
        cursor.execute('''
        UPDATE exams 
        SET exam_name = ?, exam_date = ?, subjects = ?, updated_at = ?
        WHERE id = ?
        ''', (data['exam_name'], data['exam_date'], subjects_json, now, exam_id))
        
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'message': '考试更新成功'
        })
    except Exception as e:
        logger.error(f"更新考试时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'更新考试失败: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close() 