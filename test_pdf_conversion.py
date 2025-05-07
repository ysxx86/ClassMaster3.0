import os
import sys
import tempfile
from docx2pdf import convert
import traceback

def test_pdf_conversion():
    try:
        print("开始测试PDF转换功能...")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 尝试使用docx2pdf库转换一个示例文件
            # 首先检查是否有示例文件
            example_file = None
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file.endswith('.docx'):
                        example_file = os.path.join(root, file)
                        break
                if example_file:
                    break
            
            if not example_file:
                print("错误：找不到任何.docx文件进行测试！")
                sys.exit(1)
            
            print(f"找到示例文件: {example_file}")
            
            # 输出目录
            output_dir = os.path.join(temp_dir, "pdf_output")
            os.makedirs(output_dir, exist_ok=True)
            
            # 进行转换
            print(f"正在将文件 {example_file} 转换为PDF...")
            convert(example_file, os.path.join(output_dir, "test_output.pdf"))
            
            # 检查是否成功生成PDF
            output_pdf = os.path.join(output_dir, "test_output.pdf")
            if os.path.exists(output_pdf):
                print(f"转换成功! 生成的PDF文件: {output_pdf}")
                print(f"文件大小: {os.path.getsize(output_pdf)} 字节")
            else:
                print("转换失败：未生成PDF文件")
                
    except Exception as e:
        print(f"转换过程中出错: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_conversion() 