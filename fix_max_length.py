#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

# 打开文件
with open("comments.py", "r", encoding="utf-8") as f:
    content = f.read()

# 替换内容
content = content.replace(
    "max_length = int(data.get('max_length', 260))",
    "max_length = int(data.get('max_length', 5000))  # 修改为5000字"
)

# 写回文件
with open("comments.py", "w", encoding="utf-8") as f:
    f.write(content)

print("成功修改max_length为5000") 