# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import logging
import json
import os
import re
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('excel_processor')

class ExcelProcessor:
    """Excel数据处理类，专门用于处理学生健康数据"""
    
    def __init__(self):
        # 定义列名映射（Excel列名 -> 数据库字段名）
        self.column_mapping = {
            '学号': 'id',
            '姓名': 'name',
            '性别': 'gender',
            '班级': 'class',
            '身高(cm)': 'height',
            '身高（cm）': 'height',
            '身高': 'height',
            '体重(kg)': 'weight',
            '体重（kg）': 'weight',
            '体重': 'weight',
            '胸围(cm)': 'chest_circumference',
            '胸围（cm）': 'chest_circumference',
            '胸围': 'chest_circumference',
            '肺活量(ml)': 'vital_capacity',
            '肺活量（ml）': 'vital_capacity',
            '肺活量': 'vital_capacity',
            '龋齿': 'dental_caries',
            '视力左': 'vision_left',
            '视力右': 'vision_right',
            '体测情况': 'physical_test_status'
        }
        
        # 定义必需的列
        self.required_columns = ['学号', '姓名', '性别']
        
        # 定义数值列
        self.numeric_columns = [
            ('身高(cm)', 'height'),
            ('身高（cm）', 'height'),
            ('身高', 'height'),
            ('体重(kg)', 'weight'),
            ('体重（kg）', 'weight'),
            ('体重', 'weight'),
            ('胸围(cm)', 'chest_circumference'),
            ('胸围（cm）', 'chest_circumference'),
            ('胸围', 'chest_circumference'),
            ('肺活量(ml)', 'vital_capacity'),
            ('肺活量（ml）', 'vital_capacity'),
            ('肺活量', 'vital_capacity'),
            ('视力左', 'vision_left'),
            ('视力右', 'vision_right')
        ]

    def process_file(self, file_path):
        """处理Excel文件，返回标准化的学生数据"""
        logger.info(f"开始处理Excel文件: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return {'error': '文件不存在'}
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            logger.info(f"成功读取Excel文件，包含 {len(df)} 行数据")
            logger.info(f"Excel列: {list(df.columns)}")
            
            # 验证必要列是否存在
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Excel缺少必要列: {missing_columns}")
                return {'error': f'Excel文件缺少必要的列: {", ".join(missing_columns)}，请使用标准模板'}
            
            # 记录原始数据类型信息
            logger.info("原始DataFrame数据类型:")
            for col in df.columns:
                logger.info(f"列 {col}: {df[col].dtype}")
            
            # 预处理DataFrame
            df = self._preprocess_dataframe(df)
            
            # 转换为学生数据列表
            students_data = self._convert_to_students(df)
            
            # 生成HTML预览代码
            html_preview = self._generate_html_preview(students_data)
            
            logger.info(f"Excel处理完成，共 {len(students_data)} 条学生记录")
            
            return {
                'status': 'ok',
                'message': f'成功解析出{len(students_data)}条学生记录',
                'students': students_data,
                'html_preview': html_preview
            }
            
        except Exception as e:
            logger.exception(f"处理Excel文件时出错: {str(e)}")
            return {'error': f'处理Excel文件时出错: {str(e)}'}
    
    def _preprocess_dataframe(self, df):
        """预处理DataFrame，主要处理数值列和处理空值"""
        logger.info("开始预处理DataFrame")
        
        # 处理所有数值列
        for excel_col, db_field in self.numeric_columns:
            if excel_col in df.columns:
                logger.info(f"处理数值列 {excel_col} -> {db_field}")
                
                # 显示前几行原始数据，帮助调试
                logger.info(f"列 {excel_col} 原始数据前5行: {df[excel_col].head(5).tolist()}")
                
                # 将列转换为字符串进行预处理
                df[excel_col] = df[excel_col].astype(str)
                
                # 清理数据：移除非数字字符（保留数字、小数点和负号）
                df[excel_col] = df[excel_col].apply(self._clean_numeric_string)
                
                # 替换空字符串为NaN
                df[excel_col] = df[excel_col].replace('', np.nan)
                df[excel_col] = df[excel_col].replace('nan', np.nan)
                df[excel_col] = df[excel_col].replace('NaN', np.nan)
                df[excel_col] = df[excel_col].replace('None', np.nan)
                
                # 转换为数值类型
                df[excel_col] = pd.to_numeric(df[excel_col], errors='coerce')
                
                # 显示处理后数据，帮助调试
                logger.info(f"列 {excel_col} 处理后数据前5行: {df[excel_col].head(5).tolist()}")
                logger.info(f"列 {excel_col} 处理后数据类型: {df[excel_col].dtype}")
        
        return df
    
    def _clean_numeric_string(self, value):
        """清理数值字符串，保留有效数字"""
        if pd.isna(value) or value is None:
            return ''
        
        # 对非字符串类型，尝试转换为字符串
        if not isinstance(value, str):
            try:
                value = str(value)
            except:
                return ''
        
        # 替换逗号为点号（小数点）
        value = value.replace(',', '.')
        
        # 提取数字部分（包括负号和小数点）
        matches = re.search(r'-?\d+\.?\d*', value)
        if matches:
            return matches.group(0)
        
        return ''
    
    def _convert_to_students(self, df):
        """将DataFrame转换为学生数据列表"""
        logger.info("开始将DataFrame转换为学生数据列表")
        
        students_data = []
        
        for i, row in df.iterrows():
            student = {}
            
            # 添加基本字段
            student['id'] = str(row['学号'])
            student['name'] = str(row['姓名'])
            student['gender'] = str(row['性别'])
            
            # 添加班级（如果存在）
            if '班级' in df.columns:
                student['class'] = str(row['班级']) if pd.notna(row['班级']) else ''
            else:
                student['class'] = ''
            
            # 添加数值字段
            for excel_col, db_field in self.numeric_columns:
                if excel_col in df.columns:
                    value = row[excel_col]
                    if pd.notna(value):
                        # 转换为浮点数，确保数值类型正确
                        student[db_field] = float(value)
                        if i < 5:  # 仅记录前5条数据的详细信息
                            logger.info(f"学生{i+1} {db_field}: {value}, 转换为: {student[db_field]}")
                    else:
                        student[db_field] = None
            
            # 添加其他文本字段
            if '龋齿' in df.columns:
                student['dental_caries'] = str(row['龋齿']) if pd.notna(row['龋齿']) else ''
            else:
                student['dental_caries'] = ''
            
            if '体测情况' in df.columns:
                student['physical_test_status'] = str(row['体测情况']) if pd.notna(row['体测情况']) else ''
            else:
                student['physical_test_status'] = ''
            
            students_data.append(student)
        
        # 记录第一个学生数据，便于调试
        if students_data:
            logger.info(f"第一个学生数据: {json.dumps(students_data[0], ensure_ascii=False)}")
        
        return students_data
    
    def _generate_html_preview(self, students_data):
        """生成HTML预览表格"""
        logger.info("生成HTML预览表格")
        
        # 辅助函数，用于显示数值
        def display_value(value):
            if value == 0 or value == 0.0:
                return '0'
            return str(value) if value is not None else '-'
        
        html = """
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>学号</th>
                        <th>姓名</th>
                        <th>性别</th>
                        <th>班级</th>
                        <th>身高(cm)</th>
                        <th>体重(kg)</th>
                        <th>胸围(cm)</th>
                        <th>肺活量(ml)</th>
                        <th>龋齿</th>
                        <th>视力左</th>
                        <th>视力右</th>
                        <th>体测情况</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # 添加学生数据行
        for student in students_data:
            # 记录第一个学生的数值，便于调试
            if student == students_data[0]:
                logger.info("\n首个学生的HTML预览值:")
                logger.info(f"身高: {display_value(student.get('height'))}")
                logger.info(f"体重: {display_value(student.get('weight'))}")
                logger.info(f"胸围: {display_value(student.get('chest_circumference'))}")
                logger.info(f"肺活量: {display_value(student.get('vital_capacity'))}")
            
            html += f"""
                <tr>
                    <td>{student.get('id', '-')}</td>
                    <td>{student.get('name', '-')}</td>
                    <td>{student.get('gender', '-')}</td>
                    <td>{student.get('class', '-')}</td>
                    <td>{display_value(student.get('height'))}</td>
                    <td>{display_value(student.get('weight'))}</td>
                    <td>{display_value(student.get('chest_circumference'))}</td>
                    <td>{display_value(student.get('vital_capacity'))}</td>
                    <td>{student.get('dental_caries', '-')}</td>
                    <td>{display_value(student.get('vision_left'))}</td>
                    <td>{display_value(student.get('vision_right'))}</td>
                    <td>{student.get('physical_test_status', '-')}</td>
                </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        <div class="alert alert-info">
            <i class='bx bx-info-circle'></i> 共发现 """ + str(len(students_data)) + """ 名学生数据，点击"确认导入"按钮完成导入。
        </div>
        """
        
        return html

class CommentsExcelProcessor:
    """评语Excel数据处理类，专门用于处理学生评语导入"""
    
    def __init__(self):
        # 定义必需的列
        self.required_columns = ['姓名', '评语']
        
    def process_file(self, file_path, class_id=None):
        """处理评语Excel文件，返回标准化的评语数据"""
        logger.info(f"开始处理评语Excel文件: {file_path}, 班级ID: {class_id}")
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return {'error': '文件不存在'}
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            logger.info(f"成功读取评语Excel文件，包含 {len(df)} 行数据")
            logger.info(f"Excel列: {list(df.columns)}")
            
            # 验证必要列是否存在
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Excel缺少必要列: {missing_columns}")
                return {'error': f'Excel文件缺少必要的列: {", ".join(missing_columns)}，请使用标准模板'}
            
            # 预处理DataFrame
            df = self._preprocess_dataframe(df)
            
            # 转换为评语数据列表
            comments_data = self._convert_to_comments(df)
            
            # 生成HTML预览代码
            html_preview = self._generate_html_preview(comments_data)
            
            logger.info(f"评语Excel处理完成，共 {len(comments_data)} 条评语记录")
            
            return {
                'status': 'ok',
                'message': f'成功解析出{len(comments_data)}条评语记录',
                'comments': comments_data,
                'html_preview': html_preview
            }
            
        except Exception as e:
            logger.exception(f"处理评语Excel文件时出错: {str(e)}")
            return {'error': f'处理Excel文件时出错: {str(e)}'}
    
    def _preprocess_dataframe(self, df):
        """预处理DataFrame，处理空值和格式化评语内容"""
        logger.info("开始预处理评语DataFrame")
        
        # 确保姓名列为字符串类型
        if '姓名' in df.columns:
            df['姓名'] = df['姓名'].astype(str)
            # 去除姓名中的空白字符
            df['姓名'] = df['姓名'].apply(lambda x: x.strip() if isinstance(x, str) else x)
            # 将'nan'字符串转为空值
            df['姓名'] = df['姓名'].replace('nan', np.nan)
            df['姓名'] = df['姓名'].replace('NaN', np.nan)
            df['姓名'] = df['姓名'].replace('None', np.nan)
            df['姓名'] = df['姓名'].replace('', np.nan)
        
        # 确保评语列为字符串类型
        if '评语' in df.columns:
            # 将非字符串类型转换为字符串
            df['评语'] = df['评语'].astype(str)
            # 去除评语前后的空白字符
            df['评语'] = df['评语'].apply(lambda x: x.strip() if isinstance(x, str) else x)
            # 将'nan'字符串转为空值
            df['评语'] = df['评语'].replace('nan', np.nan)
            df['评语'] = df['评语'].replace('NaN', np.nan)
            df['评语'] = df['评语'].replace('None', np.nan)
            df['评语'] = df['评语'].replace('', np.nan)
        
        # 删除姓名或评语为空的行
        df = df.dropna(subset=['姓名', '评语'])
        
        return df
    
    def _convert_to_comments(self, df):
        """将DataFrame转换为评语数据列表"""
        logger.info("开始将DataFrame转换为评语数据列表")
        
        comments_data = []
        
        for i, row in df.iterrows():
            if pd.isna(row['姓名']) or pd.isna(row['评语']):
                continue
                
            comment = {
                'name': str(row['姓名']).strip(),
                'comment': str(row['评语']).strip()
            }
            
            # 检查评语长度，不再自动截断，仅标记是否超过限制
            if len(comment['comment']) > 260:  # 临时调整为1000字
                logger.warning(f"学生[{comment['name']}]的评语超过260字符长度限制: {len(comment['comment'])}字")
                comment['truncated'] = False  # 不再截断，只是标记
                comment['valid'] = False  # 标记为无效
            else:
                comment['truncated'] = False
                comment['valid'] = True  # 标记为有效
            
            # 检查评语长度是否有效（不超过1000个字符）
            is_valid = len(comment['comment']) <= 260
            if is_valid:
                valid_count += 1
            
            preview = {
                'name': comment['name'],
                'comment': comment['comment'],
                'matched': False,
                'length': len(comment['comment']),
                'valid': is_valid,
                'valid_text': "有效" if is_valid else "无效(超过260字)"  # 临时调整为1000字
            }
            
            # 检查学生是否存在
            if comment['name'] in students_dict:
                preview['matched'] = True
                preview['student_id'] = students_dict[comment['name']]['id']
                match_count += 1
            
            matched_comments.append(preview)
        
        logger.info(f"评语匹配完成，总计: {total_count}, 成功匹配: {match_count}, 有效评语: {valid_count}")
        
        return {
            'previews': matched_comments,
            'total_count': total_count,
            'match_count': match_count,
            'valid_count': valid_count,
            'all_valid': valid_count == total_count  # 是否所有评语都有效
        }
    
    def _generate_html_preview(self, comments_data):
        """生成HTML预览表格"""
        logger.info("生成评语数据HTML预览表格")
        
        html = """
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th width="5%">#</th>
                        <th width="15%">姓名</th>
                        <th width="80%">评语</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # 添加评语数据行
        for i, comment in enumerate(comments_data, 1):
            # 处理评语显示，对超过100字符的评语进行截断显示
            preview_comment = comment['comment']
            if len(preview_comment) > 100:
                preview_comment = preview_comment[:100] + "..."
            
            # 对HTML特殊字符进行转义，防止XSS攻击
            name = comment['name'].replace('<', '&lt;').replace('>', '&gt;')
            preview_comment = preview_comment.replace('<', '&lt;').replace('>', '&gt;')
            
            # 如果评语被截断，添加警告提示
            truncated_warning = '<span class="text-warning">(已截断)</span>' if comment.get('truncated', False) else ''
            
            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{name}</td>
                    <td>{preview_comment} {truncated_warning}</td>
                </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        <div class="alert alert-info">
            <i class='bx bx-info-circle'></i> 共发现 """ + str(len(comments_data)) + """ 条评语数据，点击"确认导入"按钮完成导入。
        </div>
        """
        
        return html

    def match_students_with_comments(self, comments_data, students_dict):
        """将评语数据与学生信息匹配"""
        logger.info(f"开始匹配评语数据与学生信息，评语数量: {len(comments_data)}, 学生数量: {len(students_dict)}")
        
        matched_comments = []
        total_count = len(comments_data)
        match_count = 0
        valid_count = 0  # 有效评语数量（长度不超过1000个字）
        
        for comment in comments_data:
            student_name = comment['name']
            comment_content = comment['comment']
            comment_length = len(comment_content)
            
            # 检查评语长度是否有效（不超过1000个字符）
            is_valid = comment_length <= 5000  # 修改为5000字  # 临时调整为1000字
            if is_valid:
                valid_count += 1
            
            preview = {
                'name': student_name,
                'comment': comment_content,
                'matched': False,
                'length': comment_length,
                'valid': is_valid,
                'valid_text': "有效" if is_valid else "无效(超过260字)"  # 临时调整为1000字
            }
            
            # 检查学生是否存在
            if student_name in students_dict:
                preview['matched'] = True
                preview['student_id'] = students_dict[student_name]['id']
                match_count += 1
            
            matched_comments.append(preview)
        
        logger.info(f"评语匹配完成，总计: {total_count}, 成功匹配: {match_count}, 有效评语: {valid_count}")
        
        return {
            'previews': matched_comments,
            'total_count': total_count,
            'match_count': match_count,
            'valid_count': valid_count,
            'all_valid': valid_count == total_count  # 是否所有评语都有效
        }

# 用于命令行测试
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python excel_processor.py <excel_file_path> [comments]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # 判断是否处理评语数据
    if len(sys.argv) > 2 and sys.argv[2] == "comments":
        processor = CommentsExcelProcessor()
    else:
        processor = ExcelProcessor()
        
    result = processor.process_file(file_path)
    
    if 'error' in result:
        print(f"错误: {result['error']}")
    else:
        if 'comments' in result:
            print(f"成功解析 {len(result['comments'])} 条评语记录")
            # 输出前两条评语记录作为示例
            if result['comments']:
                print("\n前两条评语记录:")
                for i, comment in enumerate(result['comments'][:2], 1):
                    print(f"评语 {i}:")
                    for key, value in comment.items():
                        print(f"  {key}: {value}")
        else:
            print(f"成功解析 {len(result['students'])} 条学生记录")
            # 输出前两条学生记录作为示例
            if result['students']:
                print("\n前两条学生记录:")
                for i, student in enumerate(result['students'][:2], 1):
                    print(f"学生 {i}:")
                    for key, value in student.items():
                        print(f"  {key}: {value}")
        
        # 将结果保存到JSON文件，方便检查
        output_file = f"{file_path}.processed.json"
        data_to_save = result.get('comments', result.get('students', []))
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        print(f"\n完整结果已保存到: {output_file}") 