#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 打开文件
with open("js/comments.js", "r", encoding="utf-8") as f:
    content = f.read()

# 替换所有字数限制为5000
content = content.replace("const maxLength = 1000;", "const maxLength = 5000;  // 修改为5000字")
content = content.replace("value=\"1000\"", "value=\"5000\"")
content = content.replace("max=\"1000\"", "max=\"5000\"")
content = content.replace("0/1000", "0/5000")
content = content.replace("不超过1000字", "不超过5000字")
content = content.replace("超过1000字", "超过5000字")
content = content.replace("评语超过了1000字限制", "评语超过了5000字限制")

# 写回文件
with open("js/comments.js", "w", encoding="utf-8") as f:
    f.write(content)

print("成功修改js/comments.js") 