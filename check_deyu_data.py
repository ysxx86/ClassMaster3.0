import sqlite3
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库路径
DATABASE = 'students.db'

def check_deyu_data():
    """检查德育维度字段的数据情况"""
    logger.info("开始检查德育维度数据...")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查students表结构
    cursor.execute("PRAGMA table_info(students)")
    columns = cursor.fetchall()
    column_names = [col['name'] for col in columns]
    
    # 检查德育维度字段是否存在
    deyu_fields = ['pinzhi', 'xuexi', 'jiankang', 'shenmei', 'shijian', 'shenghuo']
    missing_fields = [field for field in deyu_fields if field not in column_names]
    
    if missing_fields:
        logger.error(f"缺少以下德育维度字段: {missing_fields}")
    else:
        logger.info("所有德育维度字段已存在")
    
    # 检查是否有数据
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]
    logger.info(f"学生总数: {total_students}")
    
    # 检查有德育维度数据的学生数量
    cursor.execute("""
        SELECT COUNT(*) FROM students 
        WHERE pinzhi IS NOT NULL OR xuexi IS NOT NULL OR jiankang IS NOT NULL OR 
              shenmei IS NOT NULL OR shijian IS NOT NULL OR shenghuo IS NOT NULL
    """)
    students_with_deyu = cursor.fetchone()[0]
    logger.info(f"有德育维度数据的学生数量: {students_with_deyu}")
    
    # 检查每个维度有数据的学生数量
    for field in deyu_fields:
        cursor.execute(f"SELECT COUNT(*) FROM students WHERE {field} IS NOT NULL AND {field} > 0")
        count = cursor.fetchone()[0]
        logger.info(f"有 {field} 维度数据的学生数量: {count}")
    
    # 检查样本数据
    cursor.execute("""
        SELECT id, name, class, pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo
        FROM students
        LIMIT 5
    """)
    sample_data = cursor.fetchall()
    
    logger.info("学生样本数据:")
    for student in sample_data:
        logger.info(f"ID: {student['id']}, 姓名: {student['name']}, 班级: {student['class']}")
        logger.info(f"  品质: {student['pinzhi']}, 学习: {student['xuexi']}, 健康: {student['jiankang']}")
        logger.info(f"  审美: {student['shenmei']}, 实践: {student['shijian']}, 生活: {student['shenghuo']}")
    
    conn.close()

def add_test_data():
    """添加测试数据到德育维度字段"""
    user_input = input("是否要添加测试数据? (y/n): ")
    if user_input.lower() != 'y':
        return
    
    logger.info("开始添加测试数据...")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 查询所有学生ID
    cursor.execute("SELECT id FROM students")
    student_ids = [row[0] for row in cursor.fetchall()]
    
    if not student_ids:
        logger.error("没有找到学生记录")
        conn.close()
        return
    
    # 为所有学生添加随机德育维度分数
    import random
    
    updated_count = 0
    for student_id in student_ids:
        try:
            # 生成随机分数
            pinzhi = random.randint(20, 30)  # 品质 30分
            xuexi = random.randint(15, 20)   # 学习 20分
            jiankang = random.randint(15, 20) # 健康 20分
            shenmei = random.randint(7, 10)   # 审美 10分
            shijian = random.randint(7, 10)   # 实践 10分
            shenghuo = random.randint(7, 10)  # 生活 10分
            
            # 更新学生记录
            cursor.execute("""
                UPDATE students 
                SET pinzhi = ?, xuexi = ?, jiankang = ?, shenmei = ?, shijian = ?, shenghuo = ?
                WHERE id = ?
            """, (pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo, student_id))
            
            updated_count += 1
            
            # 每50条提交一次
            if updated_count % 50 == 0:
                conn.commit()
                logger.info(f"已更新 {updated_count}/{len(student_ids)} 名学生的德育维度数据")
        except Exception as e:
            logger.error(f"更新学生ID {student_id} 的德育维度数据时出错: {e}")
    
    # 最后提交
    conn.commit()
    
    # 验证更新
    cursor.execute("""
        SELECT COUNT(*) FROM students 
        WHERE pinzhi IS NOT NULL AND xuexi IS NOT NULL AND jiankang IS NOT NULL AND 
              shenmei IS NOT NULL AND shijian IS NOT NULL AND shenghuo IS NOT NULL
    """)
    verified_count = cursor.fetchone()[0]
    
    logger.info(f"成功添加测试数据，共更新了 {updated_count}/{len(student_ids)} 名学生的德育维度数据")
    logger.info(f"验证结果: {verified_count} 名学生有完整的德育维度数据")
    
    # 显示样本数据
    cursor.execute("""
        SELECT id, name, class, pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo
        FROM students
        LIMIT 5
    """)
    sample_data = cursor.fetchall()
    
    logger.info("更新后的学生样本数据:")
    for student in sample_data:
        logger.info(f"ID: {student[0]}, 姓名: {student[1]}, 班级: {student[2]}")
        logger.info(f"  品质: {student[3]}, 学习: {student[4]}, 健康: {student[5]}")
        logger.info(f"  审美: {student[6]}, 实践: {student[7]}, 生活: {student[8]}")
    
    conn.close()

if __name__ == "__main__":
    check_deyu_data()
    add_test_data() 