# -*- coding: utf-8 -*-
"""
班主任绩效考核管理模块
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import sqlite3
import logging
from datetime import datetime
from functools import wraps
from database import get_db_connection
from utils.permission_checker import require_performance_access

logger = logging.getLogger(__name__)

# 创建蓝图
performance_bp = Blueprint('performance', __name__, url_prefix='/api/performance')

def init_performance():
    """初始化绩效考核模块数据库表"""
    logger.info("初始化绩效考核模块")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 检查users表是否有role字段，没有则添加
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'role' not in columns:
            cursor.execute('''
                ALTER TABLE users ADD COLUMN role TEXT DEFAULT '科任老师'
            ''')
            logger.info("已添加role字段到users表")
        
        # 如果有旧的teacher_type字段，迁移数据
        if 'teacher_type' in columns and 'role' in columns:
            cursor.execute('''
                UPDATE users SET role = teacher_type WHERE teacher_type IS NOT NULL
            ''')
            logger.info("已迁移teacher_type数据到role字段")
        
        # 2. 创建考核项目表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                item_name TEXT NOT NULL,
                weight REAL NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 3. 创建评分人员权限表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_evaluators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER,
                can_evaluate_all INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (item_id) REFERENCES performance_items(id)
            )
        ''')
        
        # 4. 创建评分记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                evaluator_id INTEGER NOT NULL,
                score REAL NOT NULL,
                semester TEXT NOT NULL,
                comments TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users(id),
                FOREIGN KEY (item_id) REFERENCES performance_items(id),
                FOREIGN KEY (evaluator_id) REFERENCES users(id),
                UNIQUE(teacher_id, item_id, evaluator_id, semester)
            )
        ''')
        
        # 5. 创建考核结果汇总表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                semester TEXT NOT NULL,
                total_score REAL,
                rank INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users(id),
                UNIQUE(teacher_id, semester)
            )
        ''')
        
        # 6. 插入默认考核项目（根据截图）
        cursor.execute("SELECT COUNT(*) FROM performance_items")
        if cursor.fetchone()[0] == 0:
            default_items = [
                ('计划总结', '计划总结10%', 10.0, '班级工作计划和总结'),
                ('常规教育', '校行评语5%', 5.0, '校行评语'),
                ('常规教育', '班队课5%', 5.0, '班队课开展情况'),
                ('常规教育', '安全工作5%', 5.0, '安全教育工作'),
                ('常规教育', '礼仪卫生5%', 5.0, '礼仪卫生管理'),
                ('常规教育', '环境卫生10%', 10.0, '环境卫生管理'),
                ('常规教育', '班级建设5%', 5.0, '班级文化建设'),
                ('常规教育', '班级布置5%', 5.0, '班级布置'),
                ('常规教育', '共性成长5%', 5.0, '学生共性成长'),
                ('活动开展', '活动开展10%', 10.0, '班级活动开展'),
                ('活动开展', '大课间活动5%', 5.0, '大课间活动组织'),
                ('家校配合', '家校配合5%', 5.0, '家校沟通配合'),
                ('家校配合', '家校活动5%', 5.0, '家校活动开展'),
                ('家校配合', '家校群管理5%', 5.0, '家校群管理'),
                ('工作态度', '工作态度10%', 10.0, '工作态度评价'),
                ('德育经验', '德育经验3%', 3.0, '德育经验交流'),
                ('承担任务', '承担任务3%', 3.0, '承担额外任务')
            ]
            
            cursor.executemany('''
                INSERT INTO performance_items (category, item_name, weight, description)
                VALUES (?, ?, ?, ?)
            ''', default_items)
            logger.info("已插入默认考核项目")
        
        conn.commit()
        logger.info("绩效考核模块初始化完成")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"初始化绩效考核模块失败: {str(e)}")
        raise
    finally:
        conn.close()

# ==================== 考核项目管理 ====================

@performance_bp.route('/items', methods=['GET'])
@login_required
@require_performance_access
def get_items():
    """获取所有考核项目"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, category, item_name, weight, description, is_active
            FROM performance_items
            ORDER BY category, id
        ''')
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row[0],
                'category': row[1],
                'item_name': row[2],
                'weight': row[3],
                'description': row[4],
                'is_active': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'items': items
        })
        
    except Exception as e:
        logger.error(f"获取考核项目失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@performance_bp.route('/items', methods=['POST'])
@login_required
@require_performance_access
def add_item():
    """添加考核项目"""
    try:
        # 只有超级管理员可以添加考核项目
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有超级管理员可以添加考核项目'}), 403
        data = request.json
        category = data.get('category')
        item_name = data.get('item_name')
        weight = data.get('weight')
        description = data.get('description', '')
        
        if not all([category, item_name, weight]):
            return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_items (category, item_name, weight, description)
            VALUES (?, ?, ?, ?)
        ''', (category, item_name, weight, description))
        
        conn.commit()
        item_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '考核项目添加成功',
            'item_id': item_id
        })
        
    except Exception as e:
        logger.error(f"添加考核项目失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@performance_bp.route('/items/<int:item_id>', methods=['PUT'])
@login_required
@require_performance_access
def update_item(item_id):
    """更新考核项目"""
    try:
        # 只有超级管理员可以更新考核项目
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有超级管理员可以更新考核项目'}), 403
        data = request.json
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE performance_items
            SET category = ?, item_name = ?, weight = ?, description = ?, updated_at = ?
            WHERE id = ?
        ''', (data.get('category'), data.get('item_name'), data.get('weight'),
              data.get('description'), datetime.now().isoformat(), item_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '考核项目更新成功'
        })
        
    except Exception as e:
        logger.error(f"更新考核项目失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@performance_bp.route('/items/<int:item_id>', methods=['DELETE'])
@login_required
@require_performance_access
def delete_item(item_id):
    """删除考核项目（软删除）"""
    try:
        # 只有超级管理员可以删除考核项目
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有超级管理员可以删除考核项目'}), 403
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE performance_items SET is_active = 0 WHERE id = ?
        ''', (item_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '考核项目已删除'
        })
        
    except Exception as e:
        logger.error(f"删除考核项目失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== 评分人员管理 ====================

@performance_bp.route('/evaluators', methods=['GET'])
@login_required
@require_performance_access
def get_evaluators():
    """获取所有评分人员"""
    try:
        # 只有超级管理员可以查看评分人员
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有超级管理员可以查看评分人员'}), 403
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.id, e.user_id, u.username, e.item_id, i.item_name, e.can_evaluate_all
            FROM performance_evaluators e
            JOIN users u ON e.user_id = u.id
            LEFT JOIN performance_items i ON e.item_id = i.id
            ORDER BY u.username
        ''')
        
        evaluators = []
        for row in cursor.fetchall():
            evaluators.append({
                'id': row[0],
                'user_id': row[1],
                'username': row[2],
                'item_id': row[3],
                'item_name': row[4],
                'can_evaluate_all': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'evaluators': evaluators
        })
        
    except Exception as e:
        logger.error(f"获取评分人员失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@performance_bp.route('/evaluators', methods=['POST'])
@login_required
@require_performance_access
def add_evaluator():
    """添加评分人员"""
    try:
        # 只有超级管理员可以添加评分人员
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有超级管理员可以添加评分人员'}), 403
        data = request.json
        user_id = data.get('user_id')
        item_id = data.get('item_id')
        can_evaluate_all = data.get('can_evaluate_all', 0)
        
        if not user_id:
            return jsonify({'status': 'error', 'message': '缺少用户ID'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_evaluators (user_id, item_id, can_evaluate_all)
            VALUES (?, ?, ?)
        ''', (user_id, item_id, can_evaluate_all))
        
        conn.commit()
        evaluator_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '评分人员添加成功',
            'evaluator_id': evaluator_id
        })
        
    except Exception as e:
        logger.error(f"添加评分人员失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@performance_bp.route('/evaluators/<int:evaluator_id>', methods=['DELETE'])
@login_required
@require_performance_access
def delete_evaluator(evaluator_id):
    """删除评分人员"""
    try:
        # 只有超级管理员可以删除评分人员
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有超级管理员可以删除评分人员'}), 403
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM performance_evaluators WHERE id = ?', (evaluator_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '评分人员已删除'
        })
        
    except Exception as e:
        logger.error(f"删除评分人员失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== 评分管理 ====================

@performance_bp.route('/scores', methods=['POST'])
@login_required
@require_performance_access
def submit_score():
    """提交评分"""
    try:
        data = request.json
        teacher_id = data.get('teacher_id')
        item_id = data.get('item_id')
        score = data.get('score')
        semester = data.get('semester')
        comments = data.get('comments', '')
        
        if not all([teacher_id, item_id, score is not None, semester]):
            return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
        
        # 检查评分权限
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not current_user.is_admin:
            cursor.execute('''
                SELECT id FROM performance_evaluators
                WHERE user_id = ? AND (item_id = ? OR can_evaluate_all = 1)
            ''', (current_user.id, item_id))
            
            if not cursor.fetchone():
                conn.close()
                return jsonify({'status': 'error', 'message': '您没有权限评分此项目'}), 403
        
        # 插入或更新评分
        cursor.execute('''
            INSERT INTO performance_scores (teacher_id, item_id, evaluator_id, score, semester, comments)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(teacher_id, item_id, evaluator_id, semester)
            DO UPDATE SET score = ?, comments = ?, updated_at = ?
        ''', (teacher_id, item_id, current_user.id, score, semester, comments,
              score, comments, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '评分提交成功'
        })
        
    except Exception as e:
        logger.error(f"提交评分失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@performance_bp.route('/scores/<semester>', methods=['GET'])
@login_required
@require_performance_access
def get_all_scores(semester):
    """获取某学期所有正班主任的评分矩阵"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有正班主任（排除管理员）
        logger.info(f"获取学期 {semester} 的正班主任评分矩阵")
        cursor.execute('''
            SELECT u.id, u.username, c.class_name
            FROM users u
            LEFT JOIN classes c ON u.class_id = c.id
            WHERE u.primary_role = '正班主任' AND u.is_admin = 0
            ORDER BY c.class_name, u.username
        ''')
        
        logger.info(f"查询到 {cursor.rowcount} 位正班主任")
        
        teachers = []
        for row in cursor.fetchall():
            teachers.append({
                'id': row[0],
                'username': row[1],
                'class_name': row[2]
            })
        
        logger.info(f"返回 {len(teachers)} 位正班主任: {[t['username'] for t in teachers]}")
        
        # 获取所有考核项目
        cursor.execute('''
            SELECT id, category, item_name, weight
            FROM performance_items
            WHERE is_active = 1
            ORDER BY category, id
        ''')
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row[0],
                'category': row[1],
                'item_name': row[2],
                'weight': row[3]
            })
        
        # 获取所有评分记录
        cursor.execute('''
            SELECT teacher_id, item_id, evaluator_id, score, u.username
            FROM performance_scores s
            JOIN users u ON s.evaluator_id = u.id
            WHERE semester = ?
        ''', (semester,))
        
        scores = {}
        for row in cursor.fetchall():
            key = f"{row[0]}_{row[1]}"
            if key not in scores:
                scores[key] = []
            scores[key].append({
                'evaluator_id': row[2],
                'evaluator_name': row[4],
                'score': row[3]
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'teachers': teachers,
            'items': items,
            'scores': scores
        })
        
    except Exception as e:
        logger.error(f"获取评分矩阵失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== 结果计算和查询 ====================

@performance_bp.route('/calculate/<semester>', methods=['POST'])
@login_required
@require_performance_access
def calculate_results(semester):
    """计算考核结果（去掉最高最低分后取平均）"""
    try:
        # 只有超级管理员可以计算考核结果
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有超级管理员可以计算考核结果'}), 403
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有正班主任
        cursor.execute('''
            SELECT id, username FROM users 
            WHERE primary_role = '正班主任' AND is_admin = 0
        ''')
        teachers = cursor.fetchall()
        
        results = []
        
        for teacher in teachers:
            teacher_id = teacher[0]
            teacher_name = teacher[1]
            
            # 获取该教师所有项目的评分
            cursor.execute('''
                SELECT i.id, i.weight, s.score
                FROM performance_items i
                LEFT JOIN performance_scores s ON i.id = s.item_id 
                    AND s.teacher_id = ? AND s.semester = ?
                WHERE i.is_active = 1
            ''', (teacher_id, semester))
            
            items_scores = cursor.fetchall()
            total_score = 0
            
            for item_id, weight, _ in items_scores:
                # 获取该项目的所有评分
                cursor.execute('''
                    SELECT score FROM performance_scores
                    WHERE teacher_id = ? AND item_id = ? AND semester = ?
                    ORDER BY score
                ''', (teacher_id, item_id, semester))
                
                scores = [row[0] for row in cursor.fetchall()]
                
                if len(scores) > 0:
                    # 如果有3个或以上评分，去掉最高和最低分
                    if len(scores) >= 3:
                        scores = scores[1:-1]
                    
                    # 计算平均分
                    avg_score = sum(scores) / len(scores) if scores else 0
                    # 加权计算
                    total_score += avg_score * weight / 100
            
            results.append({
                'teacher_id': teacher_id,
                'teacher_name': teacher_name,
                'total_score': round(total_score, 2)
            })
        
        # 按总分排序
        results.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 更新排名并保存到数据库
        for rank, result in enumerate(results, 1):
            cursor.execute('''
                INSERT INTO performance_results (teacher_id, semester, total_score, rank)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(teacher_id, semester)
                DO UPDATE SET total_score = ?, rank = ?, updated_at = ?
            ''', (result['teacher_id'], semester, result['total_score'], rank,
                  result['total_score'], rank, datetime.now().isoformat()))
            
            result['rank'] = rank
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '考核结果计算完成',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"计算考核结果失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@performance_bp.route('/results/<semester>', methods=['GET'])
@login_required
@require_performance_access
def get_results(semester):
    """获取考核结果"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                r.teacher_id,
                u.username,
                u.role,
                c.class_name,
                r.total_score,
                r.rank
            FROM performance_results r
            JOIN users u ON r.teacher_id = u.id
            LEFT JOIN classes c ON u.class_id = c.id
            WHERE r.semester = ?
            ORDER BY r.rank
        ''', (semester,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'teacher_id': row[0],
                'teacher_name': row[1],
                'role': row[2],
                'class_name': row[3],
                'total_score': row[4],
                'rank': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"获取考核结果失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== 教师管理 ====================

@performance_bp.route('/teachers', methods=['GET'])
@login_required
@require_performance_access
def get_teachers():
    """获取所有教师列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                u.id,
                u.username,
                u.role,
                c.class_name
            FROM users u
            LEFT JOIN classes c ON u.class_id = c.id
            WHERE u.is_admin = 0
            ORDER BY u.role, u.username
        ''')
        
        teachers = []
        for row in cursor.fetchall():
            teachers.append({
                'id': row[0],
                'username': row[1],
                'role': row[2] or '科任老师',
                'class_name': row[3]
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'teachers': teachers
        })
        
    except Exception as e:
        logger.error(f"获取教师列表失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@performance_bp.route('/teachers/<int:teacher_id>/role', methods=['PUT'])
@login_required
@require_performance_access
def update_teacher_role(teacher_id):
    """更新教师角色"""
    try:
        # 只有超级管理员可以更新教师角色
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有超级管理员可以更新教师角色'}), 403
        data = request.json
        role = data.get('role')
        
        valid_roles = ['正班主任', '副班主任', '科任老师', '行政', '校级领导', '超级管理员']
        if role not in valid_roles:
            return jsonify({'status': 'error', 'message': '无效的角色类型'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET role = ?, updated_at = ?
            WHERE id = ?
        ''', (role, datetime.now().isoformat(), teacher_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '教师角色更新成功'
        })
        
    except Exception as e:
        logger.error(f"更新教师角色失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
