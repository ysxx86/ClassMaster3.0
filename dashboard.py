@dashboard_bp.route('/api/dashboard/info', methods=['GET'])
@login_required
def get_dashboard_info():
    """获取仪表盘信息"""
    try:
        # 获取当前用户信息
        current_user_id = current_user.id
        # 安全地获取class_id，如果不存在则默认为None
        current_user_class_id = getattr(current_user, 'class_id', None)
        is_admin = getattr(current_user, 'is_admin', False)
        
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取当前班级名称
        current_class = "暂无班级"
        if current_user_class_id:
            cursor.execute('SELECT DISTINCT class FROM students WHERE class_id = ?', (current_user_class_id,))
            result = cursor.fetchone()
            if result and result['class']:
                current_class = result['class']
        
        # 获取学生总数
        if is_admin:
            cursor.execute('SELECT COUNT(*) as count FROM students')
        else:
            cursor.execute('SELECT COUNT(*) as count FROM students WHERE class_id = ?', (current_user_class_id,))
        student_count = cursor.fetchone()['count']
        
        # 获取评语总数
        if is_admin:
            cursor.execute('SELECT COUNT(*) as count FROM comments')
        else:
            cursor.execute('SELECT COUNT(*) as count FROM comments WHERE student_id IN (SELECT id FROM students WHERE class_id = ?)', (current_user_class_id,))
        comment_count = cursor.fetchone()['count']
        
        # 获取待办事项总数
        if is_admin:
            cursor.execute('SELECT COUNT(*) as count FROM todos WHERE status = "pending"')
        else:
            cursor.execute('SELECT COUNT(*) as count FROM todos WHERE status = "pending" AND class_id = ?', (current_user_class_id,))
        todo_count = cursor.fetchone()['count']
        
        # 获取最近的活动
        if is_admin:
            cursor.execute('''
                SELECT a.*, u.username 
                FROM activities a 
                LEFT JOIN users u ON a.user_id = u.id 
                ORDER BY a.created_at DESC 
                LIMIT 5
            ''')
        else:
            cursor.execute('''
                SELECT a.*, u.username 
                FROM activities a 
                LEFT JOIN users u ON a.user_id = u.id 
                WHERE a.class_id = ? 
                ORDER BY a.created_at DESC 
                LIMIT 5
            ''', (current_user_class_id,))
        activities = [dict(row) for row in cursor.fetchall()]
        
        # 获取成绩分布
        if is_admin:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN yuwen = '优' THEN 1 ELSE 0 END) as yuwen_a,
                    SUM(CASE WHEN yuwen = '良' THEN 1 ELSE 0 END) as yuwen_b,
                    SUM(CASE WHEN yuwen = '及格' THEN 1 ELSE 0 END) as yuwen_c,
                    SUM(CASE WHEN yuwen = '待及格' THEN 1 ELSE 0 END) as yuwen_d,
                    SUM(CASE WHEN shuxue = '优' THEN 1 ELSE 0 END) as shuxue_a,
                    SUM(CASE WHEN shuxue = '良' THEN 1 ELSE 0 END) as shuxue_b,
                    SUM(CASE WHEN shuxue = '及格' THEN 1 ELSE 0 END) as shuxue_c,
                    SUM(CASE WHEN shuxue = '待及格' THEN 1 ELSE 0 END) as shuxue_d,
                    SUM(CASE WHEN yingyu = '优' THEN 1 ELSE 0 END) as yingyu_a,
                    SUM(CASE WHEN yingyu = '良' THEN 1 ELSE 0 END) as yingyu_b,
                    SUM(CASE WHEN yingyu = '及格' THEN 1 ELSE 0 END) as yingyu_c,
                    SUM(CASE WHEN yingyu = '待及格' THEN 1 ELSE 0 END) as yingyu_d
                FROM students
            ''')
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN yuwen = '优' THEN 1 ELSE 0 END) as yuwen_a,
                    SUM(CASE WHEN yuwen = '良' THEN 1 ELSE 0 END) as yuwen_b,
                    SUM(CASE WHEN yuwen = '及格' THEN 1 ELSE 0 END) as yuwen_c,
                    SUM(CASE WHEN yuwen = '待及格' THEN 1 ELSE 0 END) as yuwen_d,
                    SUM(CASE WHEN shuxue = '优' THEN 1 ELSE 0 END) as shuxue_a,
                    SUM(CASE WHEN shuxue = '良' THEN 1 ELSE 0 END) as shuxue_b,
                    SUM(CASE WHEN shuxue = '及格' THEN 1 ELSE 0 END) as shuxue_c,
                    SUM(CASE WHEN shuxue = '待及格' THEN 1 ELSE 0 END) as shuxue_d,
                    SUM(CASE WHEN yingyu = '优' THEN 1 ELSE 0 END) as yingyu_a,
                    SUM(CASE WHEN yingyu = '良' THEN 1 ELSE 0 END) as yingyu_b,
                    SUM(CASE WHEN yingyu = '及格' THEN 1 ELSE 0 END) as yingyu_c,
                    SUM(CASE WHEN yingyu = '待及格' THEN 1 ELSE 0 END) as yingyu_d
                FROM students 
                WHERE class_id = ?
            ''', (current_user_class_id,))
        grade_distribution = cursor.fetchone()
        
        # 获取待办事项
        if is_admin:
            cursor.execute('''
                SELECT t.*, u.username 
                FROM todos t 
                LEFT JOIN users u ON t.user_id = u.id 
                WHERE t.status = 'pending' 
                ORDER BY t.created_at DESC 
                LIMIT 5
            ''')
        else:
            cursor.execute('''
                SELECT t.*, u.username 
                FROM todos t 
                LEFT JOIN users u ON t.user_id = u.id 
                WHERE t.status = 'pending' AND t.class_id = ? 
                ORDER BY t.created_at DESC 
                LIMIT 5
            ''', (current_user_class_id,))
        todos = [dict(row) for row in cursor.fetchall()]
        
        # 获取最新评语
        if is_admin:
            cursor.execute('''
                SELECT c.*, s.name as student_name, u.username 
                FROM comments c 
                LEFT JOIN students s ON c.student_id = s.id 
                LEFT JOIN users u ON c.user_id = u.id 
                ORDER BY c.created_at DESC 
                LIMIT 5
            ''')
        else:
            cursor.execute('''
                SELECT c.*, s.name as student_name, u.username 
                FROM comments c 
                LEFT JOIN students s ON c.student_id = s.id 
                LEFT JOIN users u ON c.user_id = u.id 
                WHERE s.class_id = ? 
                ORDER BY c.created_at DESC 
                LIMIT 5
            ''', (current_user_class_id,))
        comments = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'data': {
                'user': {
                    'id': current_user_id,
                    'username': current_user.username,
                    'is_admin': is_admin,
                    'class_id': current_user_class_id,
                    'current_class': current_class
                },
                'stats': {
                    'student_count': student_count,
                    'comment_count': comment_count,
                    'todo_count': todo_count
                },
                'grade_distribution': {
                    'total': grade_distribution['total'] or 0,
                    'yuwen': {
                        '优': grade_distribution['yuwen_a'] or 0,
                        '良': grade_distribution['yuwen_b'] or 0,
                        '及格': grade_distribution['yuwen_c'] or 0,
                        '待及格': grade_distribution['yuwen_d'] or 0
                    },
                    'shuxue': {
                        '优': grade_distribution['shuxue_a'] or 0,
                        '良': grade_distribution['shuxue_b'] or 0,
                        '及格': grade_distribution['shuxue_c'] or 0,
                        '待及格': grade_distribution['shuxue_d'] or 0
                    },
                    'yingyu': {
                        '优': grade_distribution['yingyu_a'] or 0,
                        '良': grade_distribution['yingyu_b'] or 0,
                        '及格': grade_distribution['yingyu_c'] or 0,
                        '待及格': grade_distribution['yingyu_d'] or 0
                    }
                },
                'activities': activities,
                'todos': todos,
                'comments': comments
            }
        })
    except Exception as e:
        logger.error(f"获取仪表盘信息时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': f'获取仪表盘信息失败: {str(e)}'}) 