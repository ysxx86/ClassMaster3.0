import requests
import sqlite3
import json

# 首先检查数据库结构
def check_database_structure():
    """检查数据库结构"""
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    # 获取学生表结构
    cursor.execute("PRAGMA table_info(students)")
    students_columns = [col[1] for col in cursor.fetchall()]
    print(f"学生表列: {students_columns}")
    
    # 获取评语表结构
    cursor.execute("PRAGMA table_info(comments)")
    comments_columns = [col[1] for col in cursor.fetchall()] if cursor.fetchall() else []
    print(f"评语表列: {comments_columns}")
    
    # 获取待办事项表结构
    cursor.execute("PRAGMA table_info(todos)")
    todos_columns = [col[1] for col in cursor.fetchall()] if cursor.fetchall() else []
    print(f"待办事项表列: {todos_columns}")
    
    # 检查是否存在activities表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activities'")
    has_activities = cursor.fetchone() is not None
    print(f"是否存在activities表: {has_activities}")
    
    conn.close()

# 测试API
def test_dashboard_api():
    """测试dashboard API"""
    # 登录
    session = requests.Session()
    login_response = session.post(
        'http://localhost:8081/login',
        json={'username': 'admin', 'password': '123456'}
    )
    print(f"登录结果: {login_response.status_code} - {login_response.text}")
    
    # 测试dashboard/info API
    info_response = session.get('http://localhost:8081/api/dashboard/info')
    print(f"\n/api/dashboard/info 结果: {info_response.status_code}")
    if info_response.status_code == 200:
        print(json.dumps(info_response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"错误: {info_response.text}")
    
    # 测试grade-distribution API
    grade_response = session.get('http://localhost:8081/api/dashboard/grade-distribution')
    print(f"\n/api/dashboard/grade-distribution 结果: {grade_response.status_code}")
    if grade_response.status_code == 200:
        print(json.dumps(grade_response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"错误: {grade_response.text}")

if __name__ == "__main__":
    print("检查数据库结构...")
    check_database_structure()
    
    print("\n测试Dashboard API...")
    test_dashboard_api() 