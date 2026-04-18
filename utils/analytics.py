# -*- coding: utf-8 -*-
"""
学情分析模块
提供学生德育成长画像、班级学情图谱、发展趋势分析功能
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from utils.db import get_db_connection

logger = logging.getLogger(__name__)

DEYU_DIMENSIONS = {
    'pinzhi': {'name': '品德修养', 'max': 30},
    'xuexi': {'name': '学习素养', 'max': 20},
    'jiankang': {'name': '身心健康', 'max': 20},
    'shenmei': {'name': '审美素养', 'max': 10},
    'shijian': {'name': '实践创新', 'max': 10},
    'shenghuo': {'name': '生活素养', 'max': 10}
}

SUBJECT_NAMES = {
    'yuwen': '语文',
    'shuxue': '数学',
    'yingyu': '英语',
    'daof': '道法',
    'kexue': '科学',
    'zonghe': '综合',
    'tiyu': '体育',
    'yinyue': '音乐',
    'meishu': '美术',
    'laodong': '劳动',
    'xinxi': '信息',
    'shufa': '书法',
    'xinli': '心理'
}

SUBJECT_GRADE_MAP = {
    '优': 4, '良': 3, '及格': 2, '待及格': 1, '/': 0, '': 0, None: 0
}


def get_student_profile(student_id: int, class_id: int = None) -> Dict[str, Any]:
    """
    获取学生德育成长画像数据

    Args:
        student_id: 学生ID
        class_id: 班级ID（可选）

    Returns:
        包含雷达图数据、趋势数据、建议的字典
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT id, name, class_id,
                   pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo,
                   semester, updated_at
            FROM students
            WHERE id = ?
        '''
        params = [student_id]

        if class_id:
            query += ' AND class_id = ?'
            params.append(class_id)

        cursor.execute(query, params)
        student = cursor.fetchone()

        if not student:
            conn.close()
            return {'error': '学生不存在'}

        current_scores = {
            'pinzhi': student['pinzhi'] or 0,
            'xuexi': student['xuexi'] or 0,
            'jiankang': student['jiankang'] or 0,
            'shenmei': student['shenmei'] or 0,
            'shijian': student['shijian'] or 0,
            'shenghuo': student['shenghuo'] or 0
        }

        radar_data = []
        for dim_key, dim_info in DEYU_DIMENSIONS.items():
            score = current_scores.get(dim_key, 0)
            percentage = round((score / dim_info['max']) * 100, 1) if dim_info['max'] > 0 else 0
            radar_data.append({
                'dimension': dim_key,
                'name': dim_info['name'],
                'score': score,
                'max': dim_info['max'],
                'percentage': percentage
            })

        cursor.execute('''
            SELECT semester, pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo, updated_at
            FROM students
            WHERE id = ? AND semester IS NOT NULL AND semester != ''
            ORDER BY updated_at DESC
            LIMIT 10
        ''', [student_id])
        history_rows = cursor.fetchall()

        trend_data = []
        for row in reversed(history_rows):
            total = sum([
                row['pinzhi'] or 0, row['xuexi'] or 0, row['jiankang'] or 0,
                row['shenmei'] or 0, row['shijian'] or 0, row['shenghuo'] or 0
            ])
            trend_data.append({
                'semester': row['semester'] or '未知学期',
                'total': total,
                'pinzhi': row['pinzhi'] or 0,
                'xuexi': row['xuexi'] or 0,
                'jiankang': row['jiankang'] or 0,
                'shenmei': row['shenmei'] or 0,
                'shijian': row['shijian'] or 0,
                'shenghuo': row['shenghuo'] or 0
            })

        avg_scores = calculate_class_average(cursor, student['class_id'], student['semester'])
        suggestions = generate_suggestions(current_scores, avg_scores)

        class_rank = calculate_student_rank(cursor, student_id, student['class_id'], student['semester'])

        conn.close()

        return {
            'status': 'ok',
            'student': {
                'id': student['id'],
                'name': student['name'],
                'class_id': student['class_id'],
                'semester': student['semester']
            },
            'radar_data': radar_data,
            'current_total': sum(current_scores.values()),
            'max_total': 100,
            'class_rank': class_rank,
            'trend_data': trend_data,
            'suggestions': suggestions
        }

    except Exception as e:
        logger.error(f"获取学生画像失败: {e}")
        return {'error': str(e)}


def calculate_class_average(cursor: sqlite3.Cursor, class_id: int, semester: str = None) -> Dict[str, float]:
    """计算班级平均分"""
    query = '''
        SELECT AVG(pinzhi) as avg_pinzhi, AVG(xuexi) as avg_xuexi,
               AVG(jiankang) as avg_jiankang, AVG(shenmei) as avg_shenmei,
               AVG(shijian) as avg_shijian, AVG(shenghuo) as avg_shenghuo
        FROM students
        WHERE class_id = ? AND pinzhi IS NOT NULL
    '''
    params = [class_id]

    if semester:
        query += ' AND semester = ?'
        params.append(semester)

    cursor.execute(query, params)
    row = cursor.fetchone()

    return {
        'pinzhi': round(row['avg_pinzhi'] or 0, 1),
        'xuexi': round(row['avg_xuexi'] or 0, 1),
        'jiankang': round(row['avg_jiankang'] or 0, 1),
        'shenmei': round(row['avg_shenmei'] or 0, 1),
        'shijian': round(row['avg_shijian'] or 0, 1),
        'shenghuo': round(row['avg_shenghuo'] or 0, 1)
    }


def calculate_student_rank(cursor: sqlite3.Cursor, student_id: int, class_id: int, semester: str = None) -> Dict[str, Any]:
    """计算学生在班级中的德育排名"""
    query = '''
        SELECT id, (COALESCE(pinzhi, 0) + COALESCE(xuexi, 0) + COALESCE(jiankang, 0) +
                    COALESCE(shenmei, 0) + COALESCE(shijian, 0) + COALESCE(shenghuo, 0)) as total
        FROM students
        WHERE class_id = ? AND pinzhi IS NOT NULL
    '''
    params = [class_id]

    if semester:
        query += ' AND semester = ?'
        params.append(semester)

    cursor.execute(query, params)
    all_students = cursor.fetchall()

    if not all_students:
        return {'rank': 0, 'total': 0}

    sorted_students = sorted(all_students, key=lambda s: s['total'], reverse=True)

    rank = 0
    student_total = 0
    for idx, s in enumerate(sorted_students):
        if s['id'] == student_id:
            rank = idx + 1
            student_total = s['total']
            break

    return {
        'rank': rank,
        'total_students': len(sorted_students),
        'total': student_total
    }


def generate_suggestions(current_scores: Dict[str, int], avg_scores: Dict[str, float]) -> List[str]:
    """生成个性化成长建议"""
    suggestions = []

    for dim_key, dim_info in DEYU_DIMENSIONS.items():
        current = current_scores.get(dim_key, 0)
        avg = avg_scores.get(dim_key, 0)
        percentage = (current / dim_info['max']) * 100 if dim_info['max'] > 0 else 0

        if percentage < 60:
            suggestions.append(f"【{dim_info['name']}】需要加强，当前得分{current}分，低于班级平均水平({avg}分)")
        elif percentage >= 90:
            suggestions.append(f"【{dim_info['name']}】表现优秀继续保持！")

    if len(suggestions) < 3:
        suggestions.append("整体表现良好，建议继续保持均衡发展")

    return suggestions[:5]


def get_class_profile(class_id: int, semester: str = None) -> Dict[str, Any]:
    """
    获取班级学情图谱数据

    Args:
        class_id: 班级ID
        semester: 学期筛选（可选）

    Returns:
        包含热力图数据、德育分布数据的字典
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT id, name,
                   yuwen, shuxue, yingyu, daof, kexue, zonghe,
                   tiyu, yinyue, meishu, laodong, xinxi, shufa, xinli,
                   pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo
            FROM students
            WHERE class_id = ?
        '''
        params = [class_id]

        if semester:
            query += ' AND semester = ?'
            params.append(semester)

        cursor.execute(query, params)
        students = cursor.fetchall()

        if not students:
            conn.close()
            return {'error': '班级不存在或没有学生数据'}

        subject_stats = {}
        for subj_key, subj_name in SUBJECT_NAMES.items():
            grades = {'优': 0, '良': 0, '及格': 0, '待及格': 0, '未评分': 0}
            total = 0
            count = 0

            for student in students:
                grade = student[subj_key] if subj_key in student.keys() else '/'
                grade_display = grade if grade and grade != '' else '/'
                if grade_display in grades:
                    grades[grade_display] += 1
                else:
                    grades['未评分'] += 1

                numeric = SUBJECT_GRADE_MAP.get(grade, 0)
                total += numeric
                count += 1

            excellent_rate = round((grades['优'] / count) * 100, 1) if count > 0 else 0
            pass_rate = round(((grades['优'] + grades['良'] + grades['及格']) / count) * 100, 1) if count > 0 else 0

            subject_stats[subj_key] = {
                'name': subj_name,
                'grades': grades,
                'excellent_rate': excellent_rate,
                'pass_rate': pass_rate,
                'average_score': round(total / count, 2) if count > 0 else 0
            }

        deyu_stats = {'优': 0, '良': 0, '及格': 0, '待及格': 0}
        for student in students:
            total = sum([
                student['pinzhi'] or 0, student['xuexi'] or 0, student['jiankang'] or 0,
                student['shenmei'] or 0, student['shijian'] or 0, student['shenghuo'] or 0
            ])
            if total >= 90:
                deyu_stats['优'] += 1
            elif total >= 75:
                deyu_stats['良'] += 1
            elif total >= 60:
                deyu_stats['及格'] += 1
            else:
                deyu_stats['待及格'] += 1

        weak_subjects = []
        for subj_key, stats in subject_stats.items():
            if stats['excellent_rate'] < 40:
                weak_subjects.append({
                    'subject': stats['name'],
                    'excellent_rate': stats['excellent_rate'],
                    'suggestion': f'建议加强{stats["name"]}教学，当前优秀率仅{stats["excellent_rate"]}%'
                })

        cursor.execute('SELECT class_name FROM classes WHERE id = ?', (class_id,))
        class_row = cursor.fetchone()
        class_name = class_row['class_name'] if class_row else f'班级{class_id}'

        conn.close()

        return {
            'status': 'ok',
            'class_id': class_id,
            'class_name': class_name,
            'student_count': len(students),
            'subject_stats': subject_stats,
            'deyu_stats': deyu_stats,
            'weak_subjects': weak_subjects,
            'semester': semester or '全部学期'
        }

    except Exception as e:
        logger.error(f"获取班级学情失败: {e}")
        return {'error': str(e)}


def get_trend_analysis(class_id: int = None, semester_range: int = 4) -> Dict[str, Any]:
    """
    获取发展趋势分析数据

    Args:
        class_id: 班级ID（可选，为空则分析全校）
        semester_range: 学期数量（默认最近4个学期）

    Returns:
        包含多学期趋势、对比数据的字典
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if class_id:
            query = '''
                SELECT semester,
                       AVG(pinzhi + xuexi + jiankang + shenmei + shijian + shenghuo) as avg_deyu,
                       COUNT(*) as student_count
                FROM students
                WHERE class_id = ? AND semester IS NOT NULL AND semester != ''
                GROUP BY semester
                ORDER BY semester DESC
                LIMIT ?
            '''
            params = [class_id, semester_range]
        else:
            query = '''
                SELECT semester,
                       AVG(pinzhi + xuexi + jiankang + shenmei + shijian + shenghuo) as avg_deyu,
                       COUNT(*) as student_count
                FROM students
                WHERE semester IS NOT NULL AND semester != ''
                GROUP BY semester
                ORDER BY semester DESC
                LIMIT ?
            '''
            params = [semester_range]

        cursor.execute(query, params)
        semester_data = cursor.fetchall()

        trend_data = []
        for row in reversed(semester_data):
            trend_data.append({
                'semester': row['semester'] or '未知',
                'avg_deyu': round(row['avg_deyu'] or 0, 1),
                'student_count': row['student_count']
            })

        if class_id:
            cursor.execute('SELECT class_name FROM classes WHERE id = ?', (class_id,))
            class_row = cursor.fetchone()
            class_name = class_row['class_name'] if class_row else f'班级{class_id}'
        else:
            class_name = '全校'

        conn.close()

        return {
            'status': 'ok',
            'class_id': class_id,
            'class_name': class_name,
            'trend_data': trend_data,
            'semester_count': len(trend_data)
        }

    except Exception as e:
        logger.error(f"获取趋势分析失败: {e}")
        return {'error': str(e)}


def get_school_ranking() -> Dict[str, Any]:
    """
    获取全校班级进步率排名

    Returns:
        包含各班级进步率排名的字典
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT c.id as class_id, c.class_name,
                  AVG(s.pinzhi + s.xuexi + s.jiankang + s.shenmei + s.shijian + s.shenghuo) as avg_total
            FROM classes c
            LEFT JOIN students s ON c.id = s.class_id
            WHERE s.semester = (SELECT MAX(semester) FROM students WHERE class_id = c.id)
            GROUP BY c.id, c.class_name
            ORDER BY avg_total DESC
        ''')

        rankings = []
        for idx, row in enumerate(cursor.fetchall()):
            rankings.append({
                'rank': idx + 1,
                'class_id': row['class_id'],
                'class_name': row['class_name'],
                'avg_total': round(row['avg_total'] or 0, 1)
            })

        conn.close()

        return {
            'status': 'ok',
            'rankings': rankings
        }

    except Exception as e:
        logger.error(f"获取全校排名失败: {e}")
        return {'error': str(e)}


def calculate_progress_rate(student_id: int, class_id: int = None) -> Dict[str, Any]:
    """
    计算学生进步率

    Args:
        student_id: 学生ID
        class_id: 班级ID（复合键）

    Returns:
        包含进步率和趋势判断的字典
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT semester, pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo, updated_at
            FROM students
            WHERE id = ? AND semester IS NOT NULL AND semester != ''
        '''
        params = [student_id]

        if class_id:
            query += ' AND class_id = ?'
            params.append(class_id)

        query += ' ORDER BY updated_at DESC LIMIT 2'

        cursor.execute(query, params)

        history = cursor.fetchall()
        conn.close()

        if len(history) < 2:
            return {
                'status': 'ok',
                'student_id': student_id,
                'progress_rate': 0,
                'trend': 'insufficient_data',
                'message': '历史数据不足，无法计算进步率'
            }

        current = history[0]
        previous = history[1]

        current_total = sum([
            current['pinzhi'] or 0, current['xuexi'] or 0, current['jiankang'] or 0,
            current['shenmei'] or 0, current['shijian'] or 0, current['shenghuo'] or 0
        ])

        previous_total = sum([
            previous['pinzhi'] or 0, previous['xuexi'] or 0, previous['jiankang'] or 0,
            previous['shenmei'] or 0, previous['shijian'] or 0, previous['shenghuo'] or 0
        ])

        if previous_total == 0:
            progress_rate = 0
        else:
            progress_rate = round(((current_total - previous_total) / previous_total) * 100, 2)

        if progress_rate > 5:
            trend = 'improving'
            message = f'进步明显，较上学期提升{progress_rate}%'
        elif progress_rate < -5:
            trend = 'declining'
            message = f'需要关注，较上学期下降{abs(progress_rate)}%'
        else:
            trend = 'stable'
            message = '表现稳定'

        return {
            'status': 'ok',
            'student_id': student_id,
            'current_semester': current['semester'],
            'previous_semester': previous['semester'],
            'current_total': current_total,
            'previous_total': previous_total,
            'progress_rate': progress_rate,
            'trend': trend,
            'message': message
        }

    except Exception as e:
        logger.error(f"计算进步率失败: {e}")
        return {'error': str(e)}
