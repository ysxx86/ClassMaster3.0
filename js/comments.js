// @charset UTF-8
// 评语管理模块

// 控制是否使用服务器API（而不是本地存储）
const USE_SERVER_API = true; // 设置为true使用服务器API，false使用本地存储

// 全局变量存储评语模板
let commentTemplates = {
    study: [],
    physical: [],
    behavior: []
};
let currentStudentId = null;
let lastDataCheckTimestamp = Date.now();  // 添加最后数据检查时间戳

// 为其他页面提供的刷新方法
window.refreshCommentList = function() {
    console.log('手动触发评语列表刷新...');
    initCommentList();
};

// 定期检查学生数据是否有变更（例如：学生被删除）
function startDataChangeChecking() {
    // 每5秒检查一次
    setInterval(checkStudentDataChanged, 5000);
}

// 检查学生数据是否发生变化
function checkStudentDataChanged() {
    // 尝试从localStorage获取数据变更时间戳
    const storedTimestamp = localStorage.getItem('studentDataChangeTimestamp');
    
    if (storedTimestamp && parseInt(storedTimestamp) > lastDataCheckTimestamp) {
        console.log('检测到学生数据变更，刷新评语列表...');
        lastDataCheckTimestamp = parseInt(storedTimestamp);
        initCommentList();  // 重新加载评语列表
    }
}

// 添加DOM监控，确保按钮事件始终有效
function monitorDOMChanges() {
    console.log('开始监控DOM变化...');
    
    // 直接绑定事件，不依赖于jQuery或DOM观察器
    setInterval(function() {
        const saveBtn = document.getElementById('saveCommentBtn');
        if (saveBtn && !saveBtn.hasAttribute('data-event-bound')) {
            console.log('发现未绑定事件的保存按钮，添加点击事件');
            
            // 标记按钮已绑定事件，避免重复绑定
            saveBtn.setAttribute('data-event-bound', 'true');
            
            // 添加直接的点击事件，不使用addEventListener
            saveBtn.onclick = function(event) {
                console.log('保存按钮点击事件触发(通过DOM监控)');
                event.preventDefault();
            saveComment();
                return false;
            };
        }
    }, 1000); // 每秒检查一次
}

// 初始化函数
function initialize() {
    console.log('初始化评语管理...');
    
    // 获取班级ID
    fetchCurrentUserClassId();
    
    // 绑定事件监听器
    bindEventListeners();
    
    // 初始化评语列表
    initCommentList();
    
    // 检查新功能提示
    checkNewFeatureTips();
    
    // 监听DOM变化
    monitorDOMChanges();
    
    // 启动数据变更检查
    startDataChangeChecking();
    
    console.log('评语管理初始化完成');
}

// 在页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initialize);

// 初始化评语列表
function initCommentList() {
    console.log('初始化评语列表...');
    const startTime = performance.now();
    
    const commentCards = document.getElementById('commentCards');
    const emptyState = document.getElementById('emptyState');
    const commentsHeader = document.getElementById('commentsHeader');
    
    if (!commentCards) {
        console.error('无法找到评语卡片容器');
        return;
    }
    
    // 显示加载状态
    commentCards.innerHTML = `
        <div class="col-12 text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2">正在加载数据...</p>
        </div>
    `;
    
    // 从服务器获取学生数据
    fetch('/api/students')
        .then(response => {
            if (!response.ok) {
                throw new Error(`服务器响应错误: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                commentCards.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-danger">
                            <i class='bx bx-error-circle'></i> ${data.error}
                        </div>
                    </div>
                `;
                return;
            }
            
            const students = data.students;
            // 获取有评语的学生数量
            const commentsCount = students.filter(student => student.comments).length;
            const exportSettings = dataService.getExportSettings();
            
            console.log(`从服务器获取学生数据:`, students.length, '条');
            console.log(`有评语的学生:`, commentsCount, '人');
            
            // 设置页面标题
            if (commentsHeader) {
                const className = exportSettings.className || (students.length > 0 ? students[0].class : '未设置');
                commentsHeader.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <h1 class="page-title">评语管理</h1>
                        <div class="text-muted">
                            <span>班级：${className}</span> | 
                            <span>班主任：${exportSettings.teacherName || '未设置'}</span> | 
                            <span>学生数：${students.length}</span> | 
                            <span>评语数：${commentsCount}</span>
                        </div>
                    </div>
                `;
            }
            
            // 使用文档片段减少DOM操作，提高性能
            const fragment = document.createDocumentFragment();
            
            // 显示空状态或评语卡片
            if (students.length === 0) {
                if (emptyState) emptyState.classList.remove('d-none');
                // 清空评语区域
                commentCards.innerHTML = '';
            } else {
                if (emptyState) emptyState.classList.add('d-none');
                
                // 按班级分组学生
                const studentsByClass = {};
                students.forEach(student => {
                    const className = student.class || '未分班';
                    if (!studentsByClass[className]) {
                        studentsByClass[className] = [];
                    }
                    studentsByClass[className].push(student);
                });
                
                // 展示已分组的学生
                commentCards.innerHTML = '';
                Object.keys(studentsByClass).sort().forEach(className => {
                    // 添加班级标题
                    const classTitle = document.createElement('div');
                    classTitle.className = 'col-12 mt-4 mb-2';
                    classTitle.innerHTML = `
                        <h4 class="class-title">
                            <i class='bx bx-group'></i> ${className}
                            <span class="badge bg-primary ms-2">${studentsByClass[className].length} 名学生</span>
                        </h4>
                        <hr>
                    `;
                    fragment.appendChild(classTitle);
                    
                    // 先对班级内的学生按学号排序
                    studentsByClass[className].sort((a, b) => {
                        return parseInt(a.id) - parseInt(b.id);
                    });
                    
                    // 添加该班级的学生卡片
                    studentsByClass[className].forEach(student => {
                        // 直接使用学生数据中的comments字段
                        const commentData = student.comments ? {
                            studentId: student.id,
                            content: student.comments,
                            updateDate: student.updated_at
                        } : null;
                        
                        const card = createCommentCard(student, commentData);
                        fragment.appendChild(card);
                    });
                });
                
                commentCards.appendChild(fragment);
            }
            
            const endTime = performance.now();
            console.log(`评语列表更新完成，用时: ${(endTime - startTime).toFixed(2)}ms`);
        })
        .catch(error => {
            console.error('加载学生数据时出错:', error);
            commentCards.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-danger">
                        <i class='bx bx-error-circle'></i> 加载学生数据时出错，请确保后端服务器已启动并且可以访问。错误详情: ${error.message}
                    </div>
                    <div class="alert alert-info">
                        <h5>排查步骤：</h5>
                        <ol>
                            <li>确认后端服务器正在运行</li>
                            <li>验证网络连接正常</li>
                            <li>检查浏览器控制台(F12)获取更多错误信息</li>
                            <li>尝试重新启动服务器和浏览器</li>
                        </ol>
                    </div>
                </div>
            `;
        });
}

// 创建评语卡片
function createCommentCard(student, commentData) {
    const col = document.createElement('div');
    col.className = 'col-md-3 col-lg-3 col-xl-1-5 mb-4';
    col.dataset.studentId = student.id; // 添加数据属性以便于实时更新
    
    // 处理评语数据（兼容旧版本和新版本）
    let comment;
    if (Array.isArray(commentData)) {
        // 旧版本：传入的是评语数组，需要查找指定学生的评语
        comment = commentData.find(c => c.studentId === student.id);
    } else {
        // 新版本：传入的是单个评语对象
        comment = commentData;
    }
    
    let commentContent = comment ? comment.content : '暂无评语';
    // 移除评语末尾的"（字数：xxx字）"格式
    commentContent = commentContent.replace(/（字数：\d+字）$/, '');
    
    const updateDate = comment ? comment.updateDate : '';
    
    // 评语字数
    const commentLength = commentContent.length;
    
    // 设置字数的颜色 - 从绿色(接近0字)渐变到红色(接近1000字)
    const maxLength = 260;  // 修改为5000字 // 临时调整为5000字
    const percentage = commentLength / maxLength; // 使用百分比来确定颜色
    let textColor = '';
    
    if (percentage < 0.5) {
        // 0-50%: 从绿色渐变到黄色
        const green = Math.floor(128 + (127 - 128) * (percentage * 2)); // 从128减小
        const red = Math.floor(40 + (255 - 40) * (percentage * 2));     // 从40增加到255
        textColor = `rgb(${red}, ${green}, 0)`;
    } else {
        // 50-100%: 从黄色渐变到红色
        const green = Math.floor(127 * (2 - percentage * 2)); // 从127减小到0
        const red = 255; // 一直保持255
        textColor = `rgb(${red}, ${green}, 0)`;
    }
    
    // 是否接近字数限制的警告
    const warningClass = percentage > 0.9 ? 'fw-bold' : '';
    
    col.innerHTML = `
        <div class="comment-card">
            <span class="card-badge ${student.gender === '男' ? 'male' : 'female'}">${student.gender}</span>
            <div class="student-info">
                <div class="student-avatar">
                    <i class='bx bx-user'></i>
                </div>
                <div class="student-details">
                    <h4>${student.name}</h4>
                    <div class="text-muted">学号: ${student.id}</div>
                    <div class="text-muted">班级: ${student.class || '未分班'}</div>
                </div>
            </div>
            <div class="comment-content mt-3">
                <div class="comment-text">${commentContent}</div>
                <div class="comment-date"><i class='bx bx-calendar'></i> ${updateDate || '未更新'}</div>
            </div>
            <div class="comment-card-footer">
                <div class="comment-stats">
                    <div class="comment-stat">
                        <i class='bx bx-text'></i> <span style="color: ${textColor}" class="${warningClass}">${commentLength}/${maxLength}</span> 字
                    </div>
                </div>
                <div>
                    <button class="btn btn-sm btn-outline-info ai-comment-btn me-1 breathing-button" data-student-id="${student.id}" data-student-name="${student.name}" data-class-id="${student.class_id}" style="background: linear-gradient(135deg, #e0f7ff, #ffffff); border-color: #00c3ff; color: #0072ff; font-weight: bold;">
                        <i class='bx bx-bot'></i> AI海海
                    </button>
                    <button class="btn btn-sm btn-primary edit-comment-btn" data-student-id="${student.id}" data-student-name="${student.name}" data-class-id="${student.class_id}">
                        <i class='bx bx-edit'></i> 编辑评语
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 绑定编辑按钮事件
    const editBtn = col.querySelector('.edit-comment-btn');
    if (editBtn) {
        editBtn.addEventListener('click', function() {
            fillCommentForm(this.dataset.studentId, this.dataset.studentName, this.dataset.classId);
        });
    }
    
    // 绑定AI评语助手按钮事件
    const aiBtn = col.querySelector('.ai-comment-btn');
    if (aiBtn) {
        aiBtn.addEventListener('click', function() {
            showAICommentAssistant(this.dataset.studentId, this.dataset.studentName, this.dataset.classId);
        });
    }
    
    return col;
}

// 填充评语表单
function fillCommentForm(studentId, studentName, classId) {
    console.log('填充评语表单:', studentId, studentName, '班级ID:', classId);
    
    // 设置学生信息
    const modalStudentName = document.getElementById('modalStudentName');
    const modalStudentId = document.getElementById('modalStudentId');
    const commentText = document.getElementById('commentText');
    
    if (!modalStudentName || !modalStudentId || !commentText) {
        showNotification('找不到必要的表单元素', 'error');
        return;
    }
    
    // 设置学生信息
    modalStudentName.textContent = studentName;
    modalStudentId.textContent = `学号: ${studentId}`;
    
    // 存储学生ID，用于保存评语
    commentText.dataset.studentId = studentId;
    currentStudentId = studentId;
    
    // 存储班级ID
    if (!document.getElementById('currentClassId')) {
        const classIdField = document.createElement('input');
        classIdField.type = 'hidden';
        classIdField.id = 'currentClassId';
        document.body.appendChild(classIdField);
    }
    document.getElementById('currentClassId').value = classId;
    
    // 显示加载状态
    commentText.value = '加载中...';
    commentText.disabled = true;
    
    if (USE_SERVER_API) {
        // 从服务器获取评语数据
        fetch(`/api/comments/${studentId}?class_id=${classId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'ok' && data.comment) {
                    commentText.value = data.comment.content || '';
                } else {
                    commentText.value = '';
                }
            })
            .catch(error => {
                console.error('获取评语数据出错:', error);
                commentText.value = '';
                showNotification('获取评语数据失败: ' + error.message, 'error');
            })
            .finally(() => {
                commentText.disabled = false;
                
                // 显示模态框
                const modal = new bootstrap.Modal(document.getElementById('editCommentModal'));
                modal.show();
                
                // 更新字数统计
                updateCharCount();
                
                // 聚焦到文本框
                commentText.focus();
                
                // 渲染评语模板按钮
                renderTemplateButtons('all');
            });
    } else {
        // 从本地存储获取评语数据
        const comment = dataService.getCommentByStudentId(studentId);
        commentText.value = comment ? comment.content : '';
        commentText.disabled = false;
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('editCommentModal'));
        modal.show();
        
        // 更新字数统计
        updateCharCount();
        
        // 聚焦到文本框
        commentText.focus();
        
        // 渲染评语模板按钮
        renderTemplateButtons('all');
    }
}

// 保存评语
function saveComment() {
    console.log('执行保存评语函数...');
    
    const commentText = document.getElementById('commentText');
    if (!commentText) {
        console.error('找不到评语输入框');
        showNotification('找不到评语输入框', 'error');
        return;
    }
    
    const studentId = commentText.dataset.studentId;
    if (!studentId) {
        console.error('未找到学生ID');
        showNotification('未找到学生ID', 'error');
        return;
    }
    
    // 先调用一次字数统计更新，确保字数已被限制在允许范围内
    updateCharCount();
    
    const content = commentText.value.trim();
    if (!content) {
        console.error('评语内容为空');
        showNotification('请输入评语内容', 'error');
        return;
    }
    
    // 检查评语字数是否超过限制
    const maxLength = 260;  // 修改为5000字
    if (content.length > maxLength) {
        console.warn(`评语内容超过字数限制: ${content.length}/${maxLength}，将自动截断`);
        // 自动截断内容而不是显示错误
        commentText.value = content.substring(0, maxLength);
        updateCharCount();
        showNotification(`评语内容已自动截断至${maxLength}字`, 'warning');
    }
    
    // 检查是否为添加模式
    const appendMode = document.getElementById('appendModeSwitch')?.checked || false;
    console.log(`保存模式: ${appendMode ? '添加' : '替换'}`);
    
    // 获取班级ID - 优先使用存储的班级ID，如果没有则使用当前用户的班级ID
    const storedClassId = document.getElementById('currentClassId')?.value;
    const currentUserClassId = window.currentUserClassId;
    console.log('保存评语使用班级ID:', storedClassId || currentUserClassId, '(存储的班级ID:', storedClassId, ', 当前用户班级ID:', currentUserClassId, ')');
    
    // 创建评语对象
    const commentData = {
        studentId,
        content: commentText.value.trim(), // 使用可能被截断后的内容
        appendMode,
        classId: storedClassId || currentUserClassId, // 优先使用存储的班级ID
        isAIComment: true // 添加标志允许跨班级操作
    };
    
    // 显示处理状态
    const saveBtn = document.getElementById('saveCommentBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
    }
    
    console.log('发送保存请求:', commentData);
    
    // 发送到服务器
    fetch('/api/comments', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(commentData)
    })
    .then(response => {
        console.log('服务器响应状态:', response.status);
        if (!response.ok) {
            return response.text().then(text => {
                try {
                    // 尝试解析为JSON
                    const errorData = JSON.parse(text);
                    throw new Error(errorData.message || `HTTP错误! 状态: ${response.status}`);
                } catch (e) {
                    // 如果不是有效JSON，返回原始错误
                    throw new Error(`HTTP错误! 状态: ${response.status}, 响应: ${text}`);
                }
            });
        }
        return response.json();
    })
        .then(data => {
        console.log('保存评语响应:', data);
            if (data.status === 'ok') {
                // 关闭模态框
                const modal = bootstrap.Modal.getInstance(document.getElementById('editCommentModal'));
            if (modal) {
                modal.hide();
            }
            
            // 实时更新评语卡片
            const updatedComment = {
                content: data.updatedContent || content,
                updateDate: data.updateDate || new Date().toLocaleString()
            };
            updateCommentCard(studentId, updatedComment);
                
                // 显示成功通知
                showNotification('评语保存成功');
            } else {
            throw new Error(data.message || '保存失败');
            }
        })
        .catch(error => {
            console.error('保存评语时出错:', error);
        showNotification('保存评语时出错: ' + error.message, 'error');
        })
        .finally(() => {
            // 恢复按钮状态
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '保存评语';
            }
        });
}

// 实时更新评语卡片
function updateCommentCard(studentId, comment) {
    if (!studentId || !comment) {
        console.error('更新评语卡片失败：缺少必要参数');
        return;
    }

    // 查找对应的评语卡片
    const commentCard = document.querySelector(`[data-student-id="${studentId}"]`);
    if (!commentCard) {
        console.error(`找不到ID为 ${studentId} 的评语卡片`);
        return;
    }
    
    // 更新评语内容
    const contentElement = commentCard.querySelector('.comment-text');
    if (contentElement) {
        // 移除评语末尾的"（字数：xxx字）"格式
        let cleanedContent = (comment.content || '暂无评语').replace(/（字数：\d+字）$/, '');
        contentElement.textContent = cleanedContent;
    } else {
        console.error('找不到评语内容元素');
    }
    
    // 更新评语日期
    const dateElement = commentCard.querySelector('.comment-date');
    if (dateElement) {
        dateElement.innerHTML = `<i class='bx bx-calendar'></i> ${comment.updateDate || '未更新'}`;
    } else {
        console.error('找不到评语日期元素');
    }
    
    // 更新评语字数和状态
    const commentLength = (comment.content || '').length;
    let lengthColorClass = 'text-danger';
    if (commentLength >= 100) {
        lengthColorClass = 'text-success';
    } else if (commentLength >= 50) {
        lengthColorClass = 'text-warning';
    }
    
    const statElement = commentCard.querySelector('.comment-stat');
    if (statElement) {
        statElement.innerHTML = `
            <i class='bx bx-text'></i> ${commentLength} 字
            <span class="ms-1 ${lengthColorClass}">${commentLength < 50 ? '(字数不足)' : ''}</span>
        `;
    } else {
        console.error('找不到评语统计元素');
    }
}

// 筛选评语
function filterComments(keyword) {
    const commentCards = document.getElementById('commentCards').children;
    const emptyState = document.getElementById('emptyState');
    
    keyword = keyword.toLowerCase();
    let visibleCount = 0;
    
    // 遍历所有评语卡片
    for (let i = 0; i < commentCards.length; i++) {
        const card = commentCards[i];
        if (card.id === 'emptyState') continue;
        
        const studentName = card.querySelector('.student-name').textContent.toLowerCase();
        const studentId = card.querySelector('.student-id').textContent.toLowerCase();
        const commentContent = card.querySelector('.comment-content').textContent.toLowerCase();
        
        // 检查是否匹配关键字
        if (studentName.includes(keyword) || studentId.includes(keyword) || commentContent.includes(keyword)) {
            card.style.display = '';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    }
    
    // 显示或隐藏空状态
    if (visibleCount === 0 && emptyState) {
        emptyState.classList.remove('d-none');
    } else if (emptyState) {
        emptyState.classList.add('d-none');
    }
}

// 显示打印预览
function showPrintPreview() {
    console.log('显示打印预览');
    
    // 获取预览模态框元素
    const previewModal = document.getElementById('printPreviewModal');
    const previewContent = document.getElementById('previewContent');
    
    if (!previewModal || !previewContent) {
        showNotification('找不到预览模态框或内容元素', 'error');
        return;
    }
    
    // 显示加载状态
    previewContent.innerHTML = `
        <div class="d-flex justify-content-center align-items-center p-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="ms-3 mb-0">正在生成预览...</p>
        </div>
    `;
    
    // 显示模态框
    const modal = new bootstrap.Modal(previewModal);
    modal.show();
    
    // 创建iframe来加载预览内容
    const previewFrame = document.createElement('iframe');
    previewFrame.style.width = '100%';
    previewFrame.style.height = '100%';
    previewFrame.style.border = 'none';
    previewFrame.className = 'preview-frame';
    
    // 在iframe加载完成后处理打印按钮
    previewFrame.onload = function() {
        // 绑定打印按钮
        const printBtn = document.getElementById('printBtn');
        if (printBtn) {
            printBtn.onclick = function() {
                previewFrame.contentWindow.print();
            };
        }
        
        // 给iframe添加消息监听器，以接收加载完成通知
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'previewLoaded') {
                console.log('预览加载完成', event.data.timestamp);
                // 这里可以执行预览加载完成后的操作
            } else if (event.data && event.data.type === 'previewError') {
                console.error('预览加载出错', event.data.error);
                showNotification('预览生成失败: ' + event.data.error, 'error');
            }
        });
    };
    
    // 清空预览内容并添加iframe
    previewContent.innerHTML = '';
    previewContent.appendChild(previewFrame);
    
    // 获取过滤参数
    const params = new URLSearchParams();
    
    // 获取班级选择器
    const classFilter = document.getElementById('commentClassFilter');
    if (classFilter && classFilter.value) {
        params.append('class', classFilter.value);
    }
    
    // 生成查询字符串
    const queryString = params.toString() ? `?${params.toString()}` : '';
    
    // 直接设置iframe的src为预览API，加上查询参数
    previewFrame.src = `/api/preview-comments${queryString}`;
    
    // 错误处理
    previewFrame.onerror = function() {
        previewContent.innerHTML = `
            <div class="alert alert-danger m-5">
                <h4 class="alert-heading">加载预览失败</h4>
                <p>无法连接到服务器或服务器返回错误。请稍后再试。</p>
            </div>
        `;
        showNotification('加载预览失败，请稍后再试', 'error');
    };
}

// 导出评语
function exportComments() {
    try {
        console.log('开始导出评语...');
        
        // 创建导出格式选择对话框
        const modalId = 'exportFormatModal';
        
        // 检查是否已存在模态框
        let modalElement = document.getElementById(modalId);
        
        // 如果不存在，则创建新的模态框
        if (!modalElement) {
            console.log('创建导出格式选择对话框...');
            modalElement = document.createElement('div');
            modalElement.id = modalId;
            modalElement.className = 'modal fade';
            modalElement.tabIndex = '-1';
            modalElement.setAttribute('aria-labelledby', `${modalId}Label`);
            modalElement.setAttribute('aria-hidden', 'true');
            
            modalElement.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="${modalId}Label">选择导出格式</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="关闭"></button>
                        </div>
                        <div class="modal-body">
                            <div class="d-flex justify-content-center">
                                <button id="exportPdfBtn" class="btn btn-primary btn-lg m-2">
                                    <i class='bx bxs-file-pdf'></i> 导出PDF
                                </button>
                                <button id="exportExcelBtn" class="btn btn-success btn-lg m-2">
                                    <i class='bx bxs-file-excel'></i> 导出Excel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modalElement);
        }
        
        // 确保Bootstrap已加载
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap未加载，无法显示模态框');
            showNotification('导出功能错误：Bootstrap未加载', 'error');
            return;
        }
        
        // 创建Bootstrap模态框实例
        const modal = new bootstrap.Modal(modalElement);
        
        // 绑定按钮事件
        const pdfBtn = document.getElementById('exportPdfBtn');
        const excelBtn = document.getElementById('exportExcelBtn');
        
        if (pdfBtn) {
            // 移除旧的事件监听器
            const newPdfBtn = pdfBtn.cloneNode(true);
            pdfBtn.parentNode.replaceChild(newPdfBtn, pdfBtn);
            
            // 重新绑定事件
            document.getElementById('exportPdfBtn').addEventListener('click', function() {
                console.log('点击导出PDF按钮');
                modal.hide();
                exportCommentsToPdf();
            });
        }
        
        if (excelBtn) {
            // 移除旧的事件监听器
            const newExcelBtn = excelBtn.cloneNode(true);
            excelBtn.parentNode.replaceChild(newExcelBtn, excelBtn);
            
            // 重新绑定事件
            document.getElementById('exportExcelBtn').addEventListener('click', function() {
                console.log('点击导出Excel按钮');
                modal.hide();
                exportCommentsToExcel();
            });
        }
        
        // 显示模态框
        console.log('显示导出格式选择对话框');
        modal.show();
    } catch (error) {
        console.error('导出评语错误:', error);
        showNotification('导出功能出错: ' + error.message, 'error');
    }
}

// 导出评语为PDF
function exportCommentsToPdf() {
    // 显示加载通知
    showNotification('正在生成PDF，请稍候...', 'info', 0);
    
    // 获取过滤参数
    const params = new URLSearchParams();
    
    // 获取班级选择器
    const classFilter = document.getElementById('commentClassFilter');
    if (classFilter && classFilter.value) {
        params.append('class', classFilter.value);
    }
    
    // 生成查询字符串
    const queryString = params.toString() ? `?${params.toString()}` : '';
    
    console.log('导出请求URL:', `/api/export-comments-pdf${queryString}`);
    
    // 设置超时控制
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
        controller.abort();
    }, 60000); // 60秒超时
    
    // 显示长时间进度提示
    setTimeout(() => {
        // 5秒后如果仍在加载，显示长时间等待提示
        const toastContainer = document.getElementById('toastContainer');
        if (toastContainer) {
            const toasts = toastContainer.querySelectorAll('.toast');
            // 如果仍有加载通知，显示额外的提示
            if (toasts.length > 0) {
                showNotification('PDF生成中，请继续等待...', 'info', 8000);
            }
        }
    }, 5000);
    
    // 调用导出API
    fetch(`/api/export-comments-pdf${queryString}`, {
        signal: controller.signal
    })
        .then(response => {
            clearTimeout(timeoutId); // 清除超时
            // 即使是错误状态码，也获取JSON响应
            return response.json().then(data => {
                // 将响应状态码和数据一起返回
                return { 
                    ok: response.ok, 
                    status: response.status,
                    data: data 
                };
            });
        })
        .then(result => {
            // 关闭加载通知
            const toastContainer = document.getElementById('toastContainer');
            if (toastContainer) {
                const toasts = toastContainer.querySelectorAll('.toast');
                toasts.forEach(toast => {
                    const bsToast = bootstrap.Toast.getInstance(toast);
                    if (bsToast) bsToast.hide();
                });
            }
            
            // 检查结果
            if (result.ok && result.data.status === 'ok') {
                // 显示成功通知
                showNotification('PDF生成成功，正在下载...');
                
                // 创建下载链接
                const downloadLink = document.createElement('a');
                downloadLink.href = result.data.download_url;
                downloadLink.download = result.data.download_url.split('/').pop();
                downloadLink.target = '_blank'; // 在新标签页打开
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            } else {
                // 显示错误信息
                let errorMessage = '导出PDF失败，未知错误';
                
                // 正确提取错误信息
                try {
                    if (result.data) {
                        // 如果data是字符串，直接使用
                        if (typeof result.data === 'string') {
                            errorMessage = result.data;
                        } 
                        // 如果data是对象
                        else if (typeof result.data === 'object') {
                            // 尝试获取message字段
                            if (typeof result.data.message === 'string') {
                                errorMessage = result.data.message;
                            } 
                            // 如果status是error并且有message
                            else if (result.data.status === 'error' && typeof result.data.message === 'string') {
                                errorMessage = result.data.message;
                            }
                            // 如果对象没有可用的message字段，尝试转换为字符串
                            else {
                                // 尝试使用JSON.stringify转换
                                try {
                                    const dataStr = JSON.stringify(result.data);
                                    if (dataStr && dataStr !== '{}' && dataStr !== '[]') {
                                        errorMessage = '服务器返回: ' + dataStr.substring(0, 100);
                                    }
                                } catch (jsonErr) {
                                    console.error('JSON转换错误:', jsonErr);
                                }
                            }
                        }
                    }
                    // 如果没有提取到有意义的错误信息，加上HTTP状态码
                    if (errorMessage === '导出PDF失败，未知错误' && result.status) {
                        errorMessage += ` (HTTP ${result.status})`;
                    }
                } catch (e) {
                    console.error('解析错误消息时出错:', e);
                    errorMessage = `解析错误消息时出错: ${e.message}`;
                }
                
                showNotification(`导出PDF失败: ${errorMessage}`, 'error');
                console.error('导出PDF失败详情:', result);
            }
        })
        .catch(error => {
            clearTimeout(timeoutId); // 清除超时
            console.error('导出PDF时网络请求出错:', error);
            
            // 关闭加载通知
            const toastContainer = document.getElementById('toastContainer');
            if (toastContainer) {
                const toasts = toastContainer.querySelectorAll('.toast');
                toasts.forEach(toast => {
                    const bsToast = bootstrap.Toast.getInstance(toast);
                    if (bsToast) bsToast.hide();
                });
            }
            
            // 处理超时错误
            if (error.name === 'AbortError') {
                showNotification('PDF生成超时，请选择较小的班级范围或稍后重试', 'error');
            } else {
                showNotification('导出PDF时出错，请检查网络连接或服务器状态', 'error');
            }
        });
}

// 导出评语为Excel
function exportCommentsToExcel() {
    try {
        console.log('开始导出Excel评语...');
        
        // 显示加载状态
        showNotification('正在导出Excel评语...', 'info', 0);
        
        // 获取班级ID
        let classId;
        
        // 尝试从班级过滤器获取班级ID
        const classFilter = document.getElementById('commentClassFilter');
        if (classFilter && classFilter.value) {
            classId = classFilter.value;
            console.log('从过滤器获取班级ID:', classId);
        }
        
        // 构建请求URL - 确保URL路径正确
        let url = `/api/export-comments-excel`;
        if (classId) {
            url += `?class_id=${classId}`;
        }
        
        console.log('导出Excel请求URL:', url);
        
        // 创建一个隐藏的iframe来处理下载
        const downloadFrame = document.createElement('iframe');
        downloadFrame.style.display = 'none';
        document.body.appendChild(downloadFrame);
        
        // 设置iframe的src属性以触发下载
        downloadFrame.src = url;
        
        // 监听iframe的load事件
        downloadFrame.onload = function() {
            // 延迟移除iframe
            setTimeout(() => {
                document.body.removeChild(downloadFrame);
                
                // 隐藏加载通知
                const toastContainer = document.getElementById('toastContainer');
                if (toastContainer) {
                    const toasts = toastContainer.querySelectorAll('.toast');
                    toasts.forEach(toast => {
                        const bsToast = bootstrap.Toast.getInstance(toast);
                        if (bsToast) bsToast.hide();
                    });
                }
                
                // 显示成功消息
                showNotification('评语导出请求已发送，请检查下载内容', 'success');
            }, 1000);
        };
        
    } catch (error) {
        console.error('导出Excel评语错误:', error);
        showNotification('导出Excel功能出错: ' + error.message, 'error');
    }
}

// 导入docx库
async function importDocxLibrary() {
    // 如果已经加载了docx库，直接返回
    if (window.docx) {
        return window.docx;
    }
    
    // 否则动态加载docx库
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/docx@7.8.2/build/index.js';
        script.onload = () => {
            if (window.docx) {
                resolve(window.docx);
            } else {
                reject(new Error('加载docx库失败'));
            }
        };
        script.onerror = () => {
            reject(new Error('加载docx库失败'));
        };
        document.head.appendChild(script);
    });
}

// 格式化日期
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// 更新字数统计
function updateCharCount() {
    console.log('更新字数统计...');
    const commentText = document.getElementById('commentText');
    const charCount = document.getElementById('commentCharCount');
    const batchCommentText = document.getElementById('batchCommentText');
    const batchCharCount = document.getElementById('batchCommentCharCount');
    
    if (commentText && charCount) {
        const maxLength = 260;  // 修改为5000字
        const count = commentText.value.length;
        charCount.textContent = `${count}/${maxLength}`;
        console.log(`当前字数: ${count}/${maxLength}`);
        
        // 限制输入字数
        if (count > maxLength) {
            commentText.value = commentText.value.substring(0, maxLength);
            charCount.textContent = `${maxLength}/${maxLength}`;
            console.log(`已截断至最大字数: ${maxLength}`);
        }
        
        // 根据字数改变颜色提示 - 从绿色(接近0字)渐变到红色(接近字数限制)
        const percentage = Math.min(count / maxLength, 1.0); // 确保不超过1.0
        
        if (percentage < 0.5) {
            // 0-50%: 从绿色渐变到黄色
            const green = Math.floor(128 + (127 - 128) * (percentage * 2)); // 从128减小
            const red = Math.floor(40 + (255 - 40) * (percentage * 2));     // 从40增加到255
            charCount.style.color = `rgb(${red}, ${green}, 0)`;
        } else {
            // 50-100%: 从黄色渐变到红色
            const green = Math.floor(127 * (2 - percentage * 2)); // 从127减小到0
            const red = 255; // 一直保持255
            charCount.style.color = `rgb(${red}, ${green}, 0)`;
        }
        
        // 如果接近限制，添加警告效果
        if (percentage > 0.9) {
            charCount.classList.add('fw-bold');
        } else {
            charCount.classList.remove('fw-bold');
        }
    }
    
    if (batchCommentText && batchCharCount) {
        const maxLength = 260;  // 修改为5000字
        const count = batchCommentText.value.length;
        batchCharCount.textContent = `${count}/${maxLength}`;
        
        // 限制输入字数
        if (count > maxLength) {
            batchCommentText.value = batchCommentText.value.substring(0, maxLength);
            batchCharCount.textContent = `${maxLength}/${maxLength}`;
        }
        
        // 根据字数改变颜色提示 - 从绿色(接近0字)渐变到红色(接近字数限制)
        const percentage = Math.min(count / maxLength, 1.0); // 确保不超过1.0
        
        if (percentage < 0.5) {
            // 0-50%: 从绿色渐变到黄色
            const green = Math.floor(128 + (127 - 128) * (percentage * 2)); // 从128减小
            const red = Math.floor(40 + (255 - 40) * (percentage * 2));     // 从40增加到255
            batchCharCount.style.color = `rgb(${red}, ${green}, 0)`;
        } else {
            // 50-100%: 从黄色渐变到红色
            const green = Math.floor(127 * (2 - percentage * 2)); // 从127减小到0
            const red = 255; // 一直保持255
            batchCharCount.style.color = `rgb(${red}, ${green}, 0)`;
        }
        
        // 如果接近限制，添加警告效果
        if (percentage > 0.9) {
            batchCharCount.classList.add('fw-bold');
        } else {
            batchCharCount.classList.remove('fw-bold');
        }
    }
}
// 显示通知
function showNotification(message, type = 'success', duration = 3000) {
    // 创建一个toast元素
    const toastId = `toast-${Date.now()}`;
    const toast = document.createElement('div');
    toast.className = `toast align-items-center border-0 ${type === 'error' ? 'bg-danger' : type === 'info' ? 'bg-info' : 'bg-success'} text-white`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.id = toastId;
    
    // 设置Toast内容
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bx ${type === 'error' ? 'bx-error-circle' : type === 'info' ? 'bx-info-circle' : 'bx-check-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="关闭"></button>
        </div>
    `;
    
    // 将Toast添加到容器
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        // 如果没有容器，创建一个并添加到body，定位在屏幕中间
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'position-fixed top-50 start-50 translate-middle p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    toastContainer.appendChild(toast);
    
    // 监听隐藏事件，从DOM移除元素
    toast.addEventListener('hidden.bs.toast', function() {
        document.getElementById(toastId)?.remove();
    });
    
    // 显示Toast，0表示不自动关闭
    const delay = duration === 0 ? Infinity : duration;
    const bsToast = new bootstrap.Toast(toast, { delay: delay });
    bsToast.show();
    
    // 返回toast实例以便可以手动控制
    return bsToast;
}

// 修改学生操作函数，添加跨页面通信
// 当在学生管理页面做出更改后，通知评语管理页面更新
function notifyStudentDataChanged() {
    console.log('学生数据已变更，发送通知...');
    
    // 方法1: 通过localStorage触发storage事件
    const timestamp = Date.now();
    localStorage.setItem('studentDataChangeTimestamp', timestamp);
    
    // 方法2: 通过window.postMessage通知所有iframe
    if (window.frames && window.frames.length) {
        for (let i = 0; i <window.frames.length; i++) {
            try {
                window.frames[i].postMessage({
                    type: 'studentDataChanged',
                    timestamp: timestamp
                }, '*');
            } catch (e) {
                console.error('向iframe发送消息失败:', e);
            }
        }
    }
    
    // 方法3: 通过自定义事件
    if (window.eventBus) {
        const event = new CustomEvent('studentDataChanged', {
            detail: {
                timestamp: timestamp
            }
        });
        window.eventBus.dispatchEvent(event);
    }
    
    // 方法4: 直接调用页面上的刷新方法
    try {
        if (window.refreshCommentList) {
            window.refreshCommentList();
        }
        
        // 如果评语页面在iframe中
        const commentsFrame = document.querySelector('iframe[src*="comments.html"]');
        if (commentsFrame && commentsFrame.contentWindow && commentsFrame.contentWindow.refreshCommentList) {
            commentsFrame.contentWindow.refreshCommentList();
        }
    } catch (e) {
        console.error('直接调用刷新方法失败:', e);
    }
}

// 检查并显示新功能提示
function checkNewFeatureTips() {
    // 使用localStorage检查用户是否看过新功能提示
    const hasSeenNewFeatureTip = localStorage.getItem('hasSeenImportFeatureTip');
    
    if (!hasSeenNewFeatureTip) {
        // 用户未看过提示，显示模态框
        setTimeout(() => {
            try {
                const newFeatureModal = new bootstrap.Modal(document.getElementById('newFeatureModal'));
                newFeatureModal.show();
                
                // 标记用户已看过提示
                localStorage.setItem('hasSeenImportFeatureTip', 'true');
            } catch (error) {
                console.error('显示新功能提示模态框失败:', error);
            }
        }, 1000); // 延迟1秒显示，确保页面已完全加载
    }
}

// 获取当前用户的班级ID
function fetchCurrentUserClassId() {
    // 首先检查是否已经有存储的班级ID
    if (document.getElementById('currentUserClassId')) {
        window.currentUserClassId = document.getElementById('currentUserClassId').value;
        console.log('从DOM元素获取当前用户班级ID:', window.currentUserClassId);
        return;
    }
    
    // 从meta标签获取班级ID
    const classIdMeta = document.querySelector('meta[name="user-class-id"]');
    if (classIdMeta) {
        window.currentUserClassId = classIdMeta.content;
        console.log('从meta标签获取当前用户班级ID:', window.currentUserClassId);
        
        // 创建隐藏字段存储班级ID
        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.id = 'currentUserClassId';
        hiddenField.value = window.currentUserClassId;
        document.body.appendChild(hiddenField);
        return;
    }
    
    // 设置默认班级ID
    window.currentUserClassId = "1";
    console.log('无法获取班级ID，使用默认班级ID:', window.currentUserClassId);
    
    // 创建隐藏字段存储默认班级ID
    const hiddenField = document.createElement('input');
    hiddenField.type = 'hidden';
    hiddenField.id = 'currentUserClassId';
    hiddenField.value = window.currentUserClassId;
    document.body.appendChild(hiddenField);
}

// 绑定事件监听器
function bindEventListeners() {
    // 绑定搜索框事件
    const searchInput = document.getElementById('commentSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterComments(this.value);
        });
    }
    
    // 绑定打印预览按钮
    const previewBtn = document.getElementById('previewCommentsBtn');
    if (previewBtn) {
        previewBtn.addEventListener('click', showPrintPreview);
    }
    
    // 绑定导出按钮
    const exportBtn = document.getElementById('exportCommentsBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportComments);
    }
    
    // 绑定导入按钮
    const importBtn = document.getElementById('importCommentsBtn');
    if (importBtn) {
        importBtn.addEventListener('click', showImportCommentsModal);
    }
    
    // 绑定评语表单提交事件
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveComment();
        });
    }
    
    // 绑定评语文本区域事件
    const commentTextarea = document.getElementById('commentContent');
    if (commentTextarea) {
        commentTextarea.addEventListener('input', updateCharCount);
    }
    
    // 绑定批量更新表单提交事件
    const batchUpdateForm = document.getElementById('batchUpdateForm');
    if (batchUpdateForm) {
        batchUpdateForm.addEventListener('submit', function(e) {
            e.preventDefault();
            batchUpdateComments();
        });
    }
    
    // 绑定班级过滤器变更事件
    const classFilter = document.getElementById('commentClassFilter');
    if (classFilter) {
        classFilter.addEventListener('change', function() {
            // 保存选择的班级ID
            currentClassId = this.value;
            // 重新加载评语列表
            initCommentList();
        });
    }
    
    // 绑定AI评语助手按钮
    const aiHelperBtn = document.getElementById('aiCommentHelperBtn');
    if (aiHelperBtn) {
        aiHelperBtn.addEventListener('click', function() {
            const studentId = document.getElementById('studentId').value;
            const studentName = document.getElementById('studentName').value;
            const classId = document.getElementById('classId').value;
            
            if (studentId && studentName) {
                showAICommentAssistant(studentId, studentName, classId);
            } else {
                showNotification('请先选择一个学生', 'warning');
            }
        });
    }
    
    // 绑定API设置按钮
    const apiSettingsBtn = document.getElementById('apiSettingsBtn');
    if (apiSettingsBtn) {
        apiSettingsBtn.addEventListener('click', showApiSettingsModal);
    }
    
    // 绑定导入评语相关事件
    bindImportCommentsEvents();
}

// 导入评语相关事件绑定
function bindImportCommentsEvents() {
    // 文件选择变化事件
    const importFileInput = document.getElementById('commentsImportFile');
    if (importFileInput) {
        importFileInput.addEventListener('change', handleImportFileSelection);
    }
    
    // 导入区域拖拽事件
    const dropZone = document.getElementById('importDropZone');
    if (dropZone) {
        // 阻止默认拖拽行为
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        // 高亮显示
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });
        
        // 处理拖放
        dropZone.addEventListener('drop', handleDrop, false);
    }
    
    // 下载模板按钮
    const downloadTemplateBtn = document.getElementById('downloadImportTemplateBtn');
    if (downloadTemplateBtn) {
        downloadTemplateBtn.addEventListener('click', downloadImportTemplate);
    }
    
    // 确认导入按钮
    const confirmImportBtn = document.getElementById('confirmImportBtn');
    if (confirmImportBtn) {
        confirmImportBtn.addEventListener('click', confirmImportComments);
    }
}

// 阻止默认拖拽行为
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// 高亮拖拽区域
function highlight() {
    const dropZone = document.getElementById('importDropZone');
    if (dropZone) {
        dropZone.classList.add('border-primary');
        dropZone.classList.add('bg-light-blue');
    }
}

// 取消高亮拖拽区域
function unhighlight() {
    const dropZone = document.getElementById('importDropZone');
    if (dropZone) {
        dropZone.classList.remove('border-primary');
        dropZone.classList.remove('bg-light-blue');
    }
}

// 处理拖放文件
function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    
    if (files.length > 0) {
        const fileInput = document.getElementById('commentsImportFile');
        fileInput.files = files;
        handleImportFileSelection({ target: fileInput });
    }
}

// 显示导入评语模态框
function showImportCommentsModal() {
    // 重置表单
    resetImportForm();
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('importCommentsModal'));
    modal.show();
}

// 重置导入表单
function resetImportForm() {
    const fileInput = document.getElementById('commentsImportFile');
    if (fileInput) {
        fileInput.value = '';
    }
    
    const fileNameDisplay = document.getElementById('importSelectedFileName');
    if (fileNameDisplay) {
        fileNameDisplay.textContent = '';
    }
    
    const previewArea = document.getElementById('importPreviewArea');
    if (previewArea) {
        previewArea.classList.add('d-none');
    }
    
    const previewLoading = document.getElementById('importPreviewLoading');
    if (previewLoading) {
        previewLoading.classList.add('d-none');
    }
    
    const importFilePath = document.getElementById('importFilePath');
    if (importFilePath) {
        importFilePath.value = '';
    }
    
    const confirmImportBtn = document.getElementById('confirmImportBtn');
    if (confirmImportBtn) {
        confirmImportBtn.classList.add('d-none');
        confirmImportBtn.disabled = true;
    }
    
    const importAppendMode = document.getElementById('importAppendMode');
    if (importAppendMode) {
        importAppendMode.checked = false;  // 默认使用替换模式
    }
    
    const importSummary = document.getElementById('importSummary');
    if (importSummary) {
        importSummary.textContent = '共发现0条评语记录，其中0条可以匹配到学生。';
    }
    
    // 清空预览容器
    const previewContainer = document.getElementById('importPreviewContainer');
    if (previewContainer) {
        previewContainer.innerHTML = '';
    }
}

// 处理导入文件选择
function handleImportFileSelection(e) {
    const fileInput = e.target;
    const files = fileInput.files;
    
    if (files.length === 0) {
        return;
    }
    
    const file = files[0];
    
    // 检查文件类型
    if (!file.name.toLowerCase().endsWith('.xlsx')) {
        showNotification('请上传Excel文件（.xlsx格式），不支持旧版.xls格式', 'warning');
        return;
    }
    
    // 显示文件名
    const fileNameDisplay = document.getElementById('importSelectedFileName');
    if (fileNameDisplay) {
        fileNameDisplay.textContent = file.name;
    }
    
    // 显示加载状态
    const previewLoading = document.getElementById('importPreviewLoading');
    if (previewLoading) {
        previewLoading.classList.remove('d-none');
    }
    
    const previewArea = document.getElementById('importPreviewArea');
    if (previewArea) {
        previewArea.classList.add('d-none');
    }
    
    const confirmImportBtn = document.getElementById('confirmImportBtn');
    if (confirmImportBtn) {
        confirmImportBtn.classList.add('d-none');
    }
    
    // 准备FormData对象
    const formData = new FormData();
    formData.append('file', file);
    
    console.log('开始上传Excel文件进行预览...');
    
    // 发送预览请求
    fetch('/api/preview-import-comments', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        // 检查响应状态
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.message || `HTTP错误! 状态: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        // 隐藏加载状态
        if (previewLoading) {
            previewLoading.classList.add('d-none');
        }
        
        if (data.status === 'ok') {
            console.log('预览成功:', data);
            
            // 确保预览区域可见
            const previewArea = document.getElementById('importPreviewArea');
            if (previewArea) {
                previewArea.classList.remove('d-none');
            }
            
            // 显示预览数据
            showCommentsPreview(data);
            
            // 保存文件路径
            const importFilePath = document.getElementById('importFilePath');
            if (importFilePath) {
                importFilePath.value = data.file_path;
            }
            
            // 显示确认导入按钮（只有当有匹配的学生且所有评语有效时才显示）
            if (confirmImportBtn) {
                // 检查是否有匹配到学生且所有评语都有效
                if (data.match_count > 0 && data.all_valid) {
                    confirmImportBtn.classList.remove('d-none');
                    confirmImportBtn.disabled = false;
                } else {
                    confirmImportBtn.classList.remove('d-none');
                    confirmImportBtn.disabled = true;
                    
                    if (data.match_count === 0) {
                        showNotification('没有匹配到任何学生，请检查Excel文件中的姓名是否正确', 'warning');
                    } else if (!data.all_valid) {
                        showNotification('部分评语超过260字限制，请修改后重试', 'warning');
                    }
                }
            }
        } else {
            showNotification(`预览失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        if (previewLoading) {
            previewLoading.classList.add('d-none');
        }
        showNotification(`预览失败: ${error.message}`, 'error');
        console.error('预览Excel数据失败:', error);
        
        // 清空文件选择
        fileInput.value = '';
        if (fileNameDisplay) {
            fileNameDisplay.textContent = '';
        }
    });
}

// 渲染导入预览数据
function renderImportPreview(data) {
    const previewArea = document.getElementById('importPreviewArea');
    const previewTableBody = document.getElementById('importPreviewTableBody');
    const importSummary = document.getElementById('importSummary');
    
    if (!previewArea || !previewTableBody || !importSummary) {
        showNotification('找不到预览区域元素', 'error');
        return;
    }
    
    // 清空预览表格
    previewTableBody.innerHTML = '';
    
    // 显示预览区域
    previewArea.classList.remove('d-none');
    
    // 渲染预览数据
    data.previews.forEach((item, index) => {
        const row = document.createElement('tr');
        
        if (!item.matched) {
            row.classList.add('table-warning');
        }
        
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${item.name || ''} ${item.matched ? '<i class="bx bx-check text-success"></i>' : '<i class="bx bx-x text-danger"></i>'}</td>
            <td>${item.comment || ''}</td>
        `;
        
        previewTableBody.appendChild(row);
    });
    
    // 更新导入摘要
    importSummary.textContent = `共发现${data.total_count}条评语记录，其中${data.match_count}条可以匹配到学生。`;
}

// 下载导入模板
function downloadImportTemplate() {
    try {
        // 检查ExcelJS是否可用
        if (typeof ExcelJS === 'undefined') {
            showNotification('ExcelJS库未加载，无法生成Excel文件', 'error');
            return;
        }
        
        // 创建一个工作簿
        const workbook = new ExcelJS.Workbook();
        const worksheet = workbook.addWorksheet('评语导入模板');
        
        // 添加表头
        worksheet.columns = [
            { header: '姓名', key: 'name', width: 15 },
            { header: '评语', key: 'comment', width: 60 }
        ];
        
        // 添加示例数据
        worksheet.addRow({ name: '张三', comment: '这是张三的评语示例，请替换为实际内容。' });
        worksheet.addRow({ name: '李四', comment: '这是李四的评语示例，请替换为实际内容。' });
        worksheet.addRow({ name: '王五', comment: '这是王五的评语示例，请替换为实际内容。' });
        
        // 设置表头样式
        worksheet.getRow(1).font = { bold: true };
        worksheet.getRow(1).fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFD3D3D3' }
        };
        
        // 导出Excel文件
        workbook.xlsx.writeBuffer().then(function(buffer) {
            const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = '评语导入模板.xlsx';
            a.click();
            
            URL.revokeObjectURL(url);
            showNotification('模板下载成功', 'success');
        }).catch(function(error) {
            console.error('生成Excel文件失败:', error);
            showNotification('生成Excel文件失败: ' + error.message, 'error');
        });
    } catch (error) {
        console.error('下载模板失败:', error);
        showNotification('下载模板失败: ' + error.message, 'error');
    }
}

// 显示评语导入预览
function showCommentsPreview(data) {
    if (!data || !data.previews || data.previews.length === 0) {
        showNotification('没有找到有效的评语数据', 'warning');
        return false;
    }

    // 保存文件路径到隐藏字段，用于确认导入时使用
    document.getElementById('importFilePath').value = data.file_path;
    
    // 构建预览表格
    let tableHtml = `
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th width="5%">#</th>
                        <th width="15%">姓名</th>
                        <th width="60%">评语</th>
                        <th width="10%">字数</th>
                        <th width="10%">状态</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // 添加每行评语数据
    for (let i = 0; i < data.previews.length; i++) {
        const preview = data.previews[i];
        const matchStatus = preview.matched ? 
            '<span class="badge bg-success">匹配</span>' : 
            '<span class="badge bg-danger">未匹配</span>';
        
        // 添加有效性状态标签 - 强调字数超出问题
        const validStatus = preview.valid ? 
            '<span class="badge bg-success">有效</span>' : 
            `<span class="badge bg-danger">超出字数(${preview.length}/260)</span>`;
        
        // 计算评语显示，超过100字符的截断显示（仅用于UI展示）
        let previewComment = preview.comment;
        if (previewComment.length > 100) {
            previewComment = previewComment.substring(0, 100) + "...";
        }
        
        tableHtml += `
            <tr class="${preview.matched ? '' : 'table-warning'} ${preview.valid ? '' : 'table-danger'}">
                <td>${i + 1}</td>
                <td>${preview.name}</td>
                <td>${previewComment.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</td>
                <td>${preview.length} / 260</td>
                <td>${matchStatus} ${validStatus}</td>
            </tr>
        `;
    }
    
    tableHtml += `
                </tbody>
            </table>
        </div>
    `;
    
    // 添加摘要信息，强调字数问题
    const allValid = data.all_valid;
    const validClass = allValid ? 'alert-success' : 'alert-danger';
    const validIcon = allValid ? 'bx-check-circle' : 'bx-error-circle';
    
    // 计算有效评语数量，如果服务器没有提供valid_count，则手动计算
    const validCount = data.valid_count !== undefined ? data.valid_count : 
        data.previews.filter(preview => preview.valid).length;
    
    tableHtml += `
        <div class="alert ${validClass}">
            <i class='bx ${validIcon}'></i> 
            共发现 ${data.total_count} 条评语记录，其中 ${data.match_count} 条可匹配到学生，
            ${validCount} 条在字数范围内有效(不超过260字)。
            ${!allValid ? '<strong>存在超出260字数限制的评语，请修改Excel文件后重新导入。系统不会自动截断评语。</strong>' : ''}
        </div>
    `;
    
    // 显示预览数据
    const previewContainer = document.getElementById('importPreviewContainer');
    if (previewContainer) {
        previewContainer.innerHTML = tableHtml;
        previewContainer.style.display = 'block';
    }
    
    // 控制确认按钮状态
    const confirmBtn = document.getElementById('confirmImportBtn');
    if (confirmBtn) {
        // 只有当所有评语都有效且至少匹配一条才可以启用按钮
        const enableButton = allValid && data.match_count > 0;
        confirmBtn.disabled = !enableButton;
        
        if (!enableButton) {
            if (data.match_count === 0) {
                confirmBtn.title = "没有任何评语匹配到学生，无法导入";
            } else if (!allValid) {
                confirmBtn.title = "存在评语超过字数限制(260字)，请修改后重试，系统不会自动截断评语";
            }
        } else {
            confirmBtn.title = "确认导入评语";
        }
    }
    
    // 更新摘要信息
    const importSummary = document.getElementById('importSummary');
    if (importSummary) {
        if (!allValid) {
            importSummary.innerHTML = `共发现 ${data.total_count} 条评语记录，其中 <strong class="text-danger">${data.total_count - validCount} 条超出字数限制</strong>，请修改后重试。`;
        } else {
            importSummary.textContent = `共发现 ${data.total_count} 条评语记录，其中 ${data.match_count} 条可匹配到学生。`;
        }
    }
    
    return true;
}

// 确认导入评语
function confirmImportComments() {
    const filePath = document.getElementById('importFilePath').value;
    // 检查并打印文件路径，帮助调试问题
    console.log('确认导入，文件路径:', filePath);
    
    if (!filePath) {
        showNotification('未找到导入文件路径', 'error');
        return;
    }
    
    // 评语导入模式设置为替换模式（默认）
    const appendMode = false;
    console.log('导入模式 - 替换原评语');
    
    // 禁用确认按钮
    const confirmImportBtn = document.getElementById('confirmImportBtn');
    if (confirmImportBtn) {
        confirmImportBtn.disabled = true;
        confirmImportBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 导入中...';
    }
    
    // 构建请求数据
    const requestData = {
        file_path: filePath,
        append_mode: appendMode
    };
    console.log('发送请求数据:', requestData);
    
    // 发送请求
    fetch('/api/confirm-import-comments', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        console.log('服务器响应状态:', response.status);
        return response.json().then(data => {
            if (!response.ok) {
                return Promise.reject({
                    status: response.status,
                    ...data
                });
            }
            return data;
        });
    })
    .then(data => {
        // 导入成功
        let message = `成功导入 ${data.success_count} 条评语`;
        if (data.error_count > 0) {
            message += `，但有 ${data.error_count} 条导入失败`;
        }
        
        // 关闭导入模态框
        const importModal = bootstrap.Modal.getInstance(document.getElementById('importCommentsModal'));
        if (importModal) {
            importModal.hide();
        }
        
        // 显示成功消息
        showNotification(message, data.status === 'ok' ? 'success' : 'warning');
        
        // 如果需要，刷新页面或重新加载评语数据
        if (data.success_count > 0) {
            // 延迟刷新页面，让用户先看到成功消息
            setTimeout(() => {
                location.reload();
            }, 1500);
        }
    })
    .catch(error => {
        console.error('确认导入评语失败:', error);
        
        // 还原确认按钮状态
        if (confirmImportBtn) {
            confirmImportBtn.disabled = false;
            confirmImportBtn.innerHTML = '确认导入';
        }
        
        // 显示错误消息
        let errorMessage = '导入失败: ';
        if (error.status) {
            errorMessage += `服务器返回 ${error.status}`;
            if (error.message) {
                errorMessage += ` - ${error.message}`;
            }
        } else {
            errorMessage += error.message || '未知错误';
        }
        
        showNotification(errorMessage, 'error');
    });
}

// 显示AI评语助手模态框
function showAICommentAssistant(studentId, studentName, classId) {
    console.log('打开AI海海:', studentId, studentName, classId);
    
    // 创建模态框HTML
    const modalId = 'aiCommentAssistantModal';
    let modalElement = document.getElementById(modalId);
    
    // 如果模态框不存在，创建新的
    if (!modalElement) {
        modalElement = document.createElement('div');
        modalElement.className = 'modal fade';
        modalElement.id = modalId;
        modalElement.tabIndex = '-1';
        modalElement.setAttribute('data-bs-backdrop', 'static');
        modalElement.setAttribute('aria-labelledby', `${modalId}Label`);
        modalElement.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content breathing-border">
                    <div class="modal-header" style="background: linear-gradient(135deg, #00c6ff, #0072ff); color: white;">
                        <h5 class="modal-title" id="${modalId}Label">
                            <i class='bx bx-bot'></i> AI海海 <small class="badge bg-light text-dark">DeepSeek</small> - <span id="aiModalStudentName"></span>
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <!-- 欢迎信息 -->
                        <div class="alert alert-info d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <i class='bx bx-info-circle me-2'></i> 
                                欢迎使用青柠半夏为您提供的Deepseek API，您也可以使用自己的API
                                <span class="badge bg-secondary ms-2" style="font-size: 0.8rem;">使用 DeepSeek Chat 模型</span>
                            </div>
                            <a href="#" class="btn btn-sm btn-outline-primary" id="openApiSettingsBtn">
                                <i class='bx bx-cog'></i> 修改
                            </a>
                        </div>
                        
                        <!-- AI评语生成设置 -->
                        <div class="card mb-3">
                            <div class="card-body">
                                <div class="alert alert-info mb-3">
                                    <i class='bx bx-bulb'></i> 请尽量填写以下学生特征信息，AI将根据这些信息生成<strong>个性化</strong>的评语，不同信息会生成不同风格的评语。
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <label class="form-label">学生个性特点 <span class="text-primary">*</span></label>
                                        <textarea class="form-control" id="aiPersonalityInput" rows="2" placeholder="例如：活泼开朗、喜欢思考、认真负责..."></textarea>
                                        <small class="form-text text-muted">填写学生的性格和个性特点</small>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">学习表现 <span class="text-primary">*</span></label>
                                        <textarea class="form-control" id="aiStudyInput" rows="2" placeholder="例如：数学成绩优秀、语文需要提高、认真听讲..."></textarea>
                                        <small class="form-text text-muted">填写学生的学习情况和成绩表现</small>
                                    </div>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <label class="form-label">爱好/特长 <span class="text-primary">*</span></label>
                                        <textarea class="form-control" id="aiHobbiesInput" rows="2" placeholder="例如：喜欢画画、擅长球类运动、对科学感兴趣..."></textarea>
                                        <small class="form-text text-muted">填写学生的兴趣爱好和特长</small>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">需要改进的方面 <span class="text-primary">*</span></label>
                                        <textarea class="form-control" id="aiImprovementInput" rows="2" placeholder="例如：注意力不集中、作业拖延、不爱发言..."></textarea>
                                        <small class="form-text text-muted">填写学生需要改进或提高的地方</small>
                                    </div>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-4">
                                        <label class="form-label">评语风格</label>
                                        <select class="form-select" id="aiStyleSelect">
                                            <option value="鼓励性的">鼓励性</option>
                                            <option value="严肃的">严肃</option>
                                            <option value="中肯的">中肯</option>
                                            <option value="温和的">温和</option>
                                            <option value="诗意的">诗意的</option>
                                            <option value="自然的">自然的</option>
                                        </select>
                                    </div>
                                    <div class="col-md-4">
                                        <label class="form-label">评语语气</label>
                                        <select class="form-select" id="aiToneSelect">
                                            <option value="正式的">正式</option>
                                            <option value="亲切的">亲切</option>
                                            <option value="严厉的">严厉</option>
                                            <option value="随和的">随和</option>
                                        </select>
                                    </div>
                                    <div class="col-md-4">
                                        <label class="form-label">最大字数</label>
                                        <input type="number" class="form-control" id="aiMaxLengthInput" value="260" min="200" max="260">
                                        <small class="form-text text-muted">系统将生成200-260字的评语</small>
                                    </div>
                                </div>
                                <div class="text-end">
                                    <button id="generateAICommentBtn" class="btn btn-primary">
                                        <i class='bx bx-magic'></i> 生成AI评语
                                    </button>
                                </div>
                            </div>
                        </div>
                        
                        <!-- AI评语预览 -->
                        <div id="aiCommentPreview" class="card" style="display: none; border: 2px solid #00c3ff; box-shadow: 0 0 10px rgba(0, 195, 255, 0.3);">
                            <div class="card-header bg-info text-white" style="background: linear-gradient(135deg, #00c6ff, #0072ff) !important;">
                                <h6 class="mb-0">
                                    <i class='bx bx-bot'></i> AI海海生成的评语 <small class="badge bg-light text-dark">DeepSeek</small>
                                </h6>
                            </div>
                            <div class="card-body">
                                <div id="aiCommentContent" class="mb-3 p-3 border rounded" style="min-height: 100px;"></div>
                                <div id="aiReasoningContent" class="mb-3 p-3 border rounded bg-light" style="min-height: 100px; display: none;"></div>
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <span class="badge bg-light text-dark" id="aiCommentLength">0/260</span> 字 
                                        <small class="text-muted">(最少200字)</small>
                                        <button class="btn btn-sm btn-outline-info ms-2" id="toggleReasoningBtn" style="display: none;">
                                            <i class='bx bx-brain'></i> 查看思考过程
                                        </button>
                                    </div>
                                    <div>
                                        <button class="btn btn-outline-secondary" id="generateAnotherBtn">
                                            <i class='bx bx-refresh'></i> 重新生成
                                        </button>
                                        <button class="btn btn-primary" id="useAICommentBtn">
                                            <i class='bx bx-check'></i> 使用此评语
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 加载中提示 -->
                        <div id="aiGeneratingIndicator" class="text-center p-4" style="display: none;">
                            <div class="spinner-border text-primary mb-3" role="status">
                                <span class="visually-hidden">正在生成...</span>
                            </div>
                            <p>正在生成评语，请稍候...</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        `;
        
        
        document.body.appendChild(modalElement);
        
        // 自定义确认对话框模板
        const confirmModalHTML = `
            <div class="modal fade" id="aiConfirmModal" tabindex="-1" aria-labelledby="aiConfirmModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="aiConfirmModalLabel">确认</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="aiConfirmModalBody">
                            <!-- 确认消息内容 -->
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="aiConfirmCancelBtn">取消</button>
                            <button type="button" class="btn btn-primary" id="aiConfirmOkBtn">确定</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', confirmModalHTML);
        
        // 绑定API设置按钮事件 - 现在打开模态框而不是跳转
        document.getElementById('openApiSettingsBtn').addEventListener('click', function(e) {
            e.preventDefault();
            showApiSettingsModal();
        });
        
        // 绑定模态框隐藏前的事件处理器
        modalElement.addEventListener('hide.bs.modal', function() {
            // 移除所有按钮的焦点，避免ARIA警告
            const focusableElements = modalElement.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            focusableElements.forEach(el => el.blur());
        });
    }
    
    // 保存当前学生ID和班级ID到模态框中的隐藏字段
    if (!modalElement.querySelector('#currentStudentId')) {
        const studentIdField = document.createElement('input');
        studentIdField.type = 'hidden';
        studentIdField.id = 'currentStudentId';
        modalElement.appendChild(studentIdField);
    }
    
    if (!modalElement.querySelector('#currentClassId')) {
        const classIdField = document.createElement('input');
        classIdField.type = 'hidden';
        classIdField.id = 'currentClassId';
        modalElement.appendChild(classIdField);
    }
    
    if (!modalElement.querySelector('#lastStudentId')) {
        const lastStudentIdField = document.createElement('input');
        lastStudentIdField.type = 'hidden';
        lastStudentIdField.id = 'lastStudentId';
        modalElement.appendChild(lastStudentIdField);
    }
    
    // 获取上一次学生ID
    const lastStudentId = document.getElementById('lastStudentId').value;
    
    // 检查是否切换了学生 - 只有当lastStudentId存在且与当前学生ID不同时才清空
    if (lastStudentId && lastStudentId !== studentId) {
        console.log('学生已切换，清空个性化信息');
        // 清空所有个性化输入框的值
        document.getElementById('aiPersonalityInput').value = '';
        document.getElementById('aiStudyInput').value = '';
        document.getElementById('aiHobbiesInput').value = '';
        document.getElementById('aiImprovementInput').value = '';
    }
    
    // 更新当前学生ID和班级ID
    document.getElementById('currentStudentId').value = studentId;
    document.getElementById('currentClassId').value = classId;
    
    // 先检查学生切换后再更新lastStudentId
    document.getElementById('lastStudentId').value = studentId;
    
    // 设置学生姓名
    document.getElementById('aiModalStudentName').textContent = studentName;
    
    // 清空生成的评语预览
    document.getElementById('aiCommentPreview').style.display = 'none';
    document.getElementById('aiCommentContent').textContent = '';
    
    // 清空思考过程和隐藏切换按钮
    const aiReasoningContent = document.getElementById('aiReasoningContent');
    const toggleReasoningBtn = document.getElementById('toggleReasoningBtn');
    if (aiReasoningContent) {
        aiReasoningContent.textContent = '';
        aiReasoningContent.style.display = 'none';
    }
    if (toggleReasoningBtn) {
        toggleReasoningBtn.style.display = 'none';
    }
    
    // 每次打开模态框时重新绑定事件，使用当前的学生ID和班级ID
    const generateBtn = document.getElementById('generateAICommentBtn');
    const generateAnotherBtn = document.getElementById('generateAnotherBtn');
    const useAICommentBtn = document.getElementById('useAICommentBtn');
    
    // 移除旧的事件监听器
    const newGenerateBtn = generateBtn.cloneNode(true);
    generateBtn.parentNode.replaceChild(newGenerateBtn, generateBtn);
    
    const newGenerateAnotherBtn = generateAnotherBtn ? generateAnotherBtn.cloneNode(true) : null;
    if (generateAnotherBtn && newGenerateAnotherBtn) {
        generateAnotherBtn.parentNode.replaceChild(newGenerateAnotherBtn, generateAnotherBtn);
    }
    
    const newUseAICommentBtn = useAICommentBtn ? useAICommentBtn.cloneNode(true) : null;
    if (useAICommentBtn && newUseAICommentBtn) {
        useAICommentBtn.parentNode.replaceChild(newUseAICommentBtn, useAICommentBtn);
    }
    
    // 添加新的事件监听器
    document.getElementById('generateAICommentBtn').addEventListener('click', function() {
        // 使用getCurrentStudentId()函数获取当前正在操作的学生ID和班级ID
        const currentId = document.getElementById('currentStudentId').value;
        const currentClassId = document.getElementById('currentClassId').value;
        console.log('生成评语按钮点击，当前学生ID:', currentId, '班级ID:', currentClassId);
        generateAIComment(currentId, currentClassId);
    });
    
    if (newGenerateAnotherBtn) {
        document.getElementById('generateAnotherBtn').addEventListener('click', function() {
            const currentId = document.getElementById('currentStudentId').value;
            const currentClassId = document.getElementById('currentClassId').value;
            console.log('重新生成按钮点击，当前学生ID:', currentId, '班级ID:', currentClassId);
            generateAIComment(currentId, currentClassId);
        });
    }
    
    if (newUseAICommentBtn) {
        document.getElementById('useAICommentBtn').addEventListener('click', function() {
            const currentId = document.getElementById('currentStudentId').value;
            const currentClassId = document.getElementById('currentClassId').value;
            console.log('使用评语按钮点击，当前学生ID:', currentId, '班级ID:', currentClassId);
            useAIComment(currentId, currentClassId);
        });
    }
    
    // 打开模态框
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

// 显示自定义确认对话框
function showCustomConfirm(message, okCallback) {
    const confirmModal = document.getElementById('aiConfirmModal');
    const confirmBody = document.getElementById('aiConfirmModalBody');
    const confirmOkBtn = document.getElementById('aiConfirmOkBtn');
    const confirmCancelBtn = document.getElementById('aiConfirmCancelBtn');
    
    if (!confirmModal || !confirmBody || !confirmOkBtn || !confirmCancelBtn) {
        // 降级到使用浏览器原生confirm
        return confirm(message);
    }
    
    // 设置消息内容
    confirmBody.textContent = message;
    
    // 创建一个Promise来处理用户响应
    return new Promise((resolve) => {
        // 确定按钮事件
        const okClickHandler = () => {
            confirmOkBtn.removeEventListener('click', okClickHandler);
            confirmCancelBtn.removeEventListener('click', cancelClickHandler);
            const bsModal = bootstrap.Modal.getInstance(confirmModal);
            if (bsModal) bsModal.hide();
            resolve(true);
            if (okCallback) okCallback();
        };
        
        // 取消按钮事件
        const cancelClickHandler = () => {
            confirmOkBtn.removeEventListener('click', okClickHandler);
            confirmCancelBtn.removeEventListener('click', cancelClickHandler);
            resolve(false);
        };
        
        // 模态框关闭事件
        const modalHiddenHandler = () => {
            confirmModal.removeEventListener('hidden.bs.modal', modalHiddenHandler);
            resolve(false);
        };
        
        // 绑定事件
        confirmOkBtn.addEventListener('click', okClickHandler);
        confirmCancelBtn.addEventListener('click', cancelClickHandler);
        confirmModal.addEventListener('hidden.bs.modal', modalHiddenHandler);
        
        // 显示模态框
        const modal = new bootstrap.Modal(confirmModal);
        modal.show();
    });
}

// 生成AI评语
async function generateAIComment(studentId, classId) {
    try {
        // 获取当前模态框
        const modal = document.getElementById('aiCommentAssistantModal');
        if (!modal) {
            throw new Error('找不到AI评语模态框');
        }

        // 获取所有输入值
        const style = modal.querySelector('#aiStyleSelect').value;
        const tone = modal.querySelector('#aiToneSelect').value;
        const maxLength = parseInt(modal.querySelector('#aiMaxLengthInput').value) || 5000; // 临时调整为1000字
        const personality = modal.querySelector('#aiPersonalityInput').value.trim();
        const studyPerformance = modal.querySelector('#aiStudyInput').value.trim();
        const hobbies = modal.querySelector('#aiHobbiesInput').value.trim();
        const improvement = modal.querySelector('#aiImprovementInput').value.trim();
        const additionalInstructions = '';

        // 检查是否填写了任何学生特征信息
        if (!personality && !studyPerformance && !hobbies && !improvement) {
            // 使用自定义确认对话框替代浏览器原生confirm
            const confirmed = await showCustomConfirm('您没有填写任何学生特征信息，这将导致生成的评语缺乏个性化。是否仍要继续？');
            if (!confirmed) {
                return; // 用户选择取消生成
            }
        }

        // 打印调试信息，检查是否获取了用户输入的特征信息
        console.log('学生特征信息:');
        console.log('- 个性特点:', personality);
        console.log('- 学习表现:', studyPerformance);
        console.log('- 爱好特长:', hobbies);
        console.log('- 需要改进:', improvement);
        console.log('- 评语风格:', style);
        console.log('- 评语语气:', tone);
        console.log('- 最大字数:', maxLength);

        // 显示加载状态
        const generateBtn = modal.querySelector('#generateAICommentBtn');
        const aiGeneratingIndicator = modal.querySelector('#aiGeneratingIndicator');
        const aiCommentPreview = modal.querySelector('#aiCommentPreview');
        
        // 保存原始按钮文本
        const originalText = generateBtn.textContent;
        
        // 更新UI状态 - 显示加载中
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 生成中...';
        
        if (aiGeneratingIndicator) {
            aiGeneratingIndicator.style.display = 'block';
        }
        
        if (aiCommentPreview) {
            aiCommentPreview.style.display = 'none';
        }

        // 使用传入的classId参数，而不是当前用户的班级ID
        console.log('使用传入的班级ID进行AI生成:', classId);

        // 发送请求
        let timeoutId = null;
        try {
            // 设置60秒超时提示
            timeoutId = setTimeout(() => {
                // 如果请求仍在进行，显示提示但不取消请求
                if (generateBtn.disabled) {
                    showNotification('评语生成可能需要较长时间，请耐心等待...', 'info', 5000);
                }
            }, 15000);
            
            const response = await fetch('/api/generate-comment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    student_id: studentId,
                    class_id: classId, // 使用传入的班级ID，而不是当前用户的班级ID
                    style: style,
                    tone: tone,
                    max_length: maxLength,
                    min_length: 200, // 添加最小字数参数，设置为200字
                    personality: personality,
                    study_performance: studyPerformance,
                    hobbies: hobbies,
                    improvement: improvement,
                    additional_instructions: additionalInstructions
                })
            });
            
            // 清除超时提示
            if (timeoutId) {
                clearTimeout(timeoutId);
                timeoutId = null;
            }

            // 检查是否是会话超时或权限错误
            if (response.status === 401 || response.status === 405) {
                console.error('会话已过期，需要重新登录');
                
                // 显示会话超时提示
                await showCustomConfirm('您的会话已超时，需要重新登录。点击确定将跳转到登录页面。');
                
                // 重定向到登录页面
                window.location.href = '/login?timeout=true';
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP错误! 状态: ${response.status}`);
            }

            const data = await response.json();
            console.log('评语生成结果:', data);

            if (data.status === 'ok') {
                // 显示生成的评语
                const aiCommentContent = modal.querySelector('#aiCommentContent');
                const aiReasoningContent = modal.querySelector('#aiReasoningContent');
                const aiCommentLength = modal.querySelector('#aiCommentLength');
                const toggleReasoningBtn = modal.querySelector('#toggleReasoningBtn');
                
                // 获取评语内容
                let commentText = data.comment;
                
                // 移除评语末尾的"（字数：xxx字）"格式
                commentText = commentText.replace(/（字数：\d+字）$/, '');
                
                // 获取思考过程和原始content字段
                const reasoningContent = data.reasoning_content || '';
                const contentField = data.content_field || '';
                
                // 保存思考过程内容
                if (aiReasoningContent && reasoningContent) {
                    aiReasoningContent.textContent = reasoningContent;
                    
                    // 如果有思考过程，显示切换按钮
                    if (toggleReasoningBtn) {
                        toggleReasoningBtn.style.display = 'inline-block';
                        
                        // 添加切换事件
                        toggleReasoningBtn.onclick = function() {
                            const isShowingReasoning = aiReasoningContent.style.display !== 'none';
                            
                            // 切换显示内容
                            aiCommentContent.style.display = isShowingReasoning ? 'block' : 'none';
                            aiReasoningContent.style.display = isShowingReasoning ? 'none' : 'block';
                            
                            // 更改按钮文本
                            this.innerHTML = isShowingReasoning ? 
                                '<i class="bx bx-brain"></i> 查看思考过程' : 
                                '<i class="bx bx-comment-detail"></i> 查看评语';
                        };
                    }
                } else if (toggleReasoningBtn) {
                    toggleReasoningBtn.style.display = 'none';
                }
                
                // 检查并截断超过字数限制的评语
                const maxLength = parseInt(modal.querySelector('#aiMaxLengthInput').value) || 260; // 临时调整为1000字
                const minLength = 200; // 设置最小字数为200
                
                if (commentText.length > maxLength) {
                    console.warn(`评语超过字数限制: ${commentText.length}/${maxLength}，截断至${maxLength}字`);
                    commentText = commentText.substring(0, maxLength);
                    // 显示截断提示
                    showNotification(`评语已自动截断至${maxLength}字`, 'warning');
                } else if (commentText.length < minLength) {
                    console.warn(`评语字数不足: ${commentText.length}字，最少需要${minLength}字`);
                    // 显示字数不足提示
                    showNotification(`评语字数仅有${commentText.length}字，低于${minLength}字的要求，建议重新生成`, 'warning');
                } else {
                    console.log(`评语字数符合要求: ${commentText.length}/${maxLength}字`);
                }
                
                if (aiCommentContent) {
                    aiCommentContent.textContent = commentText;
                }
                
                if (aiCommentLength) {
                    aiCommentLength.textContent = `${commentText.length}/${maxLength}`;
                    // 根据字数比例设置颜色
                    if (commentText.length < minLength) {
                        aiCommentLength.style.color = '#dc3545'; // 红色 - 字数不足
                    } else if (commentText.length / maxLength > 0.9) {
                        aiCommentLength.style.color = '#dc3545'; // 红色 - 接近上限
                    } else if (commentText.length / maxLength > 0.75) {
                        aiCommentLength.style.color = '#fd7e14'; // 橙色 - 适中偏多
                    } else {
                        aiCommentLength.style.color = '#28a745'; // 绿色 - 适中
                    }
                }
                
                if (aiCommentPreview) {
                    aiCommentPreview.style.display = 'block';
                }
                
                if (aiGeneratingIndicator) {
                    aiGeneratingIndicator.style.display = 'none';
                }

                showNotification('评语生成成功', 'success');
            } else {
                throw new Error(data.message || '生成评语失败');
            }
        } catch (error) {
            // 清除可能存在的超时提示
            if (timeoutId) {
                clearTimeout(timeoutId);
                timeoutId = null;
            }
            
            console.error('生成AI评语时出错:', error);
            
            // 获取模态框和元素
            const modal = document.getElementById('aiCommentAssistantModal');
            const aiGeneratingIndicator = modal?.querySelector('#aiGeneratingIndicator');
            
            // 隐藏加载指示器
            if (aiGeneratingIndicator) {
                aiGeneratingIndicator.style.display = 'none';
            }
            
            // 提供更友好的错误提示信息
            let errorMessage = error.message || '未知错误';
            
            if (errorMessage.includes('Read timed out') || errorMessage.includes('timeout')) {
                errorMessage = 'DeepSeek API请求超时，这可能是网络问题或服务器繁忙。请稍后再试。';
            } else if (errorMessage.includes('Network Error') || errorMessage.includes('Failed to fetch')) {
                errorMessage = '网络连接问题，请检查您的网络并稍后再试。';
            }
            
            showNotification('生成AI评语失败: ' + errorMessage, 'error');
        } finally {
            // 恢复生成按钮状态
            const modal = document.getElementById('aiCommentAssistantModal');
            const generateBtn = modal?.querySelector('#generateAICommentBtn');
            
            if (generateBtn) {
                generateBtn.disabled = false;
                generateBtn.innerHTML = '<i class="bx bx-magic"></i> 生成AI评语';
            }
        }
    } catch (error) {
        console.error('生成AI评语时出错:', error);
        showNotification('生成AI评语失败: ' + error.message, 'error');
    }
}

// 使用AI生成的评语
function useAIComment(studentId, classId) {
    console.log('使用AI评语:', studentId, classId);
    
    // 获取生成的评语内容
    const aiCommentContent = document.getElementById('aiCommentContent').textContent;
    if (!aiCommentContent) {
        showNotification('评语内容为空', 'error');
        return;
    }
    
    // 移除评语末尾的"（字数：xxx字）"格式
    let cleanedContent = aiCommentContent.replace(/（字数：\d+字）$/, '');
    
    // 检查评语字数是否超过限制
    const maxLength = 260;  // 修改为5000字 // 临时调整为5000字
    const minLength = 200;  // 设置最小字数为200字
    
    if (cleanedContent.length > maxLength) {
        showNotification(`评语超过${maxLength}字限制，请重新生成`, 'error');
        return;
    } else if (cleanedContent.length < minLength) {
        showNotification(`评语字数仅有${cleanedContent.length}字，低于${minLength}字的最小要求，请重新生成`, 'error');
        return;
    }
    
    // 使用传入的班级ID，而不是当前用户的班级ID
    console.log('保存评语使用的班级ID:', classId, '类型:', typeof classId);
    
    // 确认使用评语
    if (confirm('确定要使用此评语吗？这将替换现有评语。')) {
        // 记录班级ID类型和值
        console.log('保存评语使用的班级ID:', classId, '类型:', typeof classId);
        
        // 创建评语数据
        const commentData = {
            studentId,
            // 使用传入的班级ID，而不是当前用户的班级ID
            classId: classId,
            content: cleanedContent,
            // 添加标志表明这是AI评语
            isAIComment: true
        };
        
        // 显示保存中状态
        const useBtn = document.getElementById('useAICommentBtn');
        if (useBtn) {
            useBtn.disabled = true;
            useBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
        }
        
        // 发送到服务器
        fetch('/api/comments', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(commentData)
        })
        .then(response => {
            console.log('服务器响应状态:', response.status);
            
            // 检查是否是会话超时或权限错误
            if (response.status === 401 || response.status === 405) {
                console.error('会话已过期，需要重新登录');
                
                // 显示会话超时提示并重定向
                showCustomConfirm('您的会话已超时，需要重新登录。点击确定将跳转到登录页面。')
                .then((confirmed) => {
                    window.location.href = '/login?timeout=true';
                });
                
                throw new Error('会话已过期，请重新登录');
            }
            
            if (!response.ok) {
                return response.text().then(text => {
                    try {
                        // 尝试解析JSON
                        const errorData = JSON.parse(text);
                        throw new Error(errorData.message || `HTTP错误! 状态: ${response.status}`);
                    } catch (e) {
                        // 如果不是有效的JSON，返回原始错误
                        throw new Error(`HTTP错误! 状态: ${response.status}, 响应: ${text}`);
                    }
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('保存评语响应:', data);
            if (data.status === 'ok') {
                // 移除模态框中所有按钮的焦点，避免ARIA警告
                const modalElement = document.getElementById('aiCommentAssistantModal');
                const focusableElements = modalElement.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
                focusableElements.forEach(el => el.blur());
                
                // 关闭模态框
                const modal = bootstrap.Modal.getInstance(document.getElementById('aiCommentAssistantModal'));
                if (modal) {
                    modal.hide();
                }
                
                // 实时更新评语卡片
                updateCommentCard(studentId, {
                    content: cleanedContent,
                    updateDate: data.updateDate || new Date().toLocaleDateString()
                });
                
                showNotification('评语已保存', 'success');
                
                // 触发更新事件
                notifyStudentDataChanged();
            } else {
                throw new Error(data.message || '保存失败');
            }
        })
        .catch(error => {
            console.error('保存评语失败:', error);
            
            // 不显示会话超时重复提示
            if (!error.message.includes('会话已过期')) {
                showNotification(`保存评语失败: ${error.message}`, 'error');
            }
        })
        .finally(() => {
            // 恢复按钮状态
            if (useBtn) {
                useBtn.disabled = false;
                useBtn.innerHTML = '<i class="bx bx-check"></i> 使用此评语';
            }
        });
    }
}

// 创建并显示API设置模态框
function showApiSettingsModal() {
    console.log('显示API设置模态框');

    // 创建模态框HTML
    const modalId = 'apiSettingsModal';
    let modalElement = document.getElementById(modalId);
    
    // 如果模态框不存在，创建新的
    if (!modalElement) {
        modalElement = document.createElement('div');
        modalElement.className = 'modal fade';
        modalElement.id = modalId;
        modalElement.tabIndex = '-1';
        modalElement.setAttribute('data-bs-backdrop', 'static');
        modalElement.setAttribute('aria-labelledby', `${modalId}Label`);
        modalElement.innerHTML = `
            <div class="modal-dialog modal-md">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}Label">
                            <i class='bx bx-cog'></i> 设置 Deepseek API
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label for="apiDeepseekKey" class="form-label">Deepseek API密钥</label>
                            <div class="input-group">
                                <input type="password" class="form-control" id="apiDeepseekKey" placeholder="输入您的Deepseek API密钥">
                                <button class="btn btn-outline-secondary" type="button" id="apiToggleKeyBtn">
                                    <i class='bx bx-show'></i>
                                </button>
                            </div>
                            <div class="form-text">用于生成学生评语的API密钥，请在 <a href="https://www.deepseek.com/" target="_blank">DeepSeek官网</a> 获取</div>
                        </div>
                        
                        <!-- API状态显示 -->
                        <div id="apiStatusDisplay" class="alert alert-info mt-3" style="display: none;"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        <button type="button" class="btn btn-info" id="apiTestBtn">
                            <i class='bx bx-test-tube'></i> 测试连接
                        </button>
                        <button type="button" class="btn btn-primary" id="apiSaveBtn">
                            <i class='bx bx-save'></i> 保存设置
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modalElement);
        
        // 绑定API密钥显示/隐藏按钮事件
        document.getElementById('apiToggleKeyBtn').addEventListener('click', function() {
            const apiKeyInput = document.getElementById('apiDeepseekKey');
            const icon = this.querySelector('i');
            
            if (apiKeyInput.type === 'password') {
                apiKeyInput.type = 'text';
                icon.classList.remove('bx-show');
                icon.classList.add('bx-hide');
            } else {
                apiKeyInput.type = 'password';
                icon.classList.remove('bx-hide');
                icon.classList.add('bx-show');
            }
        });
        
        // 绑定测试按钮事件
        document.getElementById('apiTestBtn').addEventListener('click', function() {
            testApiConnection();
        });
        
        // 绑定保存按钮事件
        document.getElementById('apiSaveBtn').addEventListener('click', function() {
            saveApiSettings();
        });
    }
    
    // 加载当前的API密钥
    loadApiSettings();
    
    // 显示模态框
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

// 加载API设置
function loadApiSettings() {
    const apiKeyInput = document.getElementById('apiDeepseekKey');
    if (!apiKeyInput) return;
    
    // 从localStorage获取API密钥
    const apiKey = localStorage.getItem('deepseekApiKey') || '';
    apiKeyInput.value = apiKey;
    
    // 也可以从服务器加载，但这里我们使用本地存储的值
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok' && data.settings && data.settings.deepseek_api_key) {
                apiKeyInput.value = data.settings.deepseek_api_key;
            }
        })
        .catch(error => {
            console.error('加载API设置时出错:', error);
        });
}

// 测试API连接
function testApiConnection() {
    const apiKey = document.getElementById('apiDeepseekKey').value.trim();
    const statusDisplay = document.getElementById('apiStatusDisplay');
    
    if (!apiKey) {
        showApiStatus('请输入API密钥', 'warning');
        return;
    }
    
    // 显示加载状态
    showApiStatus('正在测试连接...', 'info');
    
    // 禁用测试按钮
    const testBtn = document.getElementById('apiTestBtn');
    if (testBtn) {
        testBtn.disabled = true;
        testBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 测试中...';
    }
    
    // 发送测试请求
    fetch('/api/test-deepseek', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: apiKey })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showApiStatus('API连接测试成功！', 'success');
        } else {
            showApiStatus(`测试失败: ${data.message || '未知错误'}`, 'danger');
        }
    })
    .catch(error => {
        console.error('测试API连接时出错:', error);
        showApiStatus(`测试出错: ${error.message}`, 'danger');
    })
    .finally(() => {
        // 恢复按钮状态
        if (testBtn) {
            testBtn.disabled = false;
            testBtn.innerHTML = '<i class="bx bx-test-tube"></i> 测试连接';
        }
    });
}

// 保存API设置
function saveApiSettings() {
    const apiKey = document.getElementById('apiDeepseekKey').value.trim();
    
    // 保存到localStorage
    localStorage.setItem('deepseekApiKey', apiKey);
    
    // 显示保存状态
    const statusDisplay = document.getElementById('apiStatusDisplay');
    
    // 禁用保存按钮
    const saveBtn = document.getElementById('apiSaveBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
    }
    
    // 发送到服务器
    fetch('/api/settings/deepseek', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: apiKey })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showApiStatus('API设置已保存', 'success');
            
            // 可以选择关闭模态框
            setTimeout(() => {
                const modal = bootstrap.Modal.getInstance(document.getElementById('apiSettingsModal'));
                if (modal) modal.hide();
            }, 1500);
        } else {
            showApiStatus(`保存失败: ${data.message || '未知错误'}`, 'danger');
        }
    })
    .catch(error => {
        console.error('保存API设置时出错:', error);
        showApiStatus(`保存失败: ${error.message}`, 'danger');
    })
    .finally(() => {
        // 恢复按钮状态
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bx bx-save"></i> 保存设置';
        }
    });
}

// 显示API状态
function showApiStatus(message, type) {
    const statusDisplay = document.getElementById('apiStatusDisplay');
    if (!statusDisplay) return;
    
    // 设置状态消息和样式
    statusDisplay.textContent = message;
    statusDisplay.style.display = 'block';
    
    // 设置样式
    statusDisplay.className = '';
    statusDisplay.classList.add('alert');
    
    switch (type) {
        case 'success':
            statusDisplay.classList.add('alert-success');
            break;
        case 'danger':
            statusDisplay.classList.add('alert-danger');
            break;
        case 'warning':
            statusDisplay.classList.add('alert-warning');
            break;
        default:
            statusDisplay.classList.add('alert-info');
    }
}// 文件结束
