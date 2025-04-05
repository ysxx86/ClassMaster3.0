#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""修复grades.py中的缩进问题"""

def fix_indentation():
    """修复grades.py文件中的缩进和语法问题"""
    # 读取文件
    with open('grades.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    i = 0
    
    # 跟踪try-except块
    try_blocks = []
    in_try_block = False
    
    while i < len(lines):
        line = lines[i]
        
        # 检测try块开始
        if ' try:' in line:
            in_try_block = True
            try_indent = len(line) - len(line.lstrip())
            try_blocks.append(try_indent)
        
        # 检测try块结束
        if in_try_block and try_blocks and line.strip() and len(line) - len(line.lstrip()) <= try_blocks[-1]:
            if not any('except' in l for l in fixed_lines[-20:]):
                # 添加缺失的except
                indent = ' ' * try_blocks[-1]
                except_line = indent + 'except Exception as e:\n'
                error_line = indent + '    logger.error(f"出错: {str(e)}")\n'
                return_line = indent + '    return jsonify({"status": "error", "message": f"操作失败: {str(e)}"}), 500\n'
                fixed_lines.append(except_line)
                fixed_lines.append(error_line)
                fixed_lines.append(return_line)
            in_try_block = False
            try_blocks.pop()
        
        # 修复问题1：第81行缩进问题
        if i >= 80 and i <= 82 and 'return jsonify({' in line and not line.startswith('                return'):
            fixed_lines.append('                return jsonify({\n')
            i += 1
            continue
            
        # 修复问题2：跳过多余的except块
        if 'except Exception as e:' in line and i > 150 and i < 160:
            # 检查前面是否已经有一个except块
            prev_lines = ''.join(fixed_lines[-10:])
            if 'except Exception as e:' in prev_lines:
                # 跳过这个重复的except块，直到下一个函数定义或路由
                while i < len(lines) and not ('@login_required' in lines[i] or '@grades_bp.route' in lines[i]):
                    i += 1
                continue
                
        # 修复问题3：修复意外缩进的else和except
        if ('else:' in line and line.strip().startswith('else:') and '                        ' in line) or \
           ('except' in line and line.strip().startswith('except') and '                    ' in line):
            # 修正缩进级别为与try相同
            indent = ' ' * 8  # 标准缩进为8个空格
            if 'else:' in line:
                fixed_lines.append(indent + 'else:\n')
            else:
                fixed_lines.append(indent + 'except Exception as e:\n')
            i += 1
            continue
            
        # 修复问题4：修复意外缩进的return
        if 'return jsonify' in line and '                return' in line and i > 250:
            fixed_lines.append('        return jsonify' + line.split('return jsonify')[1])
            i += 1
            continue
            
        # 修复问题5：修复第406行的if缩进
        if 'if class_id:' in line and '            if' in line and i > 400:
            fixed_lines.append('        if class_id:\n')
            i += 1
            continue
            
        # 修复第407行的缩进
        if 'filename +=' in line and '            filename' in line and i > 400:
            fixed_lines.append('            filename += f\'_{class_id}\'\n')
            i += 1
            continue
            
        # 对于没有匹配到特定修复规则的行，直接添加
        fixed_lines.append(line)
        i += 1
    
    # 写回文件
    with open('grades_fixed.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("已创建修复后的文件：grades_fixed.py")
    print("请检查修复后的文件是否正确，然后替换原文件")

if __name__ == "__main__":
    fix_indentation() 