#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能成绩导入功能测试
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.smart_grade_importer import SmartGradeImporter
import pandas as pd

def create_test_excel():
    """创建测试Excel文件"""
    data = {
        '学号': ['20210101', '20210102', '20210103', '20210201', '20210202'],
        '姓名': ['张三', '李四', '王五', '赵六', '钱七'],
        '班级': ['三年级1班', '三年级1班', '三年级1班', '三年级2班', '三年级2班'],
        '语文': ['优', '良', '及格', '优秀', 'A'],
        '数学': ['良', '优', '良好', '及格', 'B'],
        '英语': ['及格', '良', '优', '中等', '良']
    }
    
    df = pd.DataFrame(data)
    test_file = 'test_grades_import.xlsx'
    df.to_excel(test_file, index=False)
    print(f"✅ 创建测试文件: {test_file}")
    return test_file

def test_validate_structure():
    """测试Excel结构验证"""
    print("\n" + "="*60)
    print("测试1: Excel结构验证")
    print("="*60)
    
    importer = SmartGradeImporter()
    test_file = create_test_excel()
    
    df = pd.read_excel(test_file)
    result = importer.validate_excel_structure(df)
    
    print(f"\n验证结果: {'✅ 通过' if result['valid'] else '❌ 失败'}")
    print(f"检测到的学科: {result['detected_subjects']}")
    print(f"检测到的班级: {result['detected_classes']}")
    
    if result['errors']:
        print("\n错误:")
        for error in result['errors']:
            print(f"  {error}")
    
    if result['warnings']:
        print("\n警告:")
        for warning in result['warnings']:
            print(f"  {warning}")
    
    if result['unrecognized_columns']:
        print(f"\n未识别的列: {result['unrecognized_columns']}")
    
    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)
    
    return result['valid']

def test_grade_normalization():
    """测试成绩标准化"""
    print("\n" + "="*60)
    print("测试2: 成绩标准化")
    print("="*60)
    
    importer = SmartGradeImporter()
    
    test_cases = [
        ('优', '优'),
        ('优秀', '优'),
        ('A', '优'),
        ('良', '良'),
        ('良好', '良'),
        ('B', '良'),
        ('及格', '及格'),
        ('中等', '及格'),
        ('C', '及格'),
        ('待及格', '待及格'),
        ('不及格', '待及格'),
        ('D', '待及格'),
        ('/', '/'),
        ('无', '/'),
        ('缺', '/'),
    ]
    
    all_passed = True
    for input_val, expected in test_cases:
        result = importer._normalize_grade(input_val)
        passed = result == expected
        all_passed = all_passed and passed
        
        status = '✅' if passed else '❌'
        print(f"{status} '{input_val}' -> '{result}' (期望: '{expected}')")
    
    return all_passed

def test_permission_check():
    """测试权限检查"""
    print("\n" + "="*60)
    print("测试3: 权限检查")
    print("="*60)
    
    importer = SmartGradeImporter()
    
    # 模拟不同的权限场景
    test_cases = [
        {
            'name': '超级管理员',
            'permissions': {
                'can_import_all': True,
                'accessible_classes': [],
                'teaching_map': {}
            },
            'class_id': 1,
            'subject': '语文',
            'expected': True
        },
        {
            'name': '正班主任',
            'permissions': {
                'can_import_all': False,
                'accessible_classes': [1],
                'teaching_map': {'1': ['语文', '数学', '英语']}
            },
            'class_id': 1,
            'subject': '语文',
            'expected': True
        },
        {
            'name': '科任老师（有权限）',
            'permissions': {
                'can_import_all': False,
                'accessible_classes': [1, 2],
                'teaching_map': {'1': ['数学'], '2': ['数学']}
            },
            'class_id': 1,
            'subject': '数学',
            'expected': True
        },
        {
            'name': '科任老师（无权限）',
            'permissions': {
                'can_import_all': False,
                'accessible_classes': [1],
                'teaching_map': {'1': ['数学']}
            },
            'class_id': 1,
            'subject': '语文',
            'expected': False
        },
    ]
    
    all_passed = True
    for case in test_cases:
        result = importer._check_subject_permission(
            case['permissions'],
            case['class_id'],
            case['subject']
        )
        passed = result == case['expected']
        all_passed = all_passed and passed
        
        status = '✅' if passed else '❌'
        print(f"{status} {case['name']} - 班级{case['class_id']} {case['subject']}: "
              f"{result} (期望: {case['expected']})")
    
    return all_passed

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("智能成绩导入功能测试")
    print("="*60)
    
    results = []
    
    # 运行测试
    results.append(('Excel结构验证', test_validate_structure()))
    results.append(('成绩标准化', test_grade_normalization()))
    results.append(('权限检查', test_permission_check()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = '✅ 通过' if passed else '❌ 失败'
        print(f"{status} - {name}")
        all_passed = all_passed and passed
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
