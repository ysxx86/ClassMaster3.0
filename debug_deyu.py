import sqlite3
import random
import time
import datetime

# 数据库文件
DATABASE = 'students.db'

def check_deyu_fields():
    """检查students表中是否有德育维度字段"""
    print("正在检查students表中的德育维度字段...")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 获取学生表的所有字段
    cursor.execute("PRAGMA table_info(students)")
    columns = cursor.fetchall()
    columns_names = [col[1] for col in columns]
    
    print(f"students表中的所有字段: {columns_names}")
    
    # 检查德育维度字段是否存在
    deyu_fields = ['pinzhi', 'xuexi', 'jiankang', 'shenmei', 'shijian', 'shenghuo']
    missing_fields = [field for field in deyu_fields if field not in columns_names]
    
    if missing_fields:
        print(f"缺少以下德育维度字段: {missing_fields}")
        # 添加缺失的字段
        for field in missing_fields:
            try:
                print(f"正在添加字段: {field}")
                cursor.execute(f"ALTER TABLE students ADD COLUMN {field} INTEGER")
                conn.commit()
                print(f"成功添加字段: {field}")
            except sqlite3.Error as e:
                print(f"添加字段失败: {field}, 错误: {e}")
    else:
        print("✓ 所有德育维度字段均已存在")
    
    # 查看学生总数
    cursor.execute("SELECT COUNT(*) FROM students")
    count = cursor.fetchone()[0]
    print(f"学生总数: {count}")
    
    # 如果有学生，检查几个样本的德育维度数据
    if count > 0:
        cursor.execute("SELECT id, name, pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo FROM students LIMIT 5")
        students = cursor.fetchall()
        
        print("\n当前学生德育维度数据样本:")
        for student in students:
            print(f"学生: {student[0]}, {student[1]}, 德育维度: {student[2:]}")
    
    conn.close()

def add_sample_deyu_data():
    """为所有学生添加样本德育维度数据"""
    print("\n正在添加德育维度样本数据...")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 获取所有学生ID
    cursor.execute("SELECT id FROM students")
    students = cursor.fetchall()
    
    if not students:
        print("没有找到学生数据")
        conn.close()
        return
    
    # 当前时间
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 批量更新所有学生的德育维度数据
    count = 0
    for student in students:
        student_id = student[0]
        
        # 生成随机德育维度数据
        pinzhi = random.randint(20, 30)     # 品质 (30分)
        xuexi = random.randint(15, 20)      # 学习 (20分)
        jiankang = random.randint(15, 20)   # 健康 (20分)
        shenmei = random.randint(7, 10)     # 审美 (10分)
        shijian = random.randint(7, 10)     # 实践 (10分)
        shenghuo = random.randint(7, 10)    # 生活 (10分)
        
        try:
            # 更新学生记录
            cursor.execute('''
                UPDATE students 
                SET pinzhi = ?, xuexi = ?, jiankang = ?, shenmei = ?, shijian = ?, shenghuo = ?, updated_at = ?
                WHERE id = ?
            ''', (pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo, now, student_id))
            count += 1
        except sqlite3.Error as e:
            print(f"更新学生 {student_id} 的德育维度数据失败: {e}")
    
    # 提交更改
    conn.commit()
    
    print(f"已为 {count} 名学生添加德育维度数据")
    
    # 验证数据已更新
    print("\n验证数据已成功更新:")
    cursor.execute("SELECT id, name, pinzhi, xuexi, jiankang, shenmei, shijian, shenghuo FROM students LIMIT 5")
    students = cursor.fetchall()
    
    for student in students:
        print(f"学生: {student[0]}, {student[1]}, 德育维度: {student[2:]}")
    
    conn.close()

if __name__ == "__main__":
    print("=== 德育维度数据调试工具 ===")
    check_deyu_fields()
    
    # 询问是否要添加样本数据
    answer = input("\n是否要为所有学生添加德育维度样本数据? (y/n): ")
    if answer.lower() == 'y':
        add_sample_deyu_data()
    
    print("\n完成! 现在可以在德育维度页面查看数据了。") 