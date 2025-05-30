#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 打开文件
with open("js/comments.js", "r", encoding="utf-8") as f:
    content = f.read()

# 修改字数限制
content = content.replace("const maxLength = 5000;  // 修改为5000字", "const maxLength = 260;  // 修改为260字")
content = content.replace("const maxLength = 5000;", "const maxLength = 260;")
content = content.replace("maxLength = 5000", "maxLength = 260")
content = content.replace("`评语超过${maxLength}字限制", "`评语超过260字限制")
content = content.replace("value=\"5000\"", "value=\"260\"")
content = content.replace("max=\"5000\"", "max=\"260\"")
content = content.replace("0/5000", "0/260")
content = content.replace("不超过5000字", "不超过260字")
content = content.replace("超过5000字", "超过260字")
content = content.replace("评语超过了5000字限制", "评语超过了260字限制")

# 写回文件
with open("js/comments.js", "w", encoding="utf-8") as f:
    f.write(content)

print("成功修改js/comments.js中的字数限制") 