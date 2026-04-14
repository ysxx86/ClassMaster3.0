/**
 * 系统更新通知组件
 * 用于显示系统更新内容，首次登录自动弹出，之后可通过右上角图标查看
 */

// 当前版本号
const CURRENT_VERSION = '2.1.0';
const VERSION_KEY = 'system_last_seen_version';

// 更新日志内容
const UPDATE_LOGS = {
    version: '2.1.0',
    date: '2026年1月18日',
    title: '系统重大升级 - 权限管理与性能优化',
    categories: [
        {
            name: '👥 教师权限管理',
            icon: 'bx-user-check',
            color: '#0d6efd',
            items: [
                '新增教师角色分配功能，支持拖拽式快速分配角色（正班主任、副班主任、科任老师、行政、校级领导）',
                '新增班级分配功能，支持拖拽方式为教师分配班级',
                '新增学科班级分配功能，支持多选班级批量分配',
                '新增"全部分配"视图，一目了然查看所有教师的角色、班级和学科分配情况',
                '正副班主任的任教学科自动关联到其班级，无需手动配置',
                '科任老师支持跨班级、跨学科任教，权限精确到"班级+学科"级别'
            ]
        },
        {
            name: '🎯 权限精确控制',
            icon: 'bx-lock-alt',
            color: '#198754',
            items: [
                '成绩管理权限优化：正班主任可编辑本班所有学科，科任老师只能编辑任教的"班级+学科"',
                '修复权限匹配问题：科任老师不能跨班级编辑同名学科',
                '评语管理权限优化：教师只能查看和编辑自己权限范围内的学生',
                '新增权限检查器（permission_checker），统一管理所有权限逻辑'
            ]
        },
        {
            name: '⚡ 性能大幅提升',
            icon: 'bx-rocket',
            color: '#dc3545',
            items: [
                '评语管理页面加载速度提升80%，从5秒降至1秒以内',
                '成绩管理页面优化，支持大班级（50+学生）流畅操作',
                '数据库查询优化，添加索引和外键约束',
                '前端按需加载，减少首屏加载时间',
                '修复CDN阻塞问题，资源加载更快速'
            ]
        },
        {
            name: '📊 数据管理增强',
            icon: 'bx-data',
            color: '#0dcaf0',
            items: [
                '新增teaching_assignments表，记录教师的学科班级分配',
                '优化teacher_subjects表，管理教师任教学科',
                '数据库结构优化，支持更复杂的权限场景',
                '修复班级显示问题，空班级也能正常显示提示信息'
            ]
        },
        {
            name: '🎨 用户体验优化',
            icon: 'bx-palette',
            color: '#ffc107',
            items: [
                '教师分配页面全新设计，支持拖拽操作，更直观易用',
                '新增实时Toast通知，操作反馈更及时',
                '优化表格显示，支持筛选和搜索功能',
                '添加详细的操作说明和提示信息',
                '界面响应式优化，移动端体验更好'
            ]
        },
        {
            name: '🐛 问题修复',
            icon: 'bx-bug',
            color: '#6c757d',
            items: [
                '修复评语管理空白页面问题',
                '修复成绩分析500错误',
                '修复角色字段显示问题',
                '修复科任老师多班级显示不全的问题',
                '修复班级学科权限匹配不精确的问题',
                '修复当前分配列表显示为空的问题'
            ]
        }
    ],
    summary: '本次更新重点优化了教师权限管理体系，新增了灵活的角色、班级和学科分配功能。同时大幅提升了系统性能，修复了多个已知问题。系统运行更流畅，操作更便捷！'
};

// 检查是否需要显示更新通知
function checkAndShowUpdateNotification() {
    const lastSeenVersion = localStorage.getItem(VERSION_KEY);
    
    // 如果是首次访问或版本更新，自动显示
    if (!lastSeenVersion || lastSeenVersion !== CURRENT_VERSION) {
        setTimeout(() => {
            showUpdateModal();
            // 标记为已查看
            localStorage.setItem(VERSION_KEY, CURRENT_VERSION);
        }, 1000); // 延迟1秒显示，让页面先加载完成
    }
}

// 显示更新模态框
function showUpdateModal() {
    const modal = new bootstrap.Modal(document.getElementById('updateNotificationModal'));
    modal.show();
}

// 生成更新日志HTML
function generateUpdateLogHTML() {
    const logs = UPDATE_LOGS;
    
    let html = `
        <div class="update-header">
            <div class="update-badge">
                <i class='bx bx-rocket'></i>
                <span>v${logs.version}</span>
            </div>
            <h3 class="update-title">${logs.title}</h3>
            <p class="update-date">
                <i class='bx bx-calendar'></i> ${logs.date}
            </p>
        </div>
    `;
    
    // 生成各个分类
    logs.categories.forEach(category => {
        html += `
            <div class="update-category">
                <div class="category-header" style="border-left-color: ${category.color};">
                    <i class='bx ${category.icon}' style="color: ${category.color};"></i>
                    <h4>${category.name}</h4>
                </div>
                <ul class="category-items">
        `;
        
        category.items.forEach(item => {
            html += `<li>${item}</li>`;
        });
        
        html += `
                </ul>
            </div>
        `;
    });
    
    // 添加总结
    html += `
        <div class="update-summary">
            <i class='bx bx-info-circle'></i>
            <p>${logs.summary}</p>
        </div>
    `;
    
    return html;
}

// 初始化更新通知组件
function initUpdateNotification() {
    // 创建模态框HTML
    const modalHTML = `
        <div class="modal fade" id="updateNotificationModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header border-0">
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="关闭"></button>
                    </div>
                    <div class="modal-body">
                        <div id="updateLogContent">
                            ${generateUpdateLogHTML()}
                        </div>
                    </div>
                    <div class="modal-footer border-0">
                        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                            <i class='bx bx-check'></i> 知道了
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 创建右上角更新图标
    const updateIconHTML = `
        <div class="update-icon-container" id="updateIconContainer">
            <button class="update-icon-btn" onclick="showUpdateModal()" title="查看最新更新">
                <i class='bx bx-bell'></i>
                <span class="update-badge-dot"></span>
            </button>
        </div>
    `;
    
    // 添加到页面
    if (!document.getElementById('updateNotificationModal')) {
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
    
    // 添加更新图标到右上角（如果不存在）
    if (!document.getElementById('updateIconContainer')) {
        // 查找合适的位置插入（通常是导航栏或页面右上角）
        const navbar = document.querySelector('.navbar') || document.querySelector('header') || document.body;
        navbar.insertAdjacentHTML('beforeend', updateIconHTML);
    }
    
    // 检查并显示更新通知
    checkAndShowUpdateNotification();
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUpdateNotification);
} else {
    initUpdateNotification();
}
