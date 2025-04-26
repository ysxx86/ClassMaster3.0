/**
 * 班主任管理系统 - 新手引导教程
 * 根据README.md中的班主任操作指南提供分步骤的教学
 */

// 引导步骤配置
const tutorialSteps = [
    {
        title: "欢迎使用班主任管理系统",
        content: "这个简短的教程将帮助您快速了解系统的主要功能。",
        target: "body", // 全局提示，不针对特定元素
        position: "center",
        showSkip: true
    },
    {
        title: "第一步：修改默认密码",
        content: "首次登录系统后，请立即修改默认密码以确保账户安全。点击右上角的个人头像，选择\u201C修改密码\u201D选项。",
        target: ".user-avatar, .dropdown-toggle", // 用户头像区域
        position: "bottom",
        showSkip: true
    },
    {
        title: "第二步：学生管理",
        content: "进入\u201C学生管理\u201D模块，点击\u201C导入学生\u201D按钮。您可以下载模板，填写学生信息后上传，也可以手动添加单个学生。",
        target: ".nav-link[href='#students']", // 学生管理选项卡
        position: "right",
        showSkip: true
    },
    {
        title: "第三步：评语管理",
        content: "访问\u201C评语管理\u201D页面，系统将显示您班级的所有学生。您可以手动编写评语，使用AI海海助手生成评语，或批量导入评语。评语字数限制为260字。",
        target: ".nav-link[href='#comments']", // 评语管理选项卡
        position: "right",
        showSkip: true
    },
    {
        title: "第四步：成绩管理",
        content: "在\u201C成绩管理\u201D页面，您可以为每位学生设置各科目的成绩等级。输入具体分数或选择等级，使用批量编辑功能同时设置多名学生的成绩。",
        target: ".nav-link[href='#grades']", // 成绩管理选项卡
        position: "right",
        showSkip: true
    },
    {
        title: "第五步：德育维度",
        content: "在\u201C德育维度\u201D页面，您可以为学生设置品质、学习、健康、审美、实践和生活六个维度的评价分数。这些数据将用于生成综合素质评价报告。",
        target: ".nav-link[href='#deyu']", // 德育维度选项卡
        position: "right",
        showSkip: true
    },
    {
        title: "第六步：导出报告",
        content: "完成以上步骤后，进入\u201C报告管理\u201D页面。选择需要导出的班级和学期，选择报告模板，添加班主任签名，然后点击\u201C开始导出\u201D按钮生成最终报告。",
        target: ".nav-link[href='#export']", // 报告管理选项卡
        position: "right",
        showSkip: true
    },
    {
        title: "恭喜您完成教程！",
        content: "您已了解系统的基本操作流程。现在您可以开始使用班主任管理系统了！",
        target: "body", // 全局提示
        position: "center",
        showSkip: false,
        isLastStep: true
    }
];

// 检查是否为初次访问
function isFirstVisit() {
    try {
        return localStorage.getItem('tutorialCompleted') === null;
    } catch (e) {
        console.error('访问localStorage失败:', e);
        return false;
    }
}

// 标记教程已完成
function markTutorialCompleted() {
    try {
        localStorage.setItem('tutorialCompleted', 'true');
    } catch (e) {
        console.error('写入localStorage失败:', e);
    }
}

// 重置教程状态
function resetTutorialState() {
    try {
        localStorage.removeItem('tutorialCompleted');
    } catch (e) {
        console.error('删除localStorage项失败:', e);
    }
}

// 显示自定义欢迎对话框
function showWelcomeDialog(callback) {
    // 创建模态背景
    const modalOverlay = document.createElement('div');
    modalOverlay.style.position = 'fixed';
    modalOverlay.style.top = '0';
    modalOverlay.style.left = '0';
    modalOverlay.style.width = '100%';
    modalOverlay.style.height = '100%';
    modalOverlay.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
    modalOverlay.style.zIndex = '10001';
    modalOverlay.style.display = 'flex';
    modalOverlay.style.justifyContent = 'center';
    modalOverlay.style.alignItems = 'center';
    modalOverlay.style.backdropFilter = 'blur(4px)';
    
    // 创建模态框
    const modal = document.createElement('div');
    modal.style.width = '450px';
    modal.style.backgroundColor = '#fff';
    modal.style.borderRadius = '12px';
    modal.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.3)';
    modal.style.overflow = 'hidden';
    modal.style.animation = 'modalFadeIn 0.5s forwards';
    modal.style.opacity = '0';
    modal.style.transform = 'translateY(-20px)';
    
    // 添加动画
    const styleSheet = document.createElement('style');
    styleSheet.textContent = `
        @keyframes modalFadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(styleSheet);
    
    // 创建标题栏
    const modalHeader = document.createElement('div');
    modalHeader.style.background = 'linear-gradient(135deg, #00c6ff, #0072ff)';
    modalHeader.style.color = 'white';
    modalHeader.style.padding = '20px 25px';
    modalHeader.style.fontSize = '22px';
    modalHeader.style.fontWeight = 'bold';
    modalHeader.style.display = 'flex';
    modalHeader.style.justifyContent = 'space-between';
    modalHeader.style.alignItems = 'center';
    
    const logo = document.createElement('div');
    logo.innerHTML = '<i class="bx bx-book-reader" style="font-size: 28px; margin-right: 10px;"></i> 班主任管理系统';
    logo.style.display = 'flex';
    logo.style.alignItems = 'center';
    modalHeader.appendChild(logo);
    
    // 创建内容
    const modalBody = document.createElement('div');
    modalBody.style.padding = '25px';
    modalBody.style.fontSize = '18px';
    modalBody.style.lineHeight = '1.5';
    modalBody.style.color = '#333';
    modalBody.style.textAlign = 'center';
    
    const welcomeIcon = document.createElement('div');
    welcomeIcon.innerHTML = '<i class="bx bx-trophy" style="font-size: 64px; color: #0072ff; margin-bottom: 20px;"></i>';
    welcomeIcon.style.display = 'flex';
    welcomeIcon.style.justifyContent = 'center';
    welcomeIcon.style.alignItems = 'center';
    
    const welcomeText = document.createElement('p');
    welcomeText.textContent = '欢迎使用班主任管理系统！';
    welcomeText.style.fontSize = '20px';
    welcomeText.style.fontWeight = 'bold';
    welcomeText.style.marginBottom = '15px';
    
    const questionText = document.createElement('p');
    questionText.textContent = '您是否需要查看新手教程？';
    questionText.style.fontSize = '18px';
    questionText.style.marginBottom = '25px';
    
    modalBody.appendChild(welcomeIcon);
    modalBody.appendChild(welcomeText);
    modalBody.appendChild(questionText);
    
    // 创建按钮区域
    const modalFooter = document.createElement('div');
    modalFooter.style.display = 'flex';
    modalFooter.style.justifyContent = 'center';
    modalFooter.style.padding = '0 25px 25px 25px';
    modalFooter.style.gap = '15px';
    
    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = '稍后再说';
    cancelBtn.style.padding = '12px 20px';
    cancelBtn.style.borderRadius = '6px';
    cancelBtn.style.border = '1px solid #ddd';
    cancelBtn.style.backgroundColor = '#f5f5f5';
    cancelBtn.style.color = '#666';
    cancelBtn.style.fontSize = '16px';
    cancelBtn.style.cursor = 'pointer';
    cancelBtn.style.transition = 'all 0.2s';
    
    cancelBtn.addEventListener('mouseover', () => {
        cancelBtn.style.backgroundColor = '#ebebeb';
    });
    
    cancelBtn.addEventListener('mouseout', () => {
        cancelBtn.style.backgroundColor = '#f5f5f5';
    });
    
    const confirmBtn = document.createElement('button');
    confirmBtn.textContent = '开始教程';
    confirmBtn.style.padding = '12px 25px';
    confirmBtn.style.borderRadius = '6px';
    confirmBtn.style.border = 'none';
    confirmBtn.style.backgroundColor = '#0072ff';
    confirmBtn.style.color = 'white';
    confirmBtn.style.fontSize = '16px';
    confirmBtn.style.fontWeight = 'bold';
    confirmBtn.style.cursor = 'pointer';
    confirmBtn.style.boxShadow = '0 4px 10px rgba(0, 114, 255, 0.3)';
    confirmBtn.style.transition = 'all 0.2s';
    
    confirmBtn.addEventListener('mouseover', () => {
        confirmBtn.style.backgroundColor = '#005bcc';
        confirmBtn.style.boxShadow = '0 6px 12px rgba(0, 114, 255, 0.4)';
    });
    
    confirmBtn.addEventListener('mouseout', () => {
        confirmBtn.style.backgroundColor = '#0072ff';
        confirmBtn.style.boxShadow = '0 4px 10px rgba(0, 114, 255, 0.3)';
    });
    
    // 添加按钮事件
    cancelBtn.addEventListener('click', () => {
        document.body.removeChild(modalOverlay);
        callback(false);
    });
    
    confirmBtn.addEventListener('click', () => {
        document.body.removeChild(modalOverlay);
        callback(true);
    });
    
    modalFooter.appendChild(cancelBtn);
    modalFooter.appendChild(confirmBtn);
    
    // 组装模态框
    modal.appendChild(modalHeader);
    modal.appendChild(modalBody);
    modal.appendChild(modalFooter);
    modalOverlay.appendChild(modal);
    
    // 添加到页面
    document.body.appendChild(modalOverlay);
    
    // 显示时添加动画
    setTimeout(() => {
        modal.style.opacity = '1';
        modal.style.transform = 'translateY(0)';
    }, 10);
}

// 教程管理类
class TutorialManager {
    constructor(steps) {
        this.steps = steps;
        this.currentStep = 0;
        this.overlay = null;
        this.popupBox = null;
        this.arrow = null;
        this.isRunning = false;
        
        // 不再在构造函数中执行首次访问检查
        // 这个检查会在initTutorial函数中直接执行
    }
    
    // 初始化首次访问检查 - 保留此方法以防其他地方调用
    initFirstVisitCheck() {
        // 确保在主框架中执行，而不是iframe中
        if (window.self === window.top && isFirstVisit()) {
            console.log("检测到首次访问");
            showWelcomeDialog((result) => {
                if (result) {
                    this.start();
                } else {
                    markTutorialCompleted();
                }
            });
        }
    }
    
    // 开始教程
    start() {
        console.log("开始教程");
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.currentStep = 0;
        this.createOverlay();
        this.showStep(this.currentStep);
        
        // 监听ESC键退出教程
        document.addEventListener('keydown', this.handleKeyPress.bind(this));
        
        // 监听窗口大小变化，重新定位弹窗
        window.addEventListener('resize', this.handleResize.bind(this));
        
        // 监听滚动事件，确保弹窗位置正确
        window.addEventListener('scroll', this.handleScroll.bind(this));
    }
    
    // 重启教程
    restart() {
        console.log("重启教程");
        resetTutorialState();
        this.start();
    }
    
    // 创建遮罩层
    createOverlay() {
        console.log("创建遮罩层");
        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .tutorial-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: relative;
                padding-right: 100px; /* 为跳过按钮预留空间 */
            }
            
            .tutorial-header h3 {
                margin: 0;
                padding: 0;
                font-size: 18px;
                flex: 1;
            }
            
            .tutorial-skip-btn {
                position: absolute;
                top: 5px;
                right: 5px;
                background-color: rgba(240, 240, 240, 0.2);
                border: 1px solid rgba(200, 200, 200, 0.3);
                color: #666;
                font-size: 14px;
                cursor: pointer;
                padding: 8px 12px;
                border-radius: 4px;
                transition: all 0.2s ease;
                min-width: 80px;
                text-align: center;
                box-sizing: border-box;
                z-index: 10002; /* 确保按钮位于最上层 */
            }
            
            .tutorial-skip-btn:hover {
                background-color: rgba(0, 0, 0, 0.1);
                color: #333;
            }
            
            .tutorial-skip-btn:active {
                background-color: rgba(0, 0, 0, 0.15);
                transform: scale(0.97);
            }
        `;
        document.head.appendChild(style);
        
        // 创建遮罩层
        this.overlay = document.createElement('div');
        this.overlay.className = 'tutorial-overlay';
        document.body.appendChild(this.overlay);
        
        // 创建弹窗
        this.popupBox = document.createElement('div');
        this.popupBox.className = 'tutorial-popup';
        document.body.appendChild(this.popupBox);
        
        // 创建箭头指示器
        this.arrow = document.createElement('div');
        this.arrow.className = 'tutorial-arrow';
        this.arrow.style.display = 'none';
        document.body.appendChild(this.arrow);
    }
    
    // 显示当前步骤
    showStep(stepIndex) {
        console.log(`显示步骤 ${stepIndex+1}/${this.steps.length}`);
        if (stepIndex >= this.steps.length) {
            this.complete();
            return;
        }
        
        const step = this.steps[stepIndex];
        let targetElement;
        
        try {
            targetElement = document.querySelector(step.target);
        } catch (e) {
            console.error(`无法找到目标元素: ${step.target}`, e);
            targetElement = null;
        }
        
        // 更新弹窗内容
        this.popupBox.innerHTML = `
            <div class="tutorial-header">
                <h3>${step.title}</h3>
                <button class="tutorial-skip-btn"><i class="bx bx-x" style="margin-right: 4px;"></i> 跳过教程</button>
            </div>
            <div class="tutorial-content">
                <p>${step.content}</p>
            </div>
            <div class="tutorial-footer">
                <div class="tutorial-progress">
                    <span>${stepIndex + 1} / ${this.steps.length}</span>
                    <div class="tutorial-progress-dots">
                        ${this.createProgressDots()}
                    </div>
                </div>
                <div class="tutorial-buttons">
                    ${stepIndex > 0 ? '<button class="tutorial-prev-btn">上一步</button>' : ''}
                    <button class="tutorial-next-btn">${step.isLastStep ? '完成' : '下一步'}</button>
                </div>
            </div>
        `;
        
        // 定位弹窗
        this.positionElements(targetElement, step.position);
        
        // 添加按钮事件
        this.addButtonListeners();
        
        // 高亮目标元素
        this.highlightTarget(targetElement);
    }
    
    // 创建进度点
    createProgressDots() {
        let dots = '';
        for (let i = 0; i < this.steps.length; i++) {
            const isActive = i === this.currentStep ? 'active' : '';
            dots += `<div class="tutorial-progress-dot ${isActive}"></div>`;
        }
        return dots;
    }
    
    // 定位弹窗和箭头
    positionElements(targetElement, position) {
        // 确保弹窗不被顶部栏遮挡
        const headerHeight = 60; // 估计页面顶部栏高度
        
        // 如果是居中显示
        if (position === 'center' || !targetElement) {
            this.popupBox.style.position = 'fixed';
            this.popupBox.style.top = '50%';
            this.popupBox.style.left = '50%';
            this.popupBox.style.transform = 'translate(-50%, -50%)';
            
            // 隐藏箭头
            if (this.arrow) {
                this.arrow.style.display = 'none';
            }
            return;
        }
        
        // 获取目标元素位置
        const rect = targetElement.getBoundingClientRect();
        const popupRect = this.popupBox.getBoundingClientRect();
        
        // 箭头位置
        if (this.arrow) {
            this.arrow.style.display = 'block';
        }
        
        // 根据位置设置弹窗和箭头
        switch (position) {
            case 'top':
                // 确保弹窗不超出顶部
                let topPosition = rect.top - popupRect.height - 20;
                if (topPosition < headerHeight) {
                    // 如果顶部空间不够，改用底部显示
                    this.positionElements(targetElement, 'bottom');
                    return;
                }
                
                this.popupBox.style.top = `${topPosition}px`;
                this.popupBox.style.left = `${rect.left + (rect.width / 2) - (popupRect.width / 2)}px`;
                
                // 设置箭头
                if (this.arrow) {
                    this.arrow.style.top = `${rect.top - 15}px`;
                    this.arrow.style.left = `${rect.left + (rect.width / 2) - 20}px`;
                    this.arrow.style.transform = 'rotate(180deg)';
                }
                break;
                
            case 'bottom':
                this.popupBox.style.top = `${rect.bottom + 20}px`;
                this.popupBox.style.left = `${rect.left + (rect.width / 2) - (popupRect.width / 2)}px`;
                
                // 设置箭头
                if (this.arrow) {
                    this.arrow.style.top = `${rect.bottom - 5}px`;
                    this.arrow.style.left = `${rect.left + (rect.width / 2) - 20}px`;
                    this.arrow.style.transform = 'rotate(0deg)';
                }
                break;
                
            case 'left':
                this.popupBox.style.top = `${Math.max(headerHeight, rect.top + (rect.height / 2) - (popupRect.height / 2))}px`;
                this.popupBox.style.left = `${rect.left - popupRect.width - 20}px`;
                
                // 设置箭头
                if (this.arrow) {
                    this.arrow.style.top = `${rect.top + (rect.height / 2) - 20}px`;
                    this.arrow.style.left = `${rect.left - 15}px`;
                    this.arrow.style.transform = 'rotate(90deg)';
                }
                break;
                
            case 'right':
                this.popupBox.style.top = `${Math.max(headerHeight, rect.top + (rect.height / 2) - (popupRect.height / 2))}px`;
                this.popupBox.style.left = `${rect.right + 20}px`;
                
                // 设置箭头
                if (this.arrow) {
                    this.arrow.style.top = `${rect.top + (rect.height / 2) - 20}px`;
                    this.arrow.style.left = `${rect.right - 5}px`;
                    this.arrow.style.transform = 'rotate(-90deg)';
                }
                break;
        }
        
        // 确保弹窗在可视区域内
        this.keepInViewport();
    }
    
    // 确保弹窗在可视区域内
    keepInViewport() {
        const rect = this.popupBox.getBoundingClientRect();
        const headerHeight = 60; // 页面顶部栏高度
        
        if (rect.left < 20) {
            this.popupBox.style.left = '20px';
        }
        
        if (rect.right > window.innerWidth - 20) {
            this.popupBox.style.left = `${window.innerWidth - rect.width - 20}px`;
        }
        
        if (rect.top < headerHeight + 10) {
            this.popupBox.style.top = `${headerHeight + 10}px`;
        }
        
        if (rect.bottom > window.innerHeight - 20) {
            this.popupBox.style.top = `${window.innerHeight - rect.height - 20}px`;
        }
    }
    
    // 高亮目标元素
    highlightTarget(targetElement) {
        // 重置遮罩层
        this.overlay.innerHTML = '';
        
        if (!targetElement || this.steps[this.currentStep].position === 'center') {
            // 全屏半透明遮罩
            this.overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
            return;
        }
        
        // 创建目标元素的剪切区域，实现高亮效果
        const rect = targetElement.getBoundingClientRect();
        
        // 使用SVG创建镂空效果
        this.overlay.style.backgroundColor = 'transparent';
        this.overlay.innerHTML = `
            <svg width="100%" height="100%" class="tutorial-svg-mask">
                <defs>
                    <mask id="tutorial-mask">
                        <rect width="100%" height="100%" fill="white"></rect>
                        <rect x="${rect.left}" y="${rect.top}" width="${rect.width}" height="${rect.height}" fill="black"></rect>
                    </mask>
                </defs>
                <rect width="100%" height="100%" fill="rgba(0, 0, 0, 0.5)" mask="url(#tutorial-mask)"></rect>
                <rect x="${rect.left - 2}" y="${rect.top - 2}" width="${rect.width + 4}" height="${rect.height + 4}" 
                      fill="none" stroke="#4dabf7" stroke-width="2" rx="4"></rect>
            </svg>
        `;
        
        // 添加点击透明区域跳转到下一步的功能
        this.overlay.addEventListener('click', (e) => {
            const overlayRect = this.overlay.getBoundingClientRect();
            const clickX = e.clientX - overlayRect.left;
            const clickY = e.clientY - overlayRect.top;
            
            // 如果点击在高亮区域外
            if (clickX < rect.left || clickX > rect.right || 
                clickY < rect.top || clickY > rect.bottom) {
                // 如果不是最后一步，进入下一步
                if (!this.steps[this.currentStep].isLastStep) {
                    this.currentStep++;
                    this.showStep(this.currentStep);
                }
            }
        });
    }
    
    // 添加按钮事件监听
    addButtonListeners() {
        // 下一步按钮
        const nextBtn = this.popupBox.querySelector('.tutorial-next-btn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (this.steps[this.currentStep].isLastStep) {
                    this.complete();
                } else {
                    this.currentStep++;
                    this.showStep(this.currentStep);
                }
            });
        }
        
        // 上一步按钮
        const prevBtn = this.popupBox.querySelector('.tutorial-prev-btn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                this.currentStep--;
                this.showStep(this.currentStep);
            });
        }
        
        // 跳过教程按钮
        const skipBtn = this.popupBox.querySelector('.tutorial-skip-btn');
        if (skipBtn) {
            // 使用mousedown而不是click事件，以提高响应速度
            skipBtn.addEventListener('mousedown', (e) => {
                e.preventDefault(); // 防止可能的文本选择
                e.stopPropagation(); // 阻止事件冒泡
                
                // 使用普通的confirm对话框
                if (confirm('确定要跳过教程吗？您可以稍后在帮助菜单中重新打开。')) {
                    this.complete();
                }
            });
            
            // 确保触摸设备也能正常工作
            skipBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                if (confirm('确定要跳过教程吗？您可以稍后在帮助菜单中重新打开。')) {
                    this.complete();
                }
            }, { passive: false });
        }
    }
    
    // 处理键盘事件
    handleKeyPress(e) {
        if (e.key === 'Escape') {
            this.complete();
        } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
            if (this.steps[this.currentStep].isLastStep) {
                this.complete();
            } else {
                this.currentStep++;
                this.showStep(this.currentStep);
            }
        } else if (e.key === 'ArrowLeft' && this.currentStep > 0) {
            this.currentStep--;
            this.showStep(this.currentStep);
        }
    }
    
    // 处理窗口大小变化
    handleResize() {
        if (!this.isRunning) return;
        
        const step = this.steps[this.currentStep];
        const targetElement = document.querySelector(step.target);
        
        // 重新定位弹窗和箭头
        this.positionElements(targetElement, step.position);
        
        // 重新高亮目标元素
        this.highlightTarget(targetElement);
    }
    
    // 处理滚动事件
    handleScroll() {
        if (!this.isRunning) return;
        
        // 延迟处理，避免频繁触发
        clearTimeout(this.scrollTimeout);
        this.scrollTimeout = setTimeout(() => {
            const step = this.steps[this.currentStep];
            try {
                const targetElement = document.querySelector(step.target);
                
                // 重新定位弹窗和箭头
                this.positionElements(targetElement, step.position);
                
                // 重新高亮目标元素
                this.highlightTarget(targetElement);
            } catch (e) {
                console.error('处理滚动事件时出错:', e);
            }
        }, 100);
    }
    
    // 完成教程
    complete() {
        console.log("完成教程");
        // 移除事件监听
        document.removeEventListener('keydown', this.handleKeyPress.bind(this));
        window.removeEventListener('resize', this.handleResize.bind(this));
        window.removeEventListener('scroll', this.handleScroll.bind(this));
        
        // 移除遮罩、弹窗和箭头
        if (this.overlay) {
            document.body.removeChild(this.overlay);
            this.overlay = null;
        }
        
        if (this.popupBox) {
            document.body.removeChild(this.popupBox);
            this.popupBox = null;
        }
        
        if (this.arrow) {
            document.body.removeChild(this.arrow);
            this.arrow = null;
        }
        
        // 标记教程已完成
        markTutorialCompleted();
        
        this.isRunning = false;
        
        // 显示完成提示
        this.showNotification('教程已完成，您可以开始使用系统了！', 'success');
    }
    
    // 显示通知
    showNotification(message, type = 'success') {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `tutorial-notification ${type}`;
        notification.innerHTML = `<p>${message}</p>`;
        
        // 添加到文档
        document.body.appendChild(notification);
        
        // 显示通知
        setTimeout(() => notification.style.opacity = '1', 10);
        
        // 自动关闭
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// 等待DOM准备就绪后运行
function initTutorial() {
    console.log("初始化教程系统");
    
    // 创建全局教程管理器实例
    if (!window.tutorialManager) {
        window.tutorialManager = new TutorialManager(tutorialSteps);
        
        // 立即检查是否是首次访问
        if (isFirstVisit() && window.self === window.top) {
            console.log("立即检查首次访问状态");
            showWelcomeDialog((result) => {
                if (result) {
                    window.tutorialManager.start();
                } else {
                    markTutorialCompleted();
                }
            });
        }
        
        // 添加重启教程的方法到全局
        window.restartTutorial = function() {
            console.log("调用重启教程");
            if (window.tutorialManager) {
                window.tutorialManager.restart();
            } else {
                console.error("tutorialManager未初始化");
                alert("教程系统未正确加载，请刷新页面重试");
            }
        };
        
        // 确保按钮绑定了正确的事件
        const startTutorialBtn = document.getElementById('startTutorialBtn');
        if (startTutorialBtn) {
            console.log("发现教程按钮，添加事件监听器");
            startTutorialBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log("教程按钮被点击");
                window.restartTutorial();
            });
        } else {
            console.warn("未找到ID为startTutorialBtn的按钮");
            // 延迟尝试再次查找按钮（等待可能的动态加载）
            setTimeout(() => {
                const retryBtn = document.getElementById('startTutorialBtn');
                if (retryBtn) {
                    console.log("延迟后找到教程按钮，添加事件监听器");
                    retryBtn.addEventListener('click', function(e) {
                        e.preventDefault();
                        window.restartTutorial();
                    });
                }
            }, 500); // 缩短延迟时间
        }
    }
}

// 同时使用DOMContentLoaded和load事件，确保在各种情况下都能初始化
if (document.readyState === 'loading') {
    // 如果DOM正在加载，添加DOMContentLoaded事件监听器
    document.addEventListener('DOMContentLoaded', function() {
        console.log("DOMContentLoaded触发，立即初始化教程系统");
        initTutorial();
    });
} else {
    // 如果DOM已经加载完成，立即初始化
    console.log("DOM已经加载完成，立即初始化教程系统");
    initTutorial();
}

// 作为备份，也添加window.load事件监听
window.addEventListener('load', function() {
    if (!window.tutorialManager) {
        console.log("在window.load中初始化教程系统（备份方案）");
        initTutorial();
    }
}); 