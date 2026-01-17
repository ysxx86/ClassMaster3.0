/**
 * 性能优化工具
 * 提供缓存、防抖、节流等性能优化功能
 */

(function() {
    'use strict';
    
    // API缓存管理器
    class APICache {
        constructor() {
            this.cache = new Map();
            this.cacheTimeout = 30000; // 30秒缓存
        }
        
        /**
         * 获取缓存
         */
        get(key) {
            const cached = this.cache.get(key);
            if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
                console.log(`[缓存] 命中缓存: ${key}`);
                return cached.data;
            }
            return null;
        }
        
        /**
         * 设置缓存
         */
        set(key, data) {
            this.cache.set(key, {
                data: data,
                timestamp: Date.now()
            });
            console.log(`[缓存] 设置缓存: ${key}`);
        }
        
        /**
         * 清除缓存
         */
        clear(pattern) {
            if (pattern) {
                // 清除匹配的缓存
                for (const key of this.cache.keys()) {
                    if (key.includes(pattern)) {
                        this.cache.delete(key);
                        console.log(`[缓存] 清除缓存: ${key}`);
                    }
                }
            } else {
                // 清除所有缓存
                this.cache.clear();
                console.log('[缓存] 清除所有缓存');
            }
        }
    }
    
    // 创建全局缓存实例
    const apiCache = new APICache();
    
    /**
     * 优化的fetch函数 - 带缓存
     */
    async function cachedFetch(url, options = {}) {
        // 只缓存GET请求
        if (!options.method || options.method === 'GET') {
            const cacheKey = url;
            const cached = apiCache.get(cacheKey);
            
            if (cached) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(cached),
                    fromCache: true
                });
            }
            
            // 发起请求
            const response = await fetch(url, options);
            const data = await response.json();
            
            // 缓存成功的响应
            if (response.ok && data.status === 'ok') {
                apiCache.set(cacheKey, data);
            }
            
            return {
                ok: response.ok,
                json: () => Promise.resolve(data),
                fromCache: false
            };
        }
        
        // 非GET请求不缓存
        return fetch(url, options);
    }
    
    /**
     * 防抖函数
     */
    function debounce(func, wait = 300) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * 节流函数
     */
    function throttle(func, limit = 300) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    /**
     * 批量DOM操作优化
     */
    function batchDOMUpdate(callback) {
        requestAnimationFrame(() => {
            callback();
        });
    }
    
    /**
     * 虚拟滚动 - 只渲染可见区域的元素
     */
    class VirtualScroller {
        constructor(container, items, renderItem, itemHeight = 50) {
            this.container = container;
            this.items = items;
            this.renderItem = renderItem;
            this.itemHeight = itemHeight;
            this.visibleCount = Math.ceil(container.clientHeight / itemHeight) + 2;
            this.scrollTop = 0;
            
            this.init();
        }
        
        init() {
            // 创建容器
            this.viewport = document.createElement('div');
            this.viewport.style.height = `${this.items.length * this.itemHeight}px`;
            this.viewport.style.position = 'relative';
            
            this.content = document.createElement('div');
            this.content.style.position = 'absolute';
            this.content.style.top = '0';
            this.content.style.left = '0';
            this.content.style.right = '0';
            
            this.viewport.appendChild(this.content);
            this.container.appendChild(this.viewport);
            
            // 监听滚动
            this.container.addEventListener('scroll', throttle(() => {
                this.scrollTop = this.container.scrollTop;
                this.render();
            }, 50));
            
            // 初始渲染
            this.render();
        }
        
        render() {
            const startIndex = Math.floor(this.scrollTop / this.itemHeight);
            const endIndex = Math.min(startIndex + this.visibleCount, this.items.length);
            
            // 清空内容
            this.content.innerHTML = '';
            this.content.style.transform = `translateY(${startIndex * this.itemHeight}px)`;
            
            // 渲染可见项
            for (let i = startIndex; i < endIndex; i++) {
                const item = this.renderItem(this.items[i], i);
                this.content.appendChild(item);
            }
        }
        
        update(items) {
            this.items = items;
            this.viewport.style.height = `${this.items.length * this.itemHeight}px`;
            this.render();
        }
    }
    
    /**
     * 图片懒加载
     */
    function lazyLoadImages() {
        const images = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    }
    
    /**
     * 性能监控
     */
    class PerformanceMonitor {
        constructor() {
            this.marks = new Map();
        }
        
        start(label) {
            this.marks.set(label, performance.now());
        }
        
        end(label) {
            const startTime = this.marks.get(label);
            if (startTime) {
                const duration = performance.now() - startTime;
                console.log(`[性能] ${label}: ${duration.toFixed(2)}ms`);
                this.marks.delete(label);
                return duration;
            }
            return 0;
        }
    }
    
    // 导出到全局
    window.PerformanceOptimizer = {
        apiCache: apiCache,
        cachedFetch: cachedFetch,
        debounce: debounce,
        throttle: throttle,
        batchDOMUpdate: batchDOMUpdate,
        VirtualScroller: VirtualScroller,
        lazyLoadImages: lazyLoadImages,
        PerformanceMonitor: PerformanceMonitor
    };
    
    console.log('[性能优化] 性能优化工具已就绪');
})();
