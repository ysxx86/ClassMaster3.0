import os

# 配置
UPLOAD_FOLDER = 'uploads'
TEMPLATE_FOLDER = 'templates'
EXPORTS_FOLDER = 'exports'
DATABASE = 'students.db'

# 确保所有必要的文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)
os.makedirs(EXPORTS_FOLDER, exist_ok=True)
