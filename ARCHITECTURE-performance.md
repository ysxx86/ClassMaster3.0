# 班主任绩效考核系统 - 技术架构文档

## 系统架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                      │
├─────────────────────────────────────────────────────────────┤
│  pages/performance.html  │  js/performance.js  │  css/      │
│  - 页面结构              │  - 业务逻辑         │  - 样式    │
│  - Bootstrap 5 UI        │  - jQuery Ajax      │  - 响应式  │
│  - 标签页导航            │  - 数据交互         │  - 美化    │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTP/JSON
┌─────────────────────────────────────────────────────────────┐
│                        API层 (Backend)                        │
├─────────────────────────────────────────────────────────────┤
│  performance.py (Flask Blueprint)                            │
│  ├─ 考核项目管理 API                                         │
│  ├─ 评分人员管理 API                                         │
│  ├─ 评分录入 API                                             │
│  ├─ 结果计算 API                                             │
│  └─ 教师管理 API                                             │
└─────────────────────────────────────────────────────────────┘
                              ↕ SQL
┌─────────────────────────────────────────────────────────────┐
│                      数据层 (Database)                        │
├─────────────────────────────────────────────────────────────┤
│  students.db (SQLite)                                        │
│  ├─ users (扩展: teacher_type)                               │
│  ├─ performance_items (考核项目)                             │
│  ├─ performance_evaluators (评分人员)                        │
│  ├─ performance_scores (评分记录)                            │
│  └─ performance_results (考核结果)                           │
└─────────────────────────────────────────────────────────────┘
```

## 模块详细设计

### 1. 前端模块 (Frontend)

#### 1.1 页面结构 (pages/performance.html)

```html
├─ 页面头部
│  ├─ 标题和描述
│  └─ 导航标签
│     ├─ 评分录入
│     ├─ 考核结果
│     ├─ 考核项目 (管理员)
│     ├─ 评分人员 (管理员)
│     └─ 教师管理 (管理员)
│
├─ 评分录入面板
│  ├─ 学期选择器
│  ├─ 教师选择器
│  └─ 评分表单
│
├─ 考核结果面板
│  ├─ 学期选择器
│  ├─ 计算按钮 (管理员)
│  └─ 结果表格
│
├─ 考核项目面板 (管理员)
│  ├─ 添加按钮
│  └─ 项目列表
│
├─ 评分人员面板 (管理员)
│  ├─ 添加按钮
│  └─ 人员列表
│
└─ 教师管理面板 (管理员)
   └─ 教师类型设置
```

#### 1.2 JavaScript逻辑 (js/performance.js)

```javascript
主要功能模块:
├─ 用户认证
│  └─ getCurrentUser()
│
├─ 评分录入
│  ├─ loadScoreForm()
│  ├─ renderScoreForm()
│  └─ saveScore()
│
├─ 考核结果
│  ├─ loadResults()
│  ├─ renderResults()
│  └─ calculateResults()
│
├─ 考核项目管理
│  ├─ loadItems()
│  ├─ renderItems()
│  ├─ addItem()
│  ├─ editItem()
│  └─ deleteItem()
│
├─ 评分人员管理
│  ├─ loadEvaluators()
│  ├─ renderEvaluators()
│  └─ deleteEvaluator()
│
└─ 教师管理
   ├─ loadTeachers()
   ├─ renderTeachers()
   └─ updateTeacherType()
```

### 2. 后端模块 (Backend)

#### 2.1 API路由设计

```python
Blueprint: performance_bp
URL Prefix: /api/performance

路由列表:
├─ 考核项目管理
│  ├─ GET    /items              # 获取所有项目
│  ├─ POST   /items              # 添加项目
│  ├─ PUT    /items/<id>         # 更新项目
│  └─ DELETE /items/<id>         # 删除项目
│
├─ 评分人员管理
│  ├─ GET    /evaluators         # 获取所有评分人员
│  ├─ POST   /evaluators         # 添加评分人员
│  └─ DELETE /evaluators/<id>    # 删除评分人员
│
├─ 评分管理
│  ├─ POST   /scores             # 提交评分
│  └─ GET    /scores/<tid>/<sem> # 获取教师评分
│
├─ 结果管理
│  ├─ POST   /calculate/<sem>    # 计算结果
│  └─ GET    /results/<sem>      # 获取结果
│
└─ 教师管理
   ├─ GET    /teachers            # 获取所有教师
   └─ PUT    /teachers/<id>/type  # 更新教师类型
```

#### 2.2 权限控制

```python
装饰器层级:
├─ @login_required        # 所有API都需要登录
└─ @admin_required        # 管理功能需要管理员权限
   ├─ 考核项目管理
   ├─ 评分人员管理
   ├─ 教师类型设置
   └─ 结果计算
```

### 3. 数据库模块 (Database)

#### 3.1 表结构设计

```sql
-- 1. users表扩展
ALTER TABLE users ADD COLUMN teacher_type TEXT DEFAULT '正班主任';

-- 2. 考核项目表
CREATE TABLE performance_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,           -- 类别
    item_name TEXT NOT NULL,          -- 项目名称
    weight REAL NOT NULL,             -- 权重
    description TEXT,                 -- 说明
    is_active INTEGER DEFAULT 1,      -- 是否启用
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 3. 评分人员表
CREATE TABLE performance_evaluators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,         -- 用户ID
    item_id INTEGER,                  -- 项目ID (NULL=所有)
    can_evaluate_all INTEGER DEFAULT 0, -- 是否可评所有
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (item_id) REFERENCES performance_items(id)
);

-- 4. 评分记录表
CREATE TABLE performance_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,      -- 被评教师ID
    item_id INTEGER NOT NULL,         -- 项目ID
    evaluator_id INTEGER NOT NULL,    -- 评分人ID
    score REAL NOT NULL,              -- 分数
    semester TEXT NOT NULL,           -- 学期
    comments TEXT,                    -- 备注
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(id),
    FOREIGN KEY (item_id) REFERENCES performance_items(id),
    FOREIGN KEY (evaluator_id) REFERENCES users(id),
    UNIQUE(teacher_id, item_id, evaluator_id, semester)
);

-- 5. 考核结果表
CREATE TABLE performance_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,      -- 教师ID
    semester TEXT NOT NULL,           -- 学期
    total_score REAL,                 -- 总分
    rank INTEGER,                     -- 排名
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(id),
    UNIQUE(teacher_id, semester)
);
```

#### 3.2 数据关系图

```
users (教师)
  ├─ teacher_type: 正班主任/副班主任
  │
  ├─→ performance_evaluators (评分人员)
  │   └─→ performance_items (可评项目)
  │
  ├─→ performance_scores (评分记录)
  │   ├─→ performance_items (考核项目)
  │   └─→ users (评分人)
  │
  └─→ performance_results (考核结果)
      └─ 学期、总分、排名
```

## 核心算法

### 1. 评分计算算法

```python
def calculate_item_score(teacher_id, item_id, semester):
    """计算单个项目的得分"""
    # 1. 获取所有评分
    scores = get_scores(teacher_id, item_id, semester)
    
    # 2. 排序
    scores.sort()
    
    # 3. 去极值（3个或以上评分）
    if len(scores) >= 3:
        scores = scores[1:-1]  # 去掉首尾
    
    # 4. 计算平均分
    if len(scores) > 0:
        avg_score = sum(scores) / len(scores)
    else:
        avg_score = 0
    
    return avg_score

def calculate_total_score(teacher_id, semester):
    """计算总分"""
    total_score = 0
    
    # 遍历所有考核项目
    for item in get_active_items():
        # 计算项目得分
        item_score = calculate_item_score(
            teacher_id, item.id, semester
        )
        
        # 加权累加
        total_score += item_score * item.weight / 100
    
    return round(total_score, 2)
```

### 2. 排名算法

```python
def calculate_rankings(semester):
    """计算排名"""
    # 1. 获取所有正班主任
    teachers = get_teachers(teacher_type='正班主任')
    
    # 2. 计算每位教师的总分
    results = []
    for teacher in teachers:
        total_score = calculate_total_score(teacher.id, semester)
        results.append({
            'teacher_id': teacher.id,
            'total_score': total_score
        })
    
    # 3. 按总分降序排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # 4. 分配排名
    for rank, result in enumerate(results, 1):
        result['rank'] = rank
        save_result(result, semester)
    
    return results
```

## 安全性设计

### 1. 认证与授权

```python
安全层级:
├─ Flask-Login 会话管理
├─ @login_required 登录验证
├─ @admin_required 管理员验证
└─ 评分权限检查
   └─ check_evaluator_permission()
```

### 2. 数据验证

```python
输入验证:
├─ 评分范围: 0-100
├─ 学期格式: YYYY-YYYY-N
├─ 权重范围: 0-100
└─ SQL注入防护: 参数化查询
```

### 3. 错误处理

```python
异常处理:
├─ try-except 捕获
├─ 日志记录
├─ 友好错误提示
└─ 事务回滚
```

## 性能优化

### 1. 数据库优化

```sql
-- 索引优化
CREATE INDEX idx_scores_teacher ON performance_scores(teacher_id);
CREATE INDEX idx_scores_semester ON performance_scores(semester);
CREATE INDEX idx_results_semester ON performance_results(semester);
```

### 2. 查询优化

```python
优化策略:
├─ 使用JOIN减少查询次数
├─ 批量操作代替循环查询
├─ 结果缓存
└─ 分页加载
```

### 3. 前端优化

```javascript
优化措施:
├─ 按需加载数据
├─ 防抖处理
├─ 本地缓存
└─ 异步加载
```

## 扩展性设计

### 1. 模块化设计

```
系统采用模块化设计，便于扩展:
├─ 独立的Blueprint
├─ 独立的数据表
├─ 独立的前端页面
└─ 松耦合的接口
```

### 2. 配置化设计

```python
可配置项:
├─ 考核项目（数据库配置）
├─ 权重分配（数据库配置）
├─ 评分规则（代码配置）
└─ 学期设置（前端配置）
```

### 3. 未来扩展方向

```
扩展计划:
├─ 导出功能
│  ├─ Excel导出
│  └─ PDF报告
│
├─ 统计分析
│  ├─ 趋势分析
│  ├─ 对比分析
│  └─ 分布分析
│
├─ 通知提醒
│  ├─ 邮件通知
│  └─ 系统消息
│
└─ 移动端
   ├─ 响应式优化
   └─ 移动端APP
```

## 部署架构

```
生产环境部署:
├─ Web服务器: Nginx
├─ 应用服务器: Gunicorn + Flask
├─ 数据库: SQLite (小规模) / PostgreSQL (大规模)
├─ 缓存: Redis (可选)
└─ 监控: 日志系统 + 性能监控
```

## 维护与监控

### 1. 日志系统

```python
日志级别:
├─ INFO: 正常操作
├─ WARNING: 警告信息
├─ ERROR: 错误信息
└─ DEBUG: 调试信息
```

### 2. 备份策略

```bash
备份计划:
├─ 每日自动备份
├─ 重要操作前手动备份
└─ 异地备份存储
```

### 3. 监控指标

```
监控项目:
├─ 系统可用性
├─ 响应时间
├─ 错误率
├─ 数据库性能
└─ 用户活跃度
```

---

**文档版本**: 1.0  
**最后更新**: 2026-01-17  
**维护者**: 系统开发团队
