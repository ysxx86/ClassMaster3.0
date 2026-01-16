#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学生数据导入模板生成工具
根据班级信息生成定制化的Excel模板
"""

import os
import sqlite3
import argparse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# 配置
TEMPLATE_FOLDER = 'templates'
DATABASE = 'students.db'

def get_db_connection():
    """创建数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_class_info(class_id):
    """根据班级ID获取班级信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, class_name FROM classes WHERE id = ?', (class_id,))
    class_info = cursor.fetchone()
    conn.close()
    
    if not class_info:
        raise ValueError(f"未找到ID为 {class_id} 的班级")
    
    return class_info

def create_custom_template(class_id):
    """为特定班级创建学生导入模板"""
    # 获取班级信息
    try:
        class_info = get_class_info(class_id)
        class_name = class_info['class_name']
    except Exception as e:
        print(f"获取班级信息失败: {str(e)}")
        return None
    
    # 创建模板目录
    template_dir = TEMPLATE_FOLDER
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    # 定义文件名（使用班级名称）
    template_name = f"student_template_{class_name}.xlsx"
    template_path = os.path.join(template_dir, template_name)
    
    # 如果文件存在且被占用，则跳过创建
    if os.path.exists(template_path):
        try:
            # 尝试打开文件，如果可以打开就先删除
            with open(template_path, 'a'):
                pass
            os.remove(template_path)
        except:
            print(f"模板文件 {template_path} 被占用，跳过创建")
            return template_path
    
    # 创建工作簿和工作表
    wb = Workbook()
    ws = wb.active
    ws.title = "学生信息"
    
    # 设置样式
    # 标题样式
    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal='center', vertical='center')
    
    # 班级信息样式
    class_font = Font(bold=True, size=14)
    class_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    class_alignment = Alignment(horizontal='left', vertical='center')
    
    # 边框样式
    thin_border = Border(
        left=Side(style='thin'), 
        right=Side(style='thin'), 
        top=Side(style='thin'), 
        bottom=Side(style='thin')
    )
    
    # 添加班级信息行
    ws.merge_cells('A1:H1')
    class_cell = ws.cell(row=1, column=1, value=f"班级: {class_name} - 学生信息导入模板")
    class_cell.font = class_font
    class_cell.fill = class_fill
    class_cell.alignment = class_alignment
    
    # 设置标题行
    headers = ['学号', '姓名', '性别', '班级', '身高(cm)', '体重(kg)', '胸围(cm)', 
               '肺活量(ml)', '龋齿', '视力左', '视力右', '体测情况']
    
    # 写入表头
    for i, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=i, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(i)].width = 15
    
    # 锁定班级列
    # 添加示例数据行
    for row in range(3, 8):  # 添加5行示例
        # 学号格式示例: 001, 002...
        ws.cell(row=row, column=1, value=f"{row-2:03d}")
        
        # 姓名示例
        ws.cell(row=row, column=2, value=f"学生{row-2}")
        
        # 性别示例（交替男女）
        ws.cell(row=row, column=3, value="男" if row % 2 == 0 else "女")
        
        # 班级 - 预填当前班级且设为浅灰色背景
        class_cell = ws.cell(row=row, column=4, value=class_name)
        class_cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        
        # 其他字段示例值
        ws.cell(row=row, column=5, value="135")  # 身高
        ws.cell(row=row, column=6, value="32")   # 体重
        ws.cell(row=row, column=7, value="65")   # 胸围
        ws.cell(row=row, column=8, value="1500") # 肺活量
        ws.cell(row=row, column=9, value="0")    # 龋齿
        ws.cell(row=row, column=10, value="5.0") # 视力左
        ws.cell(row=row, column=11, value="5.0") # 视力右
        ws.cell(row=row, column=12, value="合格") # 体测情况
    
    # 添加说明信息
    ws.merge_cells('A10:H10')
    note_title = ws.cell(row=10, column=1, value="注意事项:")
    note_title.font = Font(bold=True)
    
    notes = [
        "1. 请按照示例格式填写学生信息",
        "2. 性别请填写'男'或'女'",
        f"3. 班级字段已预设为 '{class_name}'，请勿修改",
        "4. 视力格式: 5.0 或 4.8 等",
        "5. 体测情况建议填写: 优秀、良好、合格、不合格",
        "6. 导入时班级必须与当前所管理班级一致，否则无法导入"
    ]
    
    for i, note in enumerate(notes, 11):
        ws.merge_cells(f'A{i}:H{i}')
        note_cell = ws.cell(row=i, column=1, value=note)
        # 如果是关于班级的注意事项，用红色字体突出显示
        if i == 13:
            note_cell.font = Font(color="FF0000", bold=True)
    
    # 保存工作簿
    wb.save(template_path)
    print(f"已为班级 '{class_name}' 创建自定义模板: {template_path}")
    
    return template_path

def main():
    parser = argparse.ArgumentParser(description='为特定班级创建学生导入模板')
    parser.add_argument('--class_id', type=int, required=True, help='班级ID')
    
    args = parser.parse_args()
    template_path = create_custom_template(args.class_id)
    
    if template_path:
        print(f"模板已创建: {template_path}")
    else:
        print("模板创建失败")

if __name__ == "__main__":
    main() 