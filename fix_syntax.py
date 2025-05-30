#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 打开文件
with open("comments.py", "r", encoding="utf-8") as f:
    content = f.read()

# 修复语法错误 - 删除反斜杠
content = content.replace(
    "max_length = int(data.get('max_length', 5000\\))",
    "max_length = int(data.get('max_length', 5000))"
)

# 写回文件
with open("comments.py", "w", encoding="utf-8") as f:
    f.write(content)

print("成功修复comments.py中的语法错误") 