#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学科管理模块
"""

import sqlite3
import datetime
import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

# 配置日志
logger = logging.getLogger(__name__)

# 学科蓝图
subjects_bp = Blueprint('subjects', __name__)

# 配置
DATABASE = 'students.db'

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

# 初始化学科表
def init_subjects():
    """初始化学科表和教师任教表"""
    logger.info("初始化学科表")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 创建学科表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建教师任教学科关联表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS teacher_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            UNIQUE(teacher_id, subject_id)
        )
        ''')
        
        conn.commit()
        
        # 检查是否有默认学科，如果没有则添加
        cursor.execute("SELECT COUNT(*) FROM subjects")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("添加默认学科")
            default_subjects = [
                ('语文', '语文学科'),
                ('数学', '数学学科'),
                ('英语', '英语学科'),
                ('物理', '物理学科'),
                ('化学', '化学学科'),
                ('生物', '生物学科'),
                ('政治', '政治学科'),
                ('历史', '历史学科'),
                ('地理', '地理学科'),
                ('体育', '体育学科'),
                ('音乐', '音乐学科'),
                ('美术', '美术学科'),
                ('信息技术', '信息技术学科'),
                ('科学', '科学学科'),
                ('道德与法治', '道德与法治学科')
            ]
            
            for name, desc in default_subjects:
                cursor.execute('''
                INSERT INTO subjects (name, description)
                VALUES (?, ?)
                ''', (name, desc))
            
            conn.commit()
            logger.info(f"成功添加 {len(default_subjects)} 个默认学科")
        
        logger.info("学科表初始化完成")
        
    except Exception as e:
        logger.error(f"初始化学科表时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

# ==================== 学科管理API ====================

@subjects_bp.route('/api/subjects', methods=['GET'])
@login_required
def get_subjects():
    """获取所有学科列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, created_at, updated_at
            FROM subjects
            ORDER BY id ASC
        ''')
        
        subjects = []
        for row in cursor.fetchall():
            subjects.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'subjects': subjects
        })
        
    except Exception as e:
        logger.error(f"获取学科列表时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取学科列表失败: {str(e)}'
        }), 500

@subjects_bp.route('/api/subjects', methods=['POST'])
@login_required
def add_subject():
    """添加新学科"""
    # 只有超级管理员可以添加学科
    if not current_user.is_admin:
        return jsonify({
            'status': 'error',
            'message': '只有超级管理员可以添加学科'
        }), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({
                'status': 'error',
                'message': '学科名称不能为空'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学科是否已存在
        cursor.execute('SELECT id FROM subjects WHERE name = ?', (name,))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '该学科已存在'
            }), 400
        
        # 添加学科
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO subjects (name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (name, description, now, now))
        
        conn.commit()
        subject_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"成功添加学科: {name} (ID: {subject_id})")
        
        return jsonify({
            'status': 'ok',
            'message': '学科添加成功',
            'subject': {
                'id': subject_id,
                'name': name,
                'description': description
            }
        })
        
    except Exception as e:
        logger.error(f"添加学科时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'添加学科失败: {str(e)}'
        }), 500

@subjects_bp.route('/api/subjects/<int:subject_id>', methods=['PUT'])
@login_required
def update_subject(subject_id):
    """更新学科信息"""
    # 只有超级管理员可以更新学科
    if not current_user.is_admin:
        return jsonify({
            'status': 'error',
            'message': '只有超级管理员可以更新学科'
        }), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({
                'status': 'error',
                'message': '学科名称不能为空'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学科是否存在
        cursor.execute('SELECT id FROM subjects WHERE id = ?', (subject_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '学科不存在'
            }), 404
        
        # 检查新名称是否与其他学科重复
        cursor.execute('SELECT id FROM subjects WHERE name = ? AND id != ?', (name, subject_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '该学科名称已被使用'
            }), 400
        
        # 更新学科
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            UPDATE subjects
            SET name = ?, description = ?, updated_at = ?
            WHERE id = ?
        ''', (name, description, now, subject_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功更新学科: {name} (ID: {subject_id})")
        
        return jsonify({
            'status': 'ok',
            'message': '学科更新成功'
        })
        
    except Exception as e:
        logger.error(f"更新学科时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'更新学科失败: {str(e)}'
        }), 500

@subjects_bp.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
@login_required
def delete_subject(subject_id):
    """删除学科"""
    # 只有超级管理员可以删除学科
    if not current_user.is_admin:
        return jsonify({
            'status': 'error',
            'message': '只有超级管理员可以删除学科'
        }), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学科是否存在
        cursor.execute('SELECT name FROM subjects WHERE id = ?', (subject_id,))
        subject = cursor.fetchone()
        if not subject:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '学科不存在'
            }), 404
        
        subject_name = subject['name']
        
        # 检查是否有教师任教该学科
        cursor.execute('SELECT COUNT(*) FROM teacher_subjects WHERE subject_id = ?', (subject_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': f'该学科有 {count} 位教师任教，无法删除'
            }), 400
        
        # 删除学科
        cursor.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"成功删除学科: {subject_name} (ID: {subject_id})")
        
        return jsonify({
            'status': 'ok',
            'message': '学科删除成功'
        })
        
    except Exception as e:
        logger.error(f"删除学科时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'删除学科失败: {str(e)}'
        }), 500

# ==================== 教师任教管理API ====================

@subjects_bp.route('/api/teacher-subjects/<teacher_id>', methods=['GET'])
@login_required
def get_teacher_subjects(teacher_id):
    """获取教师任教的学科列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.name, s.description, ts.created_at
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            WHERE ts.teacher_id = ?
            ORDER BY s.name ASC
        ''', (teacher_id,))
        
        subjects = []
        for row in cursor.fetchall():
            subjects.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'assigned_at': row['created_at']
            })
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'subjects': subjects
        })
        
    except Exception as e:
        logger.error(f"获取教师任教学科时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取教师任教学科失败: {str(e)}'
        }), 500

@subjects_bp.route('/api/teacher-subjects', methods=['POST'])
@login_required
def assign_subject_to_teacher():
    """为教师分配学科"""
    # 只有超级管理员可以分配学科
    if not current_user.is_admin:
        return jsonify({
            'status': 'error',
            'message': '只有超级管理员可以分配学科'
        }), 403
    
    try:
        data = request.get_json()
        teacher_id = data.get('teacher_id')
        subject_id = data.get('subject_id')
        
        if not teacher_id or not subject_id:
            return jsonify({
                'status': 'error',
                'message': '教师ID和学科ID不能为空'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查教师是否存在
        cursor.execute('SELECT username FROM users WHERE id = ?', (teacher_id,))
        teacher = cursor.fetchone()
        if not teacher:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '教师不存在'
            }), 404
        
        # 检查学科是否存在
        cursor.execute('SELECT name FROM subjects WHERE id = ?', (subject_id,))
        subject = cursor.fetchone()
        if not subject:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '学科不存在'
            }), 404
        
        # 检查是否已经分配
        cursor.execute('''
            SELECT id FROM teacher_subjects 
            WHERE teacher_id = ? AND subject_id = ?
        ''', (teacher_id, subject_id))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '该教师已任教此学科'
            }), 400
        
        # 分配学科
        cursor.execute('''
            INSERT INTO teacher_subjects (teacher_id, subject_id)
            VALUES (?, ?)
        ''', (teacher_id, subject_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功为教师 {teacher['username']} 分配学科 {subject['name']}")
        
        return jsonify({
            'status': 'ok',
            'message': '学科分配成功'
        })
        
    except Exception as e:
        logger.error(f"分配学科时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'分配学科失败: {str(e)}'
        }), 500

@subjects_bp.route('/api/teacher-subjects/<teacher_id>/<int:subject_id>', methods=['DELETE'])
@login_required
def remove_subject_from_teacher(teacher_id, subject_id):
    """移除教师的任教学科"""
    # 只有超级管理员可以移除学科
    if not current_user.is_admin:
        return jsonify({
            'status': 'error',
            'message': '只有超级管理员可以移除学科'
        }), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查分配是否存在
        cursor.execute('''
            SELECT id FROM teacher_subjects 
            WHERE teacher_id = ? AND subject_id = ?
        ''', (teacher_id, subject_id))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '该教师未任教此学科'
            }), 404
        
        # 移除学科
        cursor.execute('''
            DELETE FROM teacher_subjects 
            WHERE teacher_id = ? AND subject_id = ?
        ''', (teacher_id, subject_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功移除教师 {teacher_id} 的学科 {subject_id}")
        
        return jsonify({
            'status': 'ok',
            'message': '学科移除成功'
        })
        
    except Exception as e:
        logger.error(f"移除学科时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'移除学科失败: {str(e)}'
        }), 500

# 获取学科的所有任教教师
@subjects_bp.route('/api/subject-teachers/<int:subject_id>', methods=['GET'])
@login_required
def get_subject_teachers(subject_id):
    """获取任教某学科的所有教师"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.username, u.primary_role, c.class_name, ts.created_at
            FROM teacher_subjects ts
            JOIN users u ON ts.teacher_id = u.id
            LEFT JOIN classes c ON u.class_id = c.id
            WHERE ts.subject_id = ?
            ORDER BY u.username ASC
        ''', (subject_id,))
        
        teachers = []
        for row in cursor.fetchall():
            teachers.append({
                'id': row['id'],
                'username': row['username'],
                'primary_role': row['primary_role'] if 'primary_role' in row.keys() else '科任老师',
                'class_name': row['class_name'],
                'assigned_at': row['created_at']
            })
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'teachers': teachers
        })
        
    except Exception as e:
        logger.error(f"获取学科教师时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取学科教师失败: {str(e)}'
        }), 500

# ==================== 教师班级分配 API ====================

# 获取教师任教的班级列表
@subjects_bp.route('/api/teacher-classes/<teacher_id>', methods=['GET'])
@login_required
def get_teacher_classes(teacher_id):
    """获取教师任教的班级和学科列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                ta.id,
                ta.class_id,
                c.class_name,
                s.id as subject_id,
                s.name as subject_name,
                ta.created_at
            FROM teaching_assignments ta
            JOIN classes c ON CAST(ta.class_id AS INTEGER) = c.id
            JOIN subjects s ON ta.subject = s.name
            WHERE ta.teacher_id = ?
            ORDER BY c.class_name, s.name
        ''', (teacher_id,))
        
        assignments = []
        for row in cursor.fetchall():
            assignments.append({
                'id': row['id'],
                'class_id': row['class_id'],
                'class_name': row['class_name'],
                'subject_id': row['subject_id'],
                'subject_name': row['subject_name'],
                'created_at': row['created_at']
            })
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'assignments': assignments
        })
        
    except Exception as e:
        logger.error(f"获取教师班级分配时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取教师班级分配失败: {str(e)}'
        }), 500

# 分配教师到班级和学科
@subjects_bp.route('/api/teacher-classes', methods=['POST'])
@login_required
def assign_teacher_to_classes():
    """分配教师到多个班级的某个学科"""
    try:
        data = request.get_json()
        teacher_id = data.get('teacher_id')
        subject_id = data.get('subject_id')
        class_ids = data.get('class_ids', [])  # 班级ID列表
        
        if not teacher_id or not subject_id or not class_ids:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取学科名称
        cursor.execute('SELECT name FROM subjects WHERE id = ?', (subject_id,))
        subject_row = cursor.fetchone()
        if not subject_row:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '学科不存在'
            }), 404
        
        subject_name = subject_row['name']
        
        # 先删除该教师该学科的所有班级分配
        cursor.execute('''
            DELETE FROM teaching_assignments 
            WHERE teacher_id = ? AND subject = ?
        ''', (teacher_id, subject_name))
        
        # 添加新的班级分配
        success_count = 0
        for class_id in class_ids:
            try:
                cursor.execute('''
                    INSERT INTO teaching_assignments (teacher_id, class_id, subject)
                    VALUES (?, ?, ?)
                ''', (teacher_id, str(class_id), subject_name))
                success_count += 1
            except sqlite3.IntegrityError:
                # 如果已存在，跳过
                logger.warning(f"教师 {teacher_id} 已分配到班级 {class_id} 的学科 {subject_name}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'message': f'成功分配 {success_count} 个班级'
        })
        
    except Exception as e:
        logger.error(f"分配教师班级时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'分配教师班级失败: {str(e)}'
        }), 500

# 移除教师的班级分配
@subjects_bp.route('/api/teacher-classes/<int:assignment_id>', methods=['DELETE'])
@login_required
def remove_teacher_class_assignment(assignment_id):
    """移除教师的某个班级学科分配"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM teaching_assignments WHERE id = ?', (assignment_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '分配记录不存在'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'message': '移除成功'
        })
        
    except Exception as e:
        logger.error(f"移除教师班级分配时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'移除失败: {str(e)}'
        }), 500

# 获取某个班级某个学科的任教教师
@subjects_bp.route('/api/class-subject-teachers/<int:class_id>/<int:subject_id>', methods=['GET'])
@login_required
def get_class_subject_teachers(class_id, subject_id):
    """获取某个班级某个学科的任教教师"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取学科名称
        cursor.execute('SELECT name FROM subjects WHERE id = ?', (subject_id,))
        subject_row = cursor.fetchone()
        if not subject_row:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': '学科不存在'
            }), 404
        
        subject_name = subject_row['name']
        
        cursor.execute('''
            SELECT 
                u.id,
                u.username,
                u.primary_role,
                ta.created_at
            FROM teaching_assignments ta
            JOIN users u ON ta.teacher_id = u.id
            WHERE ta.class_id = ? AND ta.subject = ?
            ORDER BY u.username
        ''', (str(class_id), subject_name))
        
        teachers = []
        for row in cursor.fetchall():
            teachers.append({
                'id': row['id'],
                'username': row['username'],
                'primary_role': row['primary_role'] if 'primary_role' in row.keys() else '科任老师',
                'assigned_at': row['created_at']
            })
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'teachers': teachers
        })
        
    except Exception as e:
        logger.error(f"获取班级学科教师时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取失败: {str(e)}'
        }), 500

# 获取所有教师的分配情况
@subjects_bp.route('/api/all-teacher-assignments', methods=['GET'])
@login_required
def get_all_teacher_assignments():
    """获取所有教师的角色、班级和学科分配情况"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有教师（排除超级管理员）
        cursor.execute('''
            SELECT 
                u.id,
                u.username,
                u.primary_role,
                u.class_id,
                c.class_name
            FROM users u
            LEFT JOIN classes c ON u.class_id = c.id
            WHERE u.is_admin = 0
            ORDER BY u.username
        ''')
        
        teachers = []
        for row in cursor.fetchall():
            teacher_id = row['id']
            teacher_role = row['primary_role'] if row['primary_role'] else '科任老师'
            teacher_class_id = row['class_id']
            teacher_class_name = row['class_name']
            
            # 1. 获取该教师的任教学科（从 teacher_subjects 表）
            cursor.execute('''
                SELECT s.name
                FROM teacher_subjects ts
                JOIN subjects s ON ts.subject_id = s.id
                WHERE ts.teacher_id = ?
                ORDER BY s.name
            ''', (teacher_id,))
            
            teacher_subjects_list = [r['name'] for r in cursor.fetchall()]
            
            # 2. 获取该教师的学科班级分配（从 teaching_assignments 表）
            cursor.execute('''
                SELECT 
                    ta.subject,
                    c.class_name
                FROM teaching_assignments ta
                JOIN classes c ON CAST(ta.class_id AS INTEGER) = c.id
                WHERE ta.teacher_id = ?
                ORDER BY ta.subject, c.class_name
            ''', (teacher_id,))
            
            # 按学科分组班级
            subject_class_map = {}
            for assignment_row in cursor.fetchall():
                subject_name = assignment_row['subject']
                class_name = assignment_row['class_name']
                
                if subject_name not in subject_class_map:
                    subject_class_map[subject_name] = []
                subject_class_map[subject_name].append(class_name)
            
            # 3. 合并两种分配信息
            subject_assignments = []
            
            # 先添加有班级分配的学科
            for subject_name, class_names in subject_class_map.items():
                subject_assignments.append({
                    'subject_name': subject_name,
                    'classes': class_names,
                    'has_class_assignment': True
                })
            
            # 处理只有学科分配但没有班级分配的学科
            assigned_subjects = set(subject_class_map.keys())
            for subject_name in teacher_subjects_list:
                if subject_name not in assigned_subjects:
                    # 如果是正班主任或副班主任，且有分配班级，自动关联到该班级
                    if (teacher_role in ['正班主任', '副班主任']) and teacher_class_id and teacher_class_name:
                        subject_assignments.append({
                            'subject_name': subject_name,
                            'classes': [teacher_class_name],
                            'has_class_assignment': True,
                            'auto_assigned': True  # 标记为自动分配
                        })
                    else:
                        # 其他角色或未分配班级的，显示未分配
                        subject_assignments.append({
                            'subject_name': subject_name,
                            'classes': ['未分配班级'],
                            'has_class_assignment': False
                        })
            
            teachers.append({
                'id': teacher_id,
                'username': row['username'],
                'role': teacher_role,
                'class_id': teacher_class_id,
                'class_name': teacher_class_name,
                'teacher_subjects': teacher_subjects_list,  # 任教学科列表
                'subject_assignments': subject_assignments  # 学科班级分配
            })
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'assignments': teachers
        })
        
    except Exception as e:
        logger.error(f"获取所有教师分配时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'获取失败: {str(e)}'
        }), 500
