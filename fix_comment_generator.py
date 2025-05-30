#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 打开文件
with open("utils/comment_generator.py", "r", encoding="utf-8") as f:
    content = f.read()

# 替换1：默认参数修改为5000
content = content.replace(
    "max_length: int = 1000) -> Dict[str, Any]:",
    "max_length: int = 5000) -> Dict[str, Any]:"
)

# 替换2：验证函数中的字数限制
content = content.replace(
    "if not (50 <= max_length <= 1000):",
    "if not (50 <= max_length <= 5000):  # 修改为5000字"
)

# 替换3：错误信息
content = content.replace(
    "\"最大字数必须在50-1000之间\"",
    "\"最大字数必须在50-5000之间\""
)

# 写回文件
with open("utils/comment_generator.py", "w", encoding="utf-8") as f:
    f.write(content)

print("成功修改utils/comment_generator.py") 