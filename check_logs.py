import os
import glob
import subprocess
import time

def get_latest_logs():
    """获取最近修改的日志文件"""
    log_files = glob.glob("logs/*.log")
    return sorted(log_files, key=os.path.getmtime, reverse=True)

if __name__ == "__main__":
    latest_logs = get_latest_logs()
    
    for log_file in latest_logs[:3]:  # 只看最近的3个日志文件
        print(f"\n{'=' * 50}")
        print(f"日志文件: {log_file}")
        print(f"{'=' * 50}")
        
        # 使用tail命令获取文件的最后20行
        result = subprocess.run(["tail", "-n", "30", log_file], capture_output=True, text=True)
        print(result.stdout)
        
        # 使用grep查找错误信息
        print(f"\n错误日志 (ERROR/Exception):")
        result = subprocess.run(["grep", "-i", "error\\|exception\\|traceback", log_file], 
                               capture_output=True, text=True)
        print(result.stdout or "未找到错误信息") 