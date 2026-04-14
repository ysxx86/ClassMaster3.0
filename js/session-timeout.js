/**
 * 会话超时控制
 * 如果用户5分钟内没有任何操作，自动退出登录
 */

// 超时时间设置（毫秒）
const SESSION_TIMEOUT = 5 * 60 * 1000; // 5分钟

// 存储定时器ID
let sessionTimeoutId = null;

// 重置超时计时器
function resetSessionTimer() {
    // 清除现有的计时器
    if (sessionTimeoutId) {
        clearTimeout(sessionTimeoutId);
    }
    
    // 设置新的计时器
    sessionTimeoutId = setTimeout(logoutDueToInactivity, SESSION_TIMEOUT);
}

// 超时后执行的登出操作
function logoutDueToInactivity() {
    console.log("会话超时，正在登出...");
    
    // 显示提示消息（如果可能）
    if (typeof showNotification === 'function') {
        showNotification("由于长时间未操作，系统将自动退出", "warning");
    } else {
        alert("由于长时间未操作，系统将自动退出");
    }
    
    // 延迟一秒后执行登出，给用户看到提示的时间
    setTimeout(() => {
        // 调用登出API
        fetch('/api/logout', {
            method: 'POST',
            credentials: 'same-origin'
        })
        .then(response => {
            // 重定向到登录页面，添加timeout参数
            window.location.href = '/login?timeout=true';
        })
        .catch(error => {
            console.error('登出失败:', error);
            // 失败时也重定向到登录页面
            window.location.href = '/login?timeout=true';
        });
    }, 1000);
}

// 监听用户活动事件
function setupActivityListeners() {
    // 鼠标移动
    document.addEventListener('mousemove', resetSessionTimer);
    // 鼠标点击
    document.addEventListener('click', resetSessionTimer);
    // 键盘按键
    document.addEventListener('keypress', resetSessionTimer);
    // 触摸事件（移动设备）
    document.addEventListener('touchstart', resetSessionTimer);
    // 滚动事件
    document.addEventListener('scroll', resetSessionTimer);
}

// 初始化会话超时功能
function initSessionTimeout() {
    console.log("初始化会话超时功能...");
    setupActivityListeners();
    resetSessionTimer();
}

// 当DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', initSessionTimeout);

// 为了便于调试，暴露一些函数
window.sessionTimeoutControl = {
    reset: resetSessionTimer,
    logout: logoutDueToInactivity,
    init: initSessionTimeout
}; 