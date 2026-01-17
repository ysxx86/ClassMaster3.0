#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
班主任绩效考核系统测试脚本
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_structure():
    """测试数据库结构"""
    logger.info("=" * 60)
    logger.info("测试1: 检查数据库表结构")
    logger.info("=" * 60)
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    # 检查必要的表是否存在
    required_tables = [
        'performance_items',
        'performance_evaluators',
        'performance_scores',
        'performance_results'
    ]
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    all_exist = True
    for table in required_tables:
        if table in existing_tables:
            logger.info(f"✓ 表 {table} 存在")
        else:
            logger.error(f"✗ 表 {table} 不存在")
            all_exist = False
    
    # 检查users表的teacher_type字段
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'teacher_type' in columns:
        logger.info("✓ users表包含teacher_type字段")
    else:
        logger.error("✗ users表缺少teacher_type字段")
        all_exist = False
    
    conn.close()
    return all_exist

def test_default_items():
    """测试默认考核项目"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 检查默认考核项目")
    logger.info("=" * 60)
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM performance_items")
    count = cursor.fetchone()[0]
    
    logger.info(f"考核项目总数: {count}")
    
    if count >= 17:
        logger.info("✓ 默认考核项目已插入")
        
        # 显示各类别的项目数量
        cursor.execute("""
            SELECT category, COUNT(*) as count, SUM(weight) as total_weight
            FROM performance_items
            WHERE is_active = 1
            GROUP BY category
        """)
        
        logger.info("\n各类别统计:")
        total_weight = 0
        for row in cursor.fetchall():
            logger.info(f"  {row[0]}: {row[1]}个项目, 权重合计: {row[2]}%")
            total_weight += row[2]
        
        logger.info(f"\n总权重: {total_weight}%")
        
        if abs(total_weight - 100) < 0.01:
            logger.info("✓ 权重合计正确（100%）")
            result = True
        else:
            logger.warning(f"⚠ 权重合计不等于100%（当前: {total_weight}%）")
            result = False
    else:
        logger.error(f"✗ 考核项目数量不足（期望>=17，实际{count}）")
        result = False
    
    conn.close()
    return result

def test_api_structure():
    """测试API结构"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 检查API模块结构")
    logger.info("=" * 60)
    
    try:
        from performance import performance_bp, init_performance
        logger.info("✓ performance模块导入成功")
        
        # 检查蓝图是否有预期的端点
        logger.info(f"✓ 蓝图名称: {performance_bp.name}")
        logger.info(f"✓ 蓝图URL前缀: {performance_bp.url_prefix}")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ 导入performance模块失败: {str(e)}")
        return False

def test_frontend_files():
    """测试前端文件"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 检查前端文件")
    logger.info("=" * 60)
    
    import os
    
    required_files = [
        'pages/performance.html',
        'js/performance.js',
        'css/performance.css'
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            logger.info(f"✓ {file_path} 存在 ({size} bytes)")
        else:
            logger.error(f"✗ {file_path} 不存在")
            all_exist = False
    
    return all_exist

def test_integration():
    """测试系统集成"""
    logger.info("\n" + "=" * 60)
    logger.info("测试5: 检查系统集成")
    logger.info("=" * 60)
    
    try:
        # 检查index.html是否包含绩效考核入口
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'performance' in content and '班主任考核' in content:
                logger.info("✓ index.html包含绩效考核入口")
            else:
                logger.warning("⚠ index.html可能缺少绩效考核入口")
                return False
        
        # 检查server.py是否注册了蓝图
        with open('server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'performance_bp' in content and 'init_performance' in content:
                logger.info("✓ server.py已注册绩效考核蓝图")
            else:
                logger.error("✗ server.py未注册绩效考核蓝图")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 集成测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    logger.info("\n" + "=" * 60)
    logger.info("班主任绩效考核系统 - 完整性测试")
    logger.info("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("数据库结构", test_database_structure()))
    results.append(("默认考核项目", test_default_items()))
    results.append(("API模块结构", test_api_structure()))
    results.append(("前端文件", test_frontend_files()))
    results.append(("系统集成", test_integration()))
    
    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        if result:
            logger.info(f"✓ {test_name}: 通过")
            passed += 1
        else:
            logger.error(f"✗ {test_name}: 失败")
            failed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"总计: {passed}个测试通过, {failed}个测试失败")
    logger.info("=" * 60)
    
    if failed == 0:
        logger.info("\n🎉 所有测试通过！系统已准备就绪。")
        return True
    else:
        logger.warning(f"\n⚠️  有{failed}个测试失败，请检查相关问题。")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
