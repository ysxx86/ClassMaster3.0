# ClassMaster 班级智慧管理系统

> 基于 DeepSeek 大模型的班主任智能工作台 · 开源 · 免费 · 即开即用

![Python](https://img.shields.io/badge/Python-3.8+-3572A5?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.0-000000?style=flat-square&logo=flask&logoColor=white)
![DeepSeek](https://img.shields.io/badge/AI-DeepSeek%20V3%2FR1-4B6CB7?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-2ECC71?style=flat-square)
![落地规模](https://img.shields.io/badge/落地规模-33班级%20·%201年实战-E74C3C?style=flat-square)

---

## 📖 项目简介

**ClassMaster** 是由一名小学班主任借助 DeepSeek 等 AI 工具独立开发的智能信息系统，专为解决班主任期末高峰期三大核心痛点而设计：

| 痛点 | 传统方式 | ClassMaster 方案 |
|------|----------|-----------------|
| 素质评语撰写耗时 | 手工逐一撰写，单班约需 **3天** | AI 批量生成草稿，微调确认，单班约需 **半天** |
| 成绩分析繁琐 | Excel 手工计算，耗时约 **2小时** | 上传即分析，自动生成报告，约 **15分钟** |
| 德育评价分散 | 纸质记录，学期末手工汇总 | 实时录入，一键汇总生成评价 |

系统已在**全校 33 个班级**持续使用逾一年，覆盖约 1400 名学生，目前已成为学校班主任工作的常态化工具。

---

## ✨ 核心功能

### 🤖 AI 智能评语
- 调用 **DeepSeek-V3 / DeepSeek-R1** 国产大模型
- 结构化提示词模板，将学生性别、各科素质等级、德育表现注入上下文
- 批量生成个性化素质评语，支持人工微调
- 一键导出 Word 文档

### 📊 成绩智能分析
- 多科目成绩 Excel 批量导入
- 自动计算优秀率、及格率、平均分
- 分数段分布统计（0-59 / 60-69 / 70-79 / 80-89 / 90-100）
- 多次考试横向对比趋势分析
- 根据年级自动调整优秀标准（一二年级 90 分、三四年级 85 分、五六年级 80 分）
- 可视化图表展示

### 📝 德育综合评价
- 品德表现实时记录
- 学期末一键汇总
- AI 辅助生成发展性评价

### 👥 学生信息管理
- Excel 批量导入学生名单
- 学籍信息维护
- 学生档案管理

### 🔐 多角色权限管理
- **管理员**：全校数据管理、用户账号管理
- **班主任**：仅可访问本班数据，数据严格隔离
- **科任教师**：可查看所教班级的相关数据

### 📤 数据导出
- 评语一键导出 Word 格式
- 成绩分析报告导出 Excel 格式

### 📈 实时仪表盘
- 班级数据总览
- 待办事项提醒
- 最新动态追踪

---

## 🚀 快速开始

### 环境要求

- 操作系统：Windows 10/11（推荐），macOS 或 Linux 亦可
- Python：**3.8 或以上版本**
- DeepSeek API Key：前往 [platform.deepseek.com](https://platform.deepseek.com) 免费申请

### 安装步骤

**第一步：克隆仓库**

```bash
git clone https://github.com/ysxx86/ClassMaster2.2.git
cd ClassMaster2.2
```

**第二步：安装依赖**

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**第三步：配置 DeepSeek API 密钥**

复制环境变量模板文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-你的密钥写在这里
```

> ⚠️ **安全提示**：请勿将真实 API Key 写入代码文件或提交至 Git 仓库。

**第四步：启动系统**

```bash
python server.py
```

**第五步：访问系统**

打开浏览器访问：[http://localhost:8080](http://localhost:8080)

使用管理员账号登录：
- 用户名：`admin`
- 密码：`admin123`

> ⚠️ 首次登录后请**立即修改管理员密码**。

---

## 📋 使用指南

### 初始化配置

1. 管理员登录后，在 **【班级管理】** 中创建班级
2. 在 **【用户管理】** 中添加班主任账号并绑定班级
3. 班主任通过 **【学生管理】** 批量导入学生名单（Excel 格式）

### AI 评语使用流程

```
进入【评语管理】
    ↓
选择学期，填写学生各科素质等级和德育表现关键词
    ↓
点击【AI生成】→ DeepSeek 自动生成个性化评语草稿
    ↓
教师审阅微调
    ↓
一键导出 Word 文档
```

### 成绩分析使用流程

```
进入【成绩分析】→ 新建考试
    ↓
下载系统生成的 Excel 模板
    ↓
填写成绩后上传（支持标注"请假"状态）
    ↓
系统自动生成统计数据和可视化图表
    ↓
可选择多次考试进行横向趋势对比
```

---

## 📁 项目结构

```
ClassMaster2.2/
├── server.py                    # 启动入口
├── app_factory.py               # Flask 应用工厂
├── app.py                       # 应用主体
├── blueprint_registrar.py       # 蓝图注册
├── config.py                    # 配置文件
├── database.py                  # 数据库连接
│
├── grade_analysis.py            # 成绩分析模块（1206行）
├── comments.py                  # AI 评语模块
├── deyu.py                      # 德育评价模块
├── students.py                  # 学生管理模块
├── classes.py                   # 班级管理模块
├── grades.py                    # 成绩管理模块
├── dashboard.py                 # 仪表盘模块
│
├── api/                         # API 接口层
├── core/                        # 核心业务逻辑
├── utils/                       # 工具函数
│   └── deepseek_api.py          # DeepSeek API 集成
├── templates/                   # HTML 页面模板
├── static/                      # 静态资源（CSS/JS/图片）
├── pages/                       # 页面模块
│
├── requirements.txt             # 依赖列表
├── .env.example                 # 环境变量模板
└── .gitignore                   # Git 忽略配置
```

---

## 🛠️ 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Python 3.x + Flask 2.0 | 轻量级 Web 框架 |
| 用户认证 | Flask-Login | 会话管理与权限控制 |
| 数据库 | SQLite | 免配置本地存储 |
| AI 大模型 | DeepSeek-V3 / R1 | 国产大模型，评语生成与智能分析 |
| 数据处理 | Pandas + NumPy | 成绩统计与分析 |
| 文档处理 | python-docx + openpyxl | Word/Excel 导出 |
| 前端 | 原生 HTML + JavaScript + CSS | 无需复杂前端框架 |
| AI 开发工具 | Cursor IDE | AI 辅助编程（开发阶段使用）|

---

## 📊 应用数据

| 指标 | 数据 |
|------|------|
| 使用班级数 | 33 个班级 |
| 覆盖学生数 | 约 1400 名 |
| 持续使用时长 | 12 个月以上 |
| 代码提交次数 | 169 次 |
| 评语效率提升 | 约 6 倍（3天 → 半天）|
| 成绩分析效率提升 | 约 8 倍（2小时 → 15分钟）|

---

## ⚠️ 注意事项

- **隐私保护**：请勿将含有学生真实姓名的数据库文件上传至公开平台，数据库文件（`*.db`）已在 `.gitignore` 中排除
- **API 安全**：DeepSeek API Key 请通过 `.env` 文件配置，切勿写入代码
- **数据备份**：建议定期备份 `students.db` 数据库文件至安全位置
- **AI 内容标注**：系统生成的评语内容属于 AI 生成，在正式使用场景中请按相关规定标注 **【AI生成】**
- **学生隐私**：演示或分享截图时，请对学生姓名等个人信息进行脱敏处理

---

## 🤝 贡献与反馈

本项目由一线教师独立开发，欢迎以下方式参与：

- 🐛 **发现 Bug**：提交 [Issue](https://github.com/ysxx86/ClassMaster2.2/issues)
- 💡 **功能建议**：提交 Issue 并添加 `enhancement` 标签
- 🔧 **代码贡献**：Fork 后提交 Pull Request
- ⭐ **支持项目**：如本项目对你有帮助，欢迎 Star

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源，欢迎自由使用、修改和分发。

---

<p align="center">
  本项目由一位小学班主任借助 AI 工具开发<br>
  献给所有为教育默默付出的班主任老师 ❤️
</p>