#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试班级名称标准化功能"""

import re

def normalize_class_name(class_name_input):
    """
    将各种格式的班级名称标准化为数据库格式
    """
    if not class_name_input:
        return None, False
    
    # 去除空格和特殊字符
    class_name = str(class_name_input).strip().replace(' ', '')
    
    # 中文数字到阿拉伯数字的映射
    chinese_to_num = {
        '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
        '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'
    }
    
    # 年级映射（处理2024级这种格式）
    current_year = 2026  # 当前年份
    
    print(f"\n处理: '{class_name}'")
    
    # 模式1: 纯数字格式 "204" -> "二年级4班"
    match = re.match(r'^(\d)(\d{1,2})$', class_name)
    if match:
        grade_num = match.group(1)
        class_num = match.group(2)
        grade_map = {'1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六'}
        if grade_num in grade_map:
            result = f"{grade_map[grade_num]}年级{class_num}班"
            print(f"  匹配模式1: {result}")
            return result, True
    
    # 模式2: "2024级4班" 或 "小学2024级4班" -> "二年级4班"
    match = re.search(r'(\d{4})级(\d+)班', class_name)
    if match:
        year = int(match.group(1))
        class_num = match.group(2)
        # 计算年级：当前年份 - 入学年份 + 1
        grade = current_year - year + 1
        print(f"  年份: {year}, 计算年级: {grade}")
        if 1 <= grade <= 6:
            grade_map = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六'}
            result = f"{grade_map[grade]}年级{class_num}班"
            print(f"  匹配模式2: {result}")
            return result, True
    
    # 模式3: "二年4班" -> "二年级4班"
    match = re.match(r'^([一二三四五六])年(\d+)班$', class_name)
    if match:
        grade_chinese = match.group(1)
        class_num = match.group(2)
        result = f"{grade_chinese}年级{class_num}班"
        print(f"  匹配模式3: {result}")
        return result, True
    
    # 模式4: "二年级四班" -> "二年级4班"
    match = re.match(r'^([一二三四五六])年级([一二三四五六七八九十]+)班$', class_name)
    if match:
        grade_chinese = match.group(1)
        class_chinese = match.group(2)
        # 转换班级数字
        class_num = chinese_to_num.get(class_chinese, class_chinese)
        result = f"{grade_chinese}年级{class_num}班"
        print(f"  匹配模式4: {result}")
        return result, True
    
    # 模式5: "二年四班" -> "二年级4班"
    match = re.match(r'^([一二三四五六])年([一二三四五六七八九十]+)班$', class_name)
    if match:
        grade_chinese = match.group(1)
        class_chinese = match.group(2)
        class_num = chinese_to_num.get(class_chinese, class_chinese)
        result = f"{grade_chinese}年级{class_num}班"
        print(f"  匹配模式5: {result}")
        return result, True
    
    # 模式6: 已经是标准格式 "二年级4班"
    match = re.match(r'^([一二三四五六])年级(\d+)班$', class_name)
    if match:
        print(f"  匹配模式6: 已是标准格式")
        return class_name, True
    
    # 无法识别的格式
    print(f"  无法识别")
    return None, False

# 测试用例
test_cases = [
    "204",
    "二年级4班",
    "二年4班",
    "二年级四班",
    "二年四班",
    "2024级4班",
    "小学2024级4班",
    "二年级 4班",  # 带空格
]

print("=" * 60)
print("班级名称标准化测试")
print("=" * 60)

for test in test_cases:
    result, success = normalize_class_name(test)
    status = "✓" if success else "✗"
    print(f"{status} '{test}' => '{result}'")

print("=" * 60)
