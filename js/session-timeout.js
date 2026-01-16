/**
 * 会话超时控制
 * 如果用户30分钟内没有任何操作，自动退出登录
 */

// 会话超时监控
(function() {
    // 超时时间设置为30分钟
    const timeoutMinutes = 30; 
    const warningMinutes = 1; // 提前1分钟警告
    
    let timeoutTimer;
    let warningTimer;
    let warningShown = false;
    
    // 重置定时器
    function resetTimers() {
        // 清除现有定时器
        clearTimeout(timeoutTimer);
        clearTimeout(warningTimer);
        warningShown = false;
        
        // 设置警告定时器
        const warningTimeMs = (timeoutMinutes - warningMinutes) * 60 * 1000;
        warningTimer = setTimeout(showWarning, warningTimeMs);
        
        // 设置超时定时器
        const timeoutTimeMs = timeoutMinutes * 60 * 1000;
        timeoutTimer = setTimeout(handleTimeout, timeoutTimeMs);
    }
    
    // 显示警告
    function showWarning() {
        if (warningShown) return;
        warningShown = true;
        
        // 创建警告模态框
        const warningModal = document.createElement('div');
        warningModal.className = 'session-timeout-warning';
        warningModal.innerHTML = `
            <div class="warning-content">
                <h3>会话即将过期</h3>
                <p>您的会话将在 <span id="countdown">30</span> 秒后过期。</p>
                <div class="warning-actions">
                    <button id="extend-session" class="btn-extend">继续操作</button>
                    <button id="logout-now" class="btn-logout">立即退出</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(warningModal);
        
        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .session-timeout-warning {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.7);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }
            .warning-content {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                max-width: 400px;
                width: 90%;
                text-align: center;
            }
            .warning-actions {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-top: 20px;
            }
            .btn-extend, .btn-logout {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .btn-extend {
                background: #2196F3;
                color: white;
            }
            .btn-logout {
                background: #f3f3f3;
                color: #333;
            }
        `;
        document.head.appendChild(style);
        
        // 添加事件监听
        document.getElementById('extend-session').addEventListener('click', function() {
            document.body.removeChild(warningModal);
            resetTimers();
            // 向服务器发送活动信号
            fetch('/api/current-user', { credentials: 'same-origin' })
              .catch(err => console.error('保持会话时出错:', err));
        });
        
        document.getElementById('logout-now').addEventListener('click', function() {
            logout();
        });
        
        // 倒计时
        let secondsLeft = Math.floor(warningMinutes * 60);
        const countdownEl = document.getElementById('countdown');
        const countdownInterval = setInterval(function() {
            secondsLeft--;
            countdownEl.textContent = secondsLeft;
            
            if (secondsLeft <= 0) {
                clearInterval(countdownInterval);
                handleTimeout();
            }
        }, 1000);
    }
    
    // 处理超时
    function handleTimeout() {
        // 向服务器发送登出请求，然后重定向到登录页
        logout();
    }
    
    // 登出函数
    function logout() {
        fetch('/api/logout', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(res => {
            window.location.href = '/login?timeout=true';
        })
        .catch(err => {
            console.error('登出时出错:', err);
            // 即使请求失败，也重定向到登录页
            window.location.href = '/login?timeout=true';
        });
    }
    
    // 用户活动监听
    const resetEvents = ['mousedown', 'keypress', 'scroll', 'touchstart'];
    resetEvents.forEach(event => {
        document.addEventListener(event, resetTimers, false);
    });
    
    // 初始启动定时器
    document.addEventListener('DOMContentLoaded', resetTimers);
    
    // 防止页面刷新或关闭时登出
    window.addEventListener('beforeunload', function(e) {
        clearTimeout(timeoutTimer);
        clearTimeout(warningTimer);
    });
    
    // 暴露几个关键函数到全局作用域，便于调试
    window.sessionTimeoutControl = {
        reset: resetTimers,
        logout: logout,
        handleTimeout: handleTimeout
    };
})(); 