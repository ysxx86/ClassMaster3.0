#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 打开文件
try:
    with open("utils/excel_processor.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 替换所有字数限制为5000
    content = content.replace("if len(comment['comment']) > 1000:", "if len(comment['comment']) > 5000:  # 修改为5000字")
    content = content.replace("logger.warning(f\"学生[{comment['name']}]的评语超过1000字符长度限制", "logger.warning(f\"学生[{comment['name']}]的评语超过5000字符长度限制")
    content = content.replace("is_valid = comment_length <= 1000", "is_valid = comment_length <= 5000  # 修改为5000字")
    content = content.replace("valid_text\": \"有效\" if is_valid else \"无效(超过1000", "valid_text\": \"有效\" if is_valid else \"无效(超过5000")
    content = content.replace("comment = comment[:1000]", "comment = comment[:5000]  # 修改为5000字")

    # 写回文件
    with open("utils/excel_processor.py", "w", encoding="utf-8") as f:
        f.write(content)

    print("成功修改utils/excel_processor.py")
except Exception as e:
    print(f"修改utils/excel_processor.py时出错: {str(e)}") 