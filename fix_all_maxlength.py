#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

def fix_file(filepath, replacements):
    """修改文件中的字符串"""
    print(f"修改 {filepath} 中的字数限制...")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"成功修改 {filepath}")
    except Exception as e:
        print(f"修改 {filepath} 失败: {e}")

# 1. 修改utils/comment_generator.py
comment_generator_replacements = [
    ("max_length: int = 260", "max_length: int = 5000"),
    ("if not (50 <= max_length <= 260)", "if not (50 <= max_length <= 5000)"),
    ("最大字数必须在50-260之间", "最大字数必须在50-5000之间")
]
fix_file("utils/comment_generator.py", comment_generator_replacements)

# 2. 修改utils/deepseek_api.py
deepseek_api_replacements = [
    ("max_length: int = 260) -> Dict[str, Any]:", "max_length: int = 5000) -> Dict[str, Any]:"),
]
fix_file("utils/deepseek_api.py", deepseek_api_replacements)

# 3. 修改comments.py
comments_replacements = [
    ("max_length = int(data.get('max_length', 260))  # 修改为260字", 
     "max_length = int(data.get('max_length', 5000))  # 评语字数限制为5000字")
]
fix_file("comments.py", comments_replacements)

# 4. 修改js/comments.js
comments_js_replacements = [
    ("const maxLength = 260;  // 修改为5000字", "const maxLength = 5000;  // 修改为5000字"),
    ("const maxLength = 260;", "const maxLength = 5000;"),
    ("maxLength = 260", "maxLength = 5000"),
    ("`评语超过${maxLength}字限制", "`评语超过5000字限制"),
    ("value=\"260\"", "value=\"5000\""),
    ("max=\"260\"", "max=\"5000\""),
    ("0/260", "0/5000"),
    ("不超过260字", "不超过5000字"),
    ("超过260字", "超过5000字"),
    ("评语超过了260字限制", "评语超过了5000字限制")
]
fix_file("js/comments.js", comments_js_replacements)

# 5. 修改utils/excel_processor.py
excel_processor_replacements = [
    ("if len(comment['comment']) > 260:  # 修改为260字", "if len(comment['comment']) > 5000:"),
    ("if len(comment['comment']) > 260:", "if len(comment['comment']) > 5000:"),
    ("is_valid = len(comment['comment']) <= 260  # 临时调整为260字", "is_valid = len(comment['comment']) <= 5000"),
    ("评语超过260字符长度限制", "评语超过5000字符长度限制"),
    ("valid_text: \"有效\" if is_valid else \"无效(超过260字)\"", "valid_text: \"有效\" if is_valid else \"无效(超过5000字)\"")
]
fix_file("utils/excel_processor.py", excel_processor_replacements)

print("所有文件中的字数限制修改完成！") 