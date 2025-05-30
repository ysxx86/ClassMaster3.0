import sys

# 打开文件
with open("comments.py", "r", encoding="utf-8") as f:
    content = f.read()

# 替换内容
content = content.replace(
    '"class_id": class_id',
    '"class_id": class_id,\n                "reasoning_content": result.get("reasoning_content", ""),\n                "content_field": result.get("content_field", "")'
)

# 写回文件
with open("comments.py", "w", encoding="utf-8") as f:
    f.write(content)

print("成功修改comments.py") 