#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据验证模块，用于验证学生报告导出前的数据完整性
"""

import logging
from typing import Dict, List, Tuple, Any, Union

# 配置日志
logger = logging.getLogger(__name__)

class DataValidator:
    """
    数据验证类，用于各种数据完整性验证操作
    """
    
    @staticmethod
    def validate_export_data(students: List[Dict[str, Any]], 
                            comments: Dict[str, Dict[str, Any]], 
                            grades: Dict[str, Dict[str, Any]]) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        验证导出报告前的数据完整性
        
        Args:
            students: 学生信息列表
            comments: 学生评语字典，键为学生ID
            grades: 学生成绩字典，键为学生ID
            
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: (是否通过验证, 错误消息, 有问题的学生列表)
        """
        problem_students = []
        
        # 用于判断"所有学生成绩等级都是优"的状态
        all_excellent_count = 0
        students_with_grades_count = 0
        
        # 用于判断"所有学生的德育维度每项都是满分"的状态
        all_max_deyu_count = 0
        students_with_deyu_count = 0
        
        # 德育维度满分配置
        deyu_max_scores = {
            'pinzhi': 30,
            'xuexi': 20,
            'jiankang': 20,
            'shenmei': 10,
            'shijian': 10,
            'shenghuo': 10
        }
        
        # 遍历所有学生进行验证
        for student in students:
            student_id = student.get('id')
            student_name = student.get('name', '未知姓名')
            problems = []
            
            # 验证1: 学生个人信息是否完整
            required_fields = [
                ('name', '姓名'), 
                ('gender', '性别'), 
                ('class', '班级'),
                ('height', '身高'), 
                ('weight', '体重'), 
                ('chest_circumference', '胸围'),
                ('vital_capacity', '肺活量'), 
                ('dental_caries', '龋齿'), 
                ('vision_left', '左眼视力'),
                ('vision_right', '右眼视力'), 
                ('physical_test_status', '体测情况')
            ]
            
            for field, field_name in required_fields:
                if field not in student or not student[field]:
                    problems.append(f"缺少{field_name}")
            
            # 验证2: 学生评语是否完整
            if student_id not in comments or not comments[student_id].get('content'):
                problems.append("评语不能为空")
            
            # 验证3: 学生成绩等级是否填写
            grade_fields = [
                'daof', 'yuwen', 'shuxue', 'yingyu', 'laodong', 
                'tiyu', 'yinyue', 'meishu', 'kexue', 'zonghe', 
                'xinxi', 'shufa'
            ]
            
            missing_grades = []
            grades_record = grades.get(student_id, {}).get('grades', {})
            
            # 检查成绩是否全部为"优"
            is_all_excellent = True
            has_grades = False
            
            for field in grade_fields:
                if field not in grades_record or not grades_record[field]:
                    missing_grades.append(field)
                else:
                    has_grades = True
                    if grades_record[field] != '优':
                        is_all_excellent = False
            
            if missing_grades:
                problems.append(f"缺少成绩等级: {', '.join(missing_grades)}")
            
            if has_grades:
                students_with_grades_count += 1
                if is_all_excellent:
                    all_excellent_count += 1
            
            # 验证4: 学生德育维度是否填写
            deyu_fields = [
                ('pinzhi', '品质'), 
                ('xuexi', '学习'), 
                ('jiankang', '健康'),
                ('shenmei', '审美'), 
                ('shijian', '实践'), 
                ('shenghuo', '生活'),
                ('xinli', '心理')
            ]
            
            missing_deyu = []
            is_all_max_deyu = True
            has_deyu = False
            
            for field, field_name in deyu_fields:
                if field not in student or student[field] in (None, ''):
                    missing_deyu.append(field_name)
                else:
                    has_deyu = True
                    # 检查是否为满分
                    if field in deyu_max_scores:
                        try:
                            score = int(student[field])
                            if score < deyu_max_scores[field]:
                                is_all_max_deyu = False
                        except (ValueError, TypeError):
                            is_all_max_deyu = False
            
            if missing_deyu:
                problems.append(f"缺少德育维度评价: {', '.join(missing_deyu)}")
            
            if has_deyu:
                students_with_deyu_count += 1
                if is_all_max_deyu:
                    all_max_deyu_count += 1
            
            # 收集问题学生信息
            if problems:
                problem_students.append({
                    'id': student_id,
                    'name': student_name,
                    'problems': problems
                })
        
        # 验证5: 不能所有学生的成绩等级都是"优"
        all_excellent = False
        if students_with_grades_count > 0 and all_excellent_count == students_with_grades_count:
            all_excellent = True
            logger.warning(f"所有学生的成绩等级均为'优', 共 {all_excellent_count} 名学生")
        
        # 验证6: 不能所有学生的德育维度每项都是满分
        all_max_deyu = False
        if students_with_deyu_count > 0 and all_max_deyu_count == students_with_deyu_count:
            all_max_deyu = True
            logger.warning(f"所有学生的德育维度均为满分, 共 {all_max_deyu_count} 名学生")
        
        # 生成整体验证结果
        if problem_students:
            error_message = f"发现 {len(problem_students)} 名学生的数据不完整，无法导出报告。"
            return False, error_message, problem_students
        
        if all_excellent:
            error_message = "成绩管理中所有学生的成绩等级均为'优'，不符合实际情况，请修改部分学生的成绩等级后再导出报告。"
            return False, error_message, []
        
        if all_max_deyu:
            error_message = "德育维度中所有学生的所有维度均为满分，不符合实际情况，请修改部分学生的德育维度分数后再导出报告。"
            return False, error_message, []
        
        return True, "", [] 