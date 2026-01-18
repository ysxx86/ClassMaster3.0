# 系统更新通知功能使用指南

## 功能说明

系统更新通知功能会在用户首次登录或版本更新后自动弹出，展示最新的系统更新内容。用户关闭后，可以通过右上角的更新图标随时查看。

## 集成方法

### 1. 在页面中引入CSS和JS文件

在所有需要显示更新通知的页面的 `<head>` 标签中添加：

```html
<!-- 更新通知样式 -->
<link rel="stylesheet" href="/css/update-notification.css">
```

在页面底部 `</body>` 标签前添加：

```html
<!-- 更新通知脚本 -->
<script src="/js/update-notification.js"></script>
```

### 2. 完整示例

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>首页 - 德育AI智能系统</title>
    
    <!-- Bootstrap CSS -->
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- 图标库 -->
    <link href="/css/boxicons-local.css" rel="stylesheet">
    
    <!-- 更新通知样式 -->
    <link rel="stylesheet" href="/css/update-notification.css">
    
    <!-- 其他样式 -->
    <link rel="stylesheet" href="/css/home.css">
</head>
<body>
    <!-- 页面内容 -->
    <div class="content">
        <h1>欢迎使用德育AI智能系统</h1>
        <!-- 其他内容 -->
    </div>

    <!-- Bootstrap JS -->
    <script src="/js/libs/bootstrap.bundle.min.js"></script>
    
    <!-- 更新通知脚本 -->
    <script src="/js/update-notification.js"></script>
    
    <!-- 其他脚本 -->
    <script src="/js/home.js"></script>
</body>
</html>
```

## 功能特性

### 1. 自动弹出
- 用户首次访问系统时自动弹出
- 系统版本更新后自动弹出
- 使用 localStorage 记录用户已查看的版本

### 2. 右上角图标
- 固定在页面右上角
- 渐变紫色背景，带有铃铛图标
- 红色小圆点提示有新更新
- 点击可随时查看更新内容

### 3. 更新内容展示
- 版本号和发布日期
- 分类展示更新内容：
  - 👥 教师权限管理
  - 🎯 权限精确控制
  - ⚡ 性能大幅提升
  - 📊 数据管理增强
  - 🎨 用户体验优化
  - 🐛 问题修复
- 每个分类有独特的颜色和图标
- 更新项目以列表形式展示，带有勾选标记
- 底部有更新总结

### 4. 交互效果
- 平滑的动画效果
- 悬停时的视觉反馈
- 响应式设计，移动端友好
- 美化的滚动条

## 自定义更新内容

如果需要更新系统更新日志，编辑 `js/update-notification.js` 文件中的以下内容：

### 1. 修改版本号

```javascript
const CURRENT_VERSION = '2.1.0'; // 修改为新版本号
```

### 2. 修改更新日志

```javascript
const UPDATE_LOGS = {
    version: '2.1.0',  // 版本号
    date: '2026年1月18日',  // 发布日期
    title: '系统重大升级 - 权限管理与性能优化',  // 标题
    categories: [
        {
            name: '👥 教师权限管理',  // 分类名称
            icon: 'bx-user-check',  // 图标类名
            color: '#0d6efd',  // 分类颜色
            items: [
                '更新项目1',
                '更新项目2',
                // 添加更多项目...
            ]
        },
        // 添加更多分类...
    ],
    summary: '本次更新的总结...'  // 更新总结
};
```

## 注意事项

1. **版本号管理**：每次发布新版本时，记得更新 `CURRENT_VERSION` 常量
2. **内容更新**：更新日志内容应该简洁明了，突出重点
3. **图标选择**：使用 Boxicons 图标库中的图标类名
4. **颜色搭配**：建议使用 Bootstrap 的颜色体系
5. **测试**：更新后建议清除浏览器 localStorage 测试首次弹出效果

## 清除已查看记录（用于测试）

在浏览器控制台执行：

```javascript
localStorage.removeItem('system_last_seen_version');
```

然后刷新页面，更新通知会再次自动弹出。

## 当前版本更新内容（v2.1.0）

本次更新包含以下主要内容：

1. **教师权限管理**：全新的角色、班级、学科分配系统
2. **权限精确控制**：精确到"班级+学科"级别的权限管理
3. **性能优化**：页面加载速度提升80%
4. **数据管理**：新增teaching_assignments表，优化数据结构
5. **用户体验**：拖拽式操作，实时反馈，响应式设计
6. **问题修复**：修复多个已知问题

详细内容请查看更新通知弹窗。
