#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""修复grades.py中的缩进问题"""

def fix_indentation():
    # 读取文件
    with open('grades.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到缩进不正确的行
    # 我们需要找到空行之后那两行，然后缩进它们
    for i in range(len(lines) - 3):
        # 检查是否是以"class_id = current_user.class_id"结尾的行
        if "class_id = current_user.class_id" in lines[i].strip():
            # 检查下一行是否是空行
            if lines[i+1].strip() == "":
                # 找到了空行，接下来的两行需要缩进
                # 获取当前行的缩进
                indentation = ' ' * 8  # 8个空格的缩进
                
                # 修正空行后的两行缩进问题
                lines[i+2] = indentation + lines[i+2].lstrip()
                lines[i+3] = indentation + lines[i+3].lstrip()
                
                print(f"修复了第{i+3}行和第{i+4}行的缩进")
                break
                
    # 写回文件
    with open('grades.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("缩进修复完成！")

if __name__ == "__main__":
    fix_indentation() 