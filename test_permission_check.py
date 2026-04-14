# -*- coding: utf-8 -*-
"""
测试权限检查逻辑
"""

# 模拟用户权限（从日志中复制）
permissions = {
    'role': '正班主任',
    'is_admin': False,
    'accessible_classes': [11],
    'teaching_map': {
        '11': ['道法', '语文', '数学', '英语', '劳动', '体育', '音乐', '美术', '科学', '综合', '信息', '书法', '心理']
    },
    'can_import_all': False
}

# 模拟检查权限的函数
def check_subject_permission(permissions, class_id, subject_name):
    """检查是否有权限导入指定班级的指定学科"""
    if permissions['can_import_all']:
        return True
    
    class_id_str = str(class_id)
    
    print(f"检查权限: class_id={class_id}, class_id_str={class_id_str}, subject={subject_name}")
    print(f"teaching_map keys: {list(permissions['teaching_map'].keys())}")
    print(f"teaching_map: {permissions['teaching_map']}")
    
    if class_id_str not in permissions['teaching_map']:
        print(f"❌ 班级 {class_id_str} 不在 teaching_map 中")
        return False
    
    has_permission = subject_name in permissions['teaching_map'][class_id_str]
    print(f"班级 {class_id_str} 的学科列表: {permissions['teaching_map'][class_id_str]}")
    print(f"是否有 {subject_name} 权限: {has_permission}")
    
    return has_permission

# 测试场景1：class_id 是整数
print("=" * 60)
print("测试场景1：class_id 是整数 11")
print("=" * 60)
result1 = check_subject_permission(permissions, 11, '道法')
print(f"结果: {result1}\n")

# 测试场景2：class_id 是字符串
print("=" * 60)
print("测试场景2：class_id 是字符串 '11'")
print("=" * 60)
result2 = check_subject_permission(permissions, '11', '语文')
print(f"结果: {result2}\n")

# 测试场景3：不存在的学科
print("=" * 60)
print("测试场景3：不存在的学科")
print("=" * 60)
result3 = check_subject_permission(permissions, 11, '不存在的学科')
print(f"结果: {result3}\n")

# 测试场景4：不存在的班级
print("=" * 60)
print("测试场景4：不存在的班级")
print("=" * 60)
result4 = check_subject_permission(permissions, 99, '道法')
print(f"结果: {result4}\n")
