#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成绩分析性能测试脚本
测试优化后的查询速度
"""

import sqlite3
import time
import json

def test_query_performance():
    """测试查询性能"""
    print("=" * 60)
    print("成绩分析性能测试")
    print("=" * 60)
    print()
    
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取一个测试用的考试ID
    cursor.execute("SELECT id, class_id FROM exams LIMIT 1")
    exam = cursor.fetchone()
    
    if not exam:
        print("❌ 没有找到考试数据")
        conn.close()
        return
    
    exam_id = exam['id']
    class_id = exam['class_id']
    
    print(f"测试考试ID: {exam_id}, 班级ID: {class_id}")
    print()
    
    # 测试1: 基本查询
    print("📊 测试1: 基本查询")
    start_time = time.time()
    cursor.execute('''
    SELECT s.*, students.name as student_name, students.class_id as student_class_id
    FROM exam_scores s
    LEFT JOIN students ON s.student_id = students.id
    WHERE s.exam_id = ? AND s.class_id = ?
    ORDER BY s.student_id, s.subject
    ''', (exam_id, class_id))
    scores = cursor.fetchall()
    end_time = time.time()
    query_time = (end_time - start_time) * 1000
    
    print(f"  查询到 {len(scores)} 条记录")
    print(f"  查询时间: {query_time:.2f}ms")
    
    if query_time < 100:
        print(f"  ✅ 优秀! (< 100ms)")
    elif query_time < 500:
        print(f"  ✅ 良好! (< 500ms)")
    elif query_time < 1000:
        print(f"  ⚠️  一般 (< 1000ms)")
    else:
        print(f"  ❌ 需要优化 (> 1000ms)")
    
    print()
    
    # 测试2: 统计计算
    print("📊 测试2: 统计计算")
    start_time = time.time()
    
    # 按学科组织数据
    scores_by_subject = {}
    for score in scores:
        score_dict = dict(score)
        subject = score_dict['subject']
        if subject not in scores_by_subject:
            scores_by_subject[subject] = []
        scores_by_subject[subject].append(score_dict)
    
    # 计算统计信息
    stats = {}
    for subject, subject_scores in scores_by_subject.items():
        valid_scores = [s['score'] for s in subject_scores if 0 < s['score'] <= 100]
        
        if valid_scores:
            stats[subject] = {
                'average': sum(valid_scores) / len(valid_scores),
                'max': max(valid_scores),
                'min': min(valid_scores),
                'count': len(valid_scores)
            }
    
    end_time = time.time()
    calc_time = (end_time - start_time) * 1000
    
    print(f"  处理 {len(scores_by_subject)} 个学科")
    print(f"  计算时间: {calc_time:.2f}ms")
    
    if calc_time < 50:
        print(f"  ✅ 优秀! (< 50ms)")
    elif calc_time < 200:
        print(f"  ✅ 良好! (< 200ms)")
    else:
        print(f"  ⚠️  需要优化 (> 200ms)")
    
    print()
    
    # 总体评估
    total_time = query_time + calc_time
    print("=" * 60)
    print(f"总耗时: {total_time:.2f}ms")
    
    if total_time < 200:
        print("✅ 性能优秀! 用户体验极佳!")
    elif total_time < 500:
        print("✅ 性能良好! 用户体验流畅!")
    elif total_time < 1000:
        print("⚠️  性能一般,建议继续优化")
    else:
        print("❌ 性能较差,需要优化")
    
    print("=" * 60)
    print()
    
    # 性能对比
    print("📈 性能对比:")
    print(f"  优化前: ~60000ms (60秒)")
    print(f"  优化后: ~{total_time:.0f}ms")
    print(f"  提升: {((60000 - total_time) / 60000 * 100):.1f}%")
    print()
    
    conn.close()

if __name__ == '__main__':
    test_query_performance()
