# ClassMaster 2.0 - 智能班级管理系统

一个全面的班级学生管理系统，专为教师和学校管理员设计，提供学生信息管理、成绩记录、评语生成与管理等功能。

## 核心功能

- **用户权限管理**：支持管理员和教师权限分离，确保数据安全
- **学生信息管理**：完整的学生档案管理，包括基本信息、照片等
- **成绩记录与分析**：记录学生各科目成绩，支持等级评定和统计分析
- **AI评语生成**：集成DeepSeek API，智能生成个性化学生评语
- **德育评价管理**：全面的德育素质评价系统
- **综合素质报告**：生成PDF格式的学生综合素质报告
- **数据导入导出**：支持Excel批量导入导出学生和教师数据
- **数据备份恢复**：自动数据备份，确保数据安全

## 技术栈

### 后端
- **Python**：主要开发语言
- **Flask**：Web框架
- **SQLite**：数据存储
- **Flask-Login**：用户认证
- **Pandas & NumPy**：数据处理
- **ReportLab**：PDF生成

### 前端
- **HTML5 / CSS3 / JavaScript**
- **Bootstrap 5**：响应式UI组件
- **jQuery**：DOM操作
- **AJAX**：异步数据交互

## 系统要求

- Python 3.7+
- 支持Windows操作系统（推荐Windows 10或更高版本）
- 浏览器：Chrome、Edge、Firefox最新版

## 安装指南

1. 克隆代码仓库
   ```
   git clone https://github.com/yourusername/ClassMaster2.0.git
   cd ClassMaster2.0
   ```

2. 创建并激活虚拟环境（可选但推荐）
   ```
   python -m venv venv
   # Windows环境
   venv\Scripts\activate
   ```

3. 安装依赖
   ```
   pip install -r requirements.txt
   ```

4. 启动应用
   ```
   python server.py
   ```

5. 访问系统
   - 浏览器中打开: `http://localhost:5000`
   - 默认管理员账号: `admin`
   - 默认密码: `admin123`（首次登录后请立即修改）

## 系统配置

### DeepSeek API配置（可选）
如需使用AI生成评语功能，请在环境变量中设置DeepSeek API密钥：
```
# Windows
set DEEPSEEK_API_KEY=your_api_key_here
```

### 自定义密钥
为提高安全性，建议修改应用密钥：
```
# Windows
set SECRET_KEY=your_secret_key_here
```

## 用户指南

### 管理员
- 用户管理：创建/编辑教师账号，分配班级
- 系统设置：配置学年、学期及其他系统参数
- 数据管理：备份/恢复数据库

### 班主任
- 学生管理：管理班级学生信息
- 评语管理：编写/生成学生评语
- 成绩管理：记录学生成绩
- 德育评价：管理学生德育素质评价
- 报告生成：生成学生综合素质报告

## 数据备份

系统会在关键操作前自动创建数据库备份，备份文件存储在项目根目录，格式为：
```
students_backup_YYYYMMDD_HHMMSS.db
```

## 故障排除

1. **PDF导出失败**：确保已正确安装ReportLab库
2. **Word文档转换失败**：Windows环境需安装Microsoft Office和pywin32库
3. **数据导入错误**：检查Excel表格格式是否符合系统模板要求

## 开发者文档

系统采用模块化设计，主要模块包括：

- `server.py`：应用主入口和核心API路由
- `users.py`：用户管理模块
- `students.py`：学生信息管理
- `comments.py`：评语管理
- `grades.py`：成绩管理
- `deyu.py`：德育评价管理
- `classes.py`：班级管理

## 许可

本软件仅供教育用途，未经授权不得用于商业目的。