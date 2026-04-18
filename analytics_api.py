# -*- coding: utf-8 -*-
"""
学情分析 API 蓝图
提供学生德育画像、班级学情、趋势分析相关接口
权限说明：
- 管理员 (is_admin=True): 可访问全校数据
- 班主任 (primary_role='班主任'): 仅可访问自己班级的数据
- 科任老师 (primary_role='科任老师'): 仅可访问自己班级的数据
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import logging

logger = logging.getLogger(__name__)

analytics_api = Blueprint('analytics', __name__, url_prefix='/api/analytics')


def get_current_user_context():
    """获取当前用户的权限上下文"""
    from flask_login import current_user
    return {
        'user_id': getattr(current_user, 'id', None),
        'is_admin': getattr(current_user, 'is_admin', False),
        'class_id': getattr(current_user, 'class_id', None),
        'primary_role': getattr(current_user, 'primary_role', ''),
        'is_authenticated': getattr(current_user, 'is_authenticated', False)
    }


def analytics_required(f):
    """验证用户是否为管理员或教师"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user

        if not current_user.is_authenticated:
            return jsonify({'error': '请先登录'}), 401

        is_admin = getattr(current_user, 'is_admin', False)
        primary_role = getattr(current_user, 'primary_role', '')

        if is_admin or primary_role in ['正班主任', '副班主任', '班主任', '科任老师', '行政', 'teacher']:
            return f(*args, **kwargs)

        return jsonify({'error': '权限不足'}), 403
    return decorated_function


def admin_required(f):
    """仅允许管理员访问"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user

        if not current_user.is_authenticated:
            return jsonify({'error': '请先登录'}), 401

        if not getattr(current_user, 'is_admin', False):
            return jsonify({'error': '此功能仅管理员可用'}), 403

        return f(*args, **kwargs)
    return decorated_function


def check_student_access(student_id, user_context):
    """检查用户是否有权访问该学生的数据"""
    if user_context['is_admin']:
        return True

    from utils.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT class_id FROM students WHERE id = ? AND class_id = ?',
                   (student_id, user_context['class_id']))
    row = cursor.fetchone()
    conn.close()

    return row is not None


def check_class_access(class_id, user_context):
    """检查用户是否有权访问该班级的数据"""
    if user_context['is_admin']:
        return True

    try:
        return int(class_id) == int(user_context['class_id'])
    except (ValueError, TypeError):
        return str(class_id) == str(user_context['class_id'])


@analytics_api.route('/student/<int:student_id>/profile', methods=['GET'])
@analytics_required
def get_student_profile(student_id):
    """
    获取学生德育成长画像

    权限：班主任/科任老师只能查看本班学生，管理员可查看全校
    """
    try:
        from utils.analytics import get_student_profile

        user_ctx = get_current_user_context()

        if not check_student_access(student_id, user_ctx):
            return jsonify({'error': '无权访问该学生数据'}), 403

        class_id = request.args.get('class_id', type=int)
        if not class_id and not user_ctx['is_admin']:
            class_id = user_ctx['class_id']

        result = get_student_profile(student_id, class_id)

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取学生画像API失败: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_api.route('/student/<int:student_id>/progress', methods=['GET'])
@analytics_required
def get_student_progress(student_id):
    """
    获取学生进步率

    权限：班主任/科任老师只能查看本班学生，管理员可查看全校
    """
    try:
        from utils.analytics import calculate_progress_rate

        user_ctx = get_current_user_context()

        if not check_student_access(student_id, user_ctx):
            return jsonify({'error': '无权访问该学生数据'}), 403

        result = calculate_progress_rate(student_id)

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取学生进步率API失败: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_api.route('/class/<int:class_id>/profile', methods=['GET'])
@analytics_required
def get_class_profile(class_id):
    """
    获取班级学情图谱

    权限：班主任/科任老师只能查看本班，管理员可查看全校
    """
    try:
        from utils.analytics import get_class_profile

        user_ctx = get_current_user_context()

        if not check_class_access(class_id, user_ctx):
            return jsonify({'error': '无权访问该班级数据'}), 403

        semester = request.args.get('semester', None)

        result = get_class_profile(class_id, semester)

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取班级学情API失败: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_api.route('/class/<int:class_id>/trend', methods=['GET'])
@analytics_required
def get_class_trend(class_id):
    """
    获取班级发展趋势

    权限：班主任/科任老师只能查看本班，管理员可查看全校
    """
    try:
        from utils.analytics import get_trend_analysis

        user_ctx = get_current_user_context()

        if not check_class_access(class_id, user_ctx):
            return jsonify({'error': '无权访问该班级数据'}), 403

        semester_range = request.args.get('range', default=4, type=int)

        result = get_trend_analysis(class_id, semester_range)

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取班级趋势API失败: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_api.route('/school/ranking', methods=['GET'])
@admin_required
def get_school_ranking():
    """
    获取全校班级排名

    权限：仅管理员可访问
    """
    try:
        from utils.analytics import get_school_ranking

        result = get_school_ranking()

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取全校排名API失败: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_api.route('/school/trend', methods=['GET'])
@admin_required
def get_school_trend():
    """
    获取全校发展趋势

    权限：仅管理员可访问
    """
    try:
        from utils.analytics import get_trend_analysis

        semester_range = request.args.get('range', default=4, type=int)

        result = get_trend_analysis(class_id=None, semester_range=semester_range)

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取全校趋势API失败: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_api.route('/students/batch/profile', methods=['POST'])
@analytics_required
def get_batch_student_profiles():
    """
    批量获取学生画像（用于班级整体分析）

    权限：班主任/科任老师只能批量获取本班学生，管理员可获取全校
    """
    try:
        from utils.analytics import get_student_profile

        user_ctx = get_current_user_context()

        data = request.get_json()
        if not data or 'student_ids' not in data:
            return jsonify({'error': '请提供student_ids列表'}), 400

        student_ids = data['student_ids']
        if not isinstance(student_ids, list) or len(student_ids) > 50:
            return jsonify({'error': 'student_ids必须是少于50个元素的列表'}), 400

        results = []
        for student_id in student_ids:
            if not check_student_access(student_id, user_ctx):
                results.append({'error': '无权访问', 'student_id': student_id})
                continue
            profile = get_student_profile(student_id)
            results.append(profile)

        return jsonify({
            'status': 'ok',
            'count': len(results),
            'profiles': results
        })

    except Exception as e:
        logger.error(f"批量获取学生画像API失败: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_api.route('/my-class/profile', methods=['GET'])
@analytics_required
def get_my_class_profile():
    """
    获取当前用户所属班级的学情（便捷接口）

    权限：班主任/科任老师获取本班，管理员获取第一个班级或返回错误
    """
    try:
        from utils.analytics import get_class_profile

        user_ctx = get_current_user_context()

        if user_ctx['is_admin']:
            if not user_ctx['class_id']:
                return jsonify({'error': '管理员未分配班级，请使用 /class/<id>/profile 接口'}), 400
            class_id = user_ctx['class_id']
        else:
            class_id = user_ctx['class_id']
            if not class_id:
                return jsonify({'error': '您未分配班级'}), 400

        semester = request.args.get('semester', None)

        try:
            class_id = int(class_id)
        except (ValueError, TypeError):
            pass

        result = get_class_profile(class_id, semester)

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取本班学情API失败: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_api.route('/my-class/trend', methods=['GET'])
@analytics_required
def get_my_class_trend():
    """
    获取当前用户所属班级的趋势（便捷接口）

    权限：班主任/科任老师获取本班，管理员返回错误提示使用明确接口
    """
    try:
        from utils.analytics import get_trend_analysis

        user_ctx = get_current_user_context()

        if user_ctx['is_admin']:
            return jsonify({'error': '管理员请使用 /school/trend 或 /class/<id>/trend 接口'}), 400

        class_id = user_ctx['class_id']
        if not class_id:
            return jsonify({'error': '您未分配班级'}), 400

        semester_range = request.args.get('range', default=4, type=int)

        try:
            class_id = int(class_id)
        except (ValueError, TypeError):
            pass

        result = get_trend_analysis(class_id, semester_range)

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取本班趋势API失败: {e}")
        return jsonify({'error': str(e)}), 500
