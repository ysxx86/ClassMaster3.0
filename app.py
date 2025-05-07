from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, redirect, url_for, session
from flask_login import current_user, logout_user

# 配置会话
app.config['SECRET_KEY'] = 'your-secret-key'  # 请更改为随机的密钥
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 设置会话超时时间为30分钟
app.config['SESSION_COOKIE_SECURE'] = False  # 在HTTP和HTTPS下均可发送cookie
app.config['SESSION_COOKIE_HTTPONLY'] = True  # 防止JavaScript访问cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 防止CSRF攻击

# 会话超时检查中间件
def check_session_timeout():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.is_authenticated:
                last_activity = session.get('last_activity')
                if last_activity:
                    try:
                        last_activity = datetime.fromisoformat(last_activity)
                        if datetime.now() - last_activity > app.config['PERMANENT_SESSION_LIFETIME']:
                            # 会话已超时，执行登出
                            logout_user()
                            session.clear()
                            session.modified = True
                            
                            # 判断请求类型，返回相应的响应
                            if request.is_xhr or request.path.startswith('/api/'):
                                return jsonify({
                                    'status': 'error', 
                                    'message': '会话已超时，请重新登录', 
                                    'code': 401,
                                    'redirect': url_for('users.login', timeout=True)
                                }), 401
                            else:
                                return redirect(url_for('users.login', timeout=True))
                    except (ValueError, TypeError) as e:
                        # 日期解析错误，重置活动时间
                        session['last_activity'] = datetime.now().isoformat()
                
                # 更新最后活动时间
                session['last_activity'] = datetime.now().isoformat()
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 为所有需要登录的路由添加会话超时检查
@students_bp.before_request
@login_required
def update_last_activity():
    session['last_activity'] = datetime.now().isoformat()

# 初始化数据库