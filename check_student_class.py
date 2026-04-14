import sqlite3
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库路径
DATABASE = 'students.db'

def check_database_structure():
    """检查数据库结构"""
    logger.info("=== 检查数据库结构 ===")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查学生表结构
    cursor.execute("PRAGMA table_info(students)")
    student_columns = cursor.fetchall()
    logger.info(f"学生表字段数: {len(student_columns)}")
    logger.info(f"学生表主要字段: id, name, class, class_id")
    
    # 检查班级表结构
    cursor.execute("PRAGMA table_info(classes)")
    class_columns = cursor.fetchall()
    logger.info(f"班级表字段数: {len(class_columns)}")
    for col in class_columns:
        logger.info(f"  班级表字段: {col['name']}")
    
    conn.close()

def check_data_consistency():
    """检查数据一致性"""
    logger.info("\n=== 检查数据一致性 ===")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取班级数据
    cursor.execute("SELECT id, class_name FROM classes")
    classes = cursor.fetchall()
    logger.info(f"班级总数: {len(classes)}")
    
    class_dict = {}
    for class_row in classes:
        class_id = class_row['id']
        class_name = class_row['class_name']
        class_dict[class_id] = class_name
        logger.info(f"班级: ID={class_id}, 名称={class_name}")
    
    # 获取学生数量
    cursor.execute("SELECT COUNT(*) FROM students")
    student_count = cursor.fetchone()[0]
    logger.info(f"学生总数: {student_count}")
    
    # 检查学生班级分布
    logger.info("\n班级学生分布:")
    for class_id, class_name in class_dict.items():
        cursor.execute("SELECT COUNT(*) FROM students WHERE class_id = ?", (class_id,))
        count = cursor.fetchone()[0]
        logger.info(f"班级 {class_name} (ID={class_id}): {count}名学生")
    
    # 检查学生class_id和class是否一致
    cursor.execute("""
        SELECT s.id, s.name, s.class, s.class_id, c.class_name
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        LIMIT 10
    """)
    students = cursor.fetchall()
    
    logger.info("\n学生班级关联示例:")
    for student in students:
        logger.info(f"学生: {student['id']} - {student['name']}")
        logger.info(f"  class_id = {student['class_id']}, class = {student['class']}")
        logger.info(f"  关联班级名称 = {student['class_name']}")
        
        # 检查class和class_name是否一致
        if student['class'] != student['class_name']:
            logger.warning(f"  不一致! class={student['class']} 与 class_name={student['class_name']} 不匹配")
    
    # 检查没有关联到班级的学生
    cursor.execute("""
        SELECT COUNT(*) FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE c.id IS NULL
    """)
    orphan_count = cursor.fetchone()[0]
    logger.info(f"\n没有有效class_id关联的学生数: {orphan_count}")
    
    if orphan_count > 0:
        cursor.execute("""
            SELECT id, name, class, class_id FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE c.id IS NULL
            LIMIT 5
        """)
        orphans = cursor.fetchall()
        logger.info("示例无班级关联学生:")
        for student in orphans:
            logger.info(f"  ID={student['id']}, 姓名={student['name']}, class={student['class']}, class_id={student['class_id']}")
    
    conn.close()

def check_deyu_data():
    """检查德育维度数据分布"""
    logger.info("\n=== 检查德育维度数据 ===")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查学生总数
    cursor.execute("SELECT COUNT(*) FROM students")
    student_count = cursor.fetchone()[0]
    
    # 检查有德育维度数据的学生数量
    cursor.execute("""
        SELECT COUNT(*) FROM students 
        WHERE pinzhi IS NOT NULL OR xuexi IS NOT NULL OR jiankang IS NOT NULL OR 
              shenmei IS NOT NULL OR shijian IS NOT NULL OR shenghuo IS NOT NULL
    """)
    with_deyu_count = cursor.fetchone()[0]
    logger.info(f"有德育维度数据的学生数: {with_deyu_count}/{student_count}")
    
    # 检查每个班级的德育维度数据分布
    cursor.execute("""
        SELECT s.class_id, c.class_name, COUNT(*) as student_count,
               SUM(CASE WHEN s.pinzhi IS NOT NULL THEN 1 ELSE 0 END) as pinzhi_count
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        GROUP BY s.class_id
    """)
    class_stats = cursor.fetchall()
    
    logger.info("\n班级德育数据统计:")
    for stat in class_stats:
        logger.info(f"班级: {stat['class_name'] or '未知'} (ID={stat['class_id']})")
        logger.info(f"  学生总数: {stat['student_count']}, 有品质数据的学生: {stat['pinzhi_count']}")
        
        # 样本检查
        cursor.execute("""
            SELECT id, name, pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo
            FROM students
            WHERE class_id = ?
            LIMIT 3
        """, (stat['class_id'],))
        samples = cursor.fetchall()
        
        logger.info("  样本学生德育数据:")
        for sample in samples:
            logger.info(f"    {sample['id']} - {sample['name']}: 品质={sample['pinzhi']}, 学习={sample['xuexi']}")
    
    conn.close()

if __name__ == "__main__":
    check_database_structure()
    check_data_consistency()
    check_deyu_data() 