/**
 * 实时数据同步系统
 * 用于在不刷新页面的情况下,实时更新所有页面的数据
 */

(function() {
    'use strict';
    
    // 数据变更事件类型
    const EventTypes = {
        STUDENT_ADDED: 'student_added',
        STUDENT_UPDATED: 'student_updated',
        STUDENT_DELETED: 'student_deleted',
        GRADE_UPDATED: 'grade_updated',
        COMMENT_UPDATED: 'comment_updated',
        DEYU_UPDATED: 'deyu_updated',
        USER_UPDATED: 'user_updated',
        CLASS_UPDATED: 'class_updated',
        SUBJECT_UPDATED: 'subject_updated'
    };
    
    // 实时同步管理器
    class RealtimeSyncManager {
        constructor() {
            this.listeners = {};
            this.lastUpdateTime = Date.now();
            this.checkInterval = 2000; // 每2秒检查一次
            this.isChecking = false;
            
            // 初始化
            this.init();
        }
        
        init() {
            console.log('[实时同步] 初始化实时同步系统');
            
            // 使用localStorage作为跨页面通信机制
            window.addEventListener('storage', (e) => {
                if (e.key && e.key.startsWith('data_change_')) {
                    const eventType = e.key.replace('data_change_', '');
                    const eventData = e.newValue ? JSON.parse(e.newValue) : null;
                    this.handleDataChange(eventType, eventData);
                }
            });
            
            // 启动定期检查
            this.startPeriodicCheck();
        }
        
        /**
         * 触发数据变更事件
         */
        triggerDataChange(eventType, data = {}) {
            console.log(`[实时同步] 触发数据变更: ${eventType}`, data);
            
            const eventData = {
                type: eventType,
                data: data,
                timestamp: Date.now()
            };
            
            // 存储到localStorage,触发storage事件
            localStorage.setItem(`data_change_${eventType}`, JSON.stringify(eventData));
            
            // 立即在当前页面处理
            this.handleDataChange(eventType, eventData);
            
            // 清理localStorage(避免累积)
            setTimeout(() => {
                localStorage.removeItem(`data_change_${eventType}`);
            }, 100);
        }
        
        /**
         * 处理数据变更
         */
        handleDataChange(eventType, eventData) {
            console.log(`[实时同步] 处理数据变更: ${eventType}`, eventData);
            
            // 更新最后更新时间
            this.lastUpdateTime = Date.now();
            
            // 通知所有监听器
            if (this.listeners[eventType]) {
                this.listeners[eventType].forEach(callback => {
                    try {
                        callback(eventData);
                    } catch (error) {
                        console.error(`[实时同步] 监听器执行出错:`, error);
                    }
                });
            }
            
            // 通知所有iframe
            this.notifyAllIframes(eventType, eventData);
        }
        
        /**
         * 注册监听器
         */
        on(eventType, callback) {
            if (!this.listeners[eventType]) {
                this.listeners[eventType] = [];
            }
            this.listeners[eventType].push(callback);
            console.log(`[实时同步] 注册监听器: ${eventType}`);
        }
        
        /**
         * 移除监听器
         */
        off(eventType, callback) {
            if (this.listeners[eventType]) {
                const index = this.listeners[eventType].indexOf(callback);
                if (index > -1) {
                    this.listeners[eventType].splice(index, 1);
                }
            }
        }
        
        /**
         * 通知所有iframe
         */
        notifyAllIframes(eventType, eventData) {
            const iframes = document.querySelectorAll('.content-iframe');
            iframes.forEach(iframe => {
                try {
                    if (iframe.contentWindow && iframe.dataset.loaded === 'true') {
                        iframe.contentWindow.postMessage({
                            type: 'data_change',
                            eventType: eventType,
                            eventData: eventData
                        }, '*');
                    }
                } catch (error) {
                    // 跨域iframe无法访问,忽略错误
                }
            });
        }
        
        /**
         * 启动定期检查
         * 已禁用 - 每2秒轮询严重影响性能
         */
        startPeriodicCheck() {
            // 禁用定期检查以提升性能
            console.log('[实时同步] 定期检查已禁用以提升性能');
            // setInterval(() => {
            //     if (!this.isChecking) {
            //         this.checkForUpdates();
            //     }
            // }, this.checkInterval);
        }
        
        /**
         * 检查更新
         */
        async checkForUpdates() {
            this.isChecking = true;
            
            try {
                // 检查是否有新的数据变更
                const response = await fetch(`/api/check-updates?since=${this.lastUpdateTime}`);
                const data = await response.json();
                
                if (data.status === 'ok' && data.updates && data.updates.length > 0) {
                    console.log(`[实时同步] 检测到 ${data.updates.length} 个更新`);
                    
                    // 处理每个更新
                    data.updates.forEach(update => {
                        this.handleDataChange(update.type, update);
                    });
                }
            } catch (error) {
                // 静默失败,不影响用户体验
                console.debug('[实时同步] 检查更新失败:', error.message);
            } finally {
                this.isChecking = false;
            }
        }
    }
    
    // 创建全局实例
    window.RealtimeSync = new RealtimeSyncManager();
    window.RealtimeSyncEventTypes = EventTypes;
    
    console.log('[实时同步] 实时同步系统已就绪');
})();
