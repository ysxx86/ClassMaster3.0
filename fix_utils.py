#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 打开文件
with open("utils/deepseek_api.py", "r", encoding="utf-8") as f:
    content = f.read()

# 替换1：默认参数修改为5000
content = content.replace(
    "max_length: int = 1000) -> Dict[str, Any]:",
    "max_length: int = 5000) -> Dict[str, Any]:"
)

# 替换2：返回结果中添加两个字段
content = content.replace(
    "                    return {\n                        \"status\": \"ok\",\n                        \"comment\": content,\n                        \"message\": \"评语生成成功\"\n                    }",
    "                    return {\n                        \"status\": \"ok\",\n                        \"comment\": content,\n                        \"message\": \"评语生成成功\",\n                        \"reasoning_content\": reasoning_content,\n                        \"content_field\": message.get(\"content\", \"\")\n                    }"
)

# 替换3：max_tokens参数调大
content = content.replace(
    "max_tokens\": min(800, max_length * 2)",
    "max_tokens\": min(4000, max_length * 2)"
)

# 写回文件
with open("utils/deepseek_api.py", "w", encoding="utf-8") as f:
    f.write(content)

print("成功修改utils/deepseek_api.py") 