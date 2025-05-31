#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 打开文件
with open("utils/excel_processor.py", "r", encoding="utf-8") as f:
    content = f.read()

# 修改字数限制
content = content.replace("if len(comment['comment']) > 5000:  # 修改为5000字", "if len(comment['comment']) > 5000:")
content = content.replace("if len(comment['comment']) > 5000:", "if len(comment['comment']) > 260:")
content = content.replace("is_valid = len(comment['comment']) <= 1000  # 临时调整为1000字", "is_valid = len(comment['comment']) <= 5000")
content = content.replace("\"有效\" if is_valid else \"无效(超过1000字)\"", "\"有效\" if is_valid else \"无效(超过5000字)\"")
content = content.replace("评语超过5000字符长度限制", "评语超过5000字符长度限制")

# 写回文件
with open("utils/excel_processor.py", "w", encoding="utf-8") as f:
    f.write(content)

print("成功修改utils/excel_processor.py中的字数限制")