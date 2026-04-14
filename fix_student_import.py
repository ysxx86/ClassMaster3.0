#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复学生导入功能
确保上传目录存在并具有适当的权限
"""

import os
import sys
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("开始修复学生导入功能...")
    
    # 确保上传目录存在
    upload_dir = 'uploads'
    if not os.path.exists(upload_dir):
        logger.info(f"创建上传目录: {upload_dir}")
        try:
            os.makedirs(upload_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建上传目录失败: {str(e)}")
            return False
    
    # 确保上传目录有正确的权限
    try:
        logger.info(f"设置上传目录权限: {upload_dir}")
        os.chmod(upload_dir, 0o775)  # rwxrwxr-x
    except Exception as e:
        logger.error(f"设置上传目录权限失败: {str(e)}")
        logger.warning("可能需要手动设置目录权限")
    
    # 检查文件 students.py 中的相关代码
    try:
        with open('students.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 检查是否有创建目录的代码
        if 'os.makedirs(UPLOAD_FOLDER, exist_ok=True)' not in code:
            logger.info("需要添加创建上传目录的代码到 students.py")
            
            # 现在尝试修改代码
            logger.info("尝试修改 students.py 文件...")
            code_lines = code.split('\n')
            
            # 找到 import_students_preview 函数
            import_func_start = -1
            for i, line in enumerate(code_lines):
                if 'def import_students_preview()' in line:
                    import_func_start = i
                    break
            
            # 找到保存文件的行
            save_file_line = -1
            if import_func_start != -1:
                for i in range(import_func_start, len(code_lines)):
                    if 'file.save(file_path)' in code_lines[i]:
                        save_file_line = i
                        break
            
            # 插入目录创建代码
            if save_file_line != -1:
                code_lines.insert(save_file_line, '        # 确保上传目录存在')
                code_lines.insert(save_file_line + 1, '        os.makedirs(UPLOAD_FOLDER, exist_ok=True)')
                
                # 写回文件
                with open('students.py', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(code_lines))
                
                logger.info("成功修改 students.py 文件，添加了创建上传目录的代码")
            else:
                logger.warning("无法找到适当的位置添加代码")
    except Exception as e:
        logger.error(f"修改 students.py 失败: {str(e)}")
    
    logger.info("修复完成! 请重启服务器以应用更改。")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 