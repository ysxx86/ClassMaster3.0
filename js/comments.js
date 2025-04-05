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

document.addEventListener('DOMContentLoaded', function() {
    console.log('评语管理页面初始化...');
    
    // 初始化
    initialize();
    
    // 启动DOM监控
    monitorDOMChanges();
});

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
    
    const commentContent = comment ? comment.content : '暂无评语';
    const updateDate = comment ? comment.updateDate : '';
    
    // 评语字数
    const commentLength = commentContent.length;
    
    // 设置字数的颜色 - 从绿色(接近0字)渐变到红色(接近260字)
    const maxLength = 260;
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
    const maxLength = 200;
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
        contentElement.textContent = comment.content || '暂无评语';
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

// 导出评语为PDF
function exportComments() {
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
        const maxLength = 260; // 最大字数限制
        const count = commentText.value.length;
        charCount.textContent = `${count}/${maxLength}`;
        console.log(`当前字数: ${count}/${maxLength}`);
        
        // 限制输入字数
        if (count > maxLength) {
            commentText.value = commentText.value.substring(0, maxLength);
            charCount.textContent = `${maxLength}/${maxLength}`;
            console.log(`已截断至最大字数: ${maxLength}`);
        }
        
        // 根据字数改变颜色提示 - 从绿色(接近0字)渐变到红色(接近260字)
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
        const maxLength = 260; // 最大字数限制
        const count = batchCommentText.value.length;
        batchCharCount.textContent = `${count}/${maxLength}`;
        
        // 限制输入字数
        if (count > maxLength) {
            batchCommentText.value = batchCommentText.value.substring(0, maxLength);
            batchCharCount.textContent = `${maxLength}/${maxLength}`;
        }
        
        // 根据字数改变颜色提示 - 从绿色(接近0字)渐变到红色(接近260字)
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
    const toastContainer = document.getElementById('toastContainer');
    if (toastContainer) {
        toastContainer.appendChild(toast);
    } else {
        // 如果没有容器，创建一个并添加到body
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
        container.appendChild(toast);
    }
    
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

// 初始化评语数据
function initialize() {
    console.log('初始化评语模块...');
    
    // 获取当前用户班级ID
    fetchCurrentUserClassId();
    
    // 加载评语数据
    initCommentList();
    
    // 绑定事件监听器
    bindEventListeners();
    
    // 设置DOM变更监听
    monitorDOMChanges();
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
    console.log('绑定事件监听器...');
    
    
    
    // 导出评语按钮事件
    const exportCommentsBtn = document.getElementById('exportCommentsBtn');
    if (exportCommentsBtn) {
        exportCommentsBtn.addEventListener('click', function() {
            console.log('导出评语按钮被点击');
            exportComments();
        });
    } else {
        console.error('找不到导出评语按钮');
    }
    
    // 打印预览按钮事件
    const printPreviewBtn = document.getElementById('printPreviewBtn');
    if (printPreviewBtn) {
        printPreviewBtn.addEventListener('click', function() {
            console.log('打印预览按钮被点击');
            showPrintPreview();
        });
    } else {
        console.error('找不到打印预览按钮');
    }
    
    
    
    
    
    
    
    // 监听评语文本框输入事件，更新字数统计
    const commentText = document.getElementById('commentText');
    if (commentText) {
        commentText.addEventListener('input', function() {
            updateCharCount();
        });
    } else {
        console.error('找不到评语文本框');
    }
    
    // 搜索输入事件
    const searchInput = document.getElementById('searchStudent');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            console.log('搜索框输入:', this.value);
            filterComments(this.value);
        });
    } else {
        console.error('找不到搜索输入框');
    }
    
    
   
    
    console.log('事件监听器绑定完成');
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
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <label class="form-label">学生个性特点</label>
                                        <textarea class="form-control" id="aiPersonalityInput" rows="2" placeholder="例如：活泼开朗、喜欢思考、认真负责..."></textarea>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">学习表现</label>
                                        <textarea class="form-control" id="aiStudyInput" rows="2" placeholder="例如：数学成绩优秀、语文需要提高、认真听讲..."></textarea>
                                    </div>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <label class="form-label">爱好/特长</label>
                                        <textarea class="form-control" id="aiHobbiesInput" rows="2" placeholder="例如：喜欢画画、擅长球类运动、对科学感兴趣..."></textarea>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">需要改进的方面</label>
                                        <textarea class="form-control" id="aiImprovementInput" rows="2" placeholder="例如：注意力不集中、作业拖延、不爱发言..."></textarea>
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
                                        <input type="number" class="form-control" id="aiMaxLengthInput" value="260" min="50" max="260">
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
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <span class="badge bg-light text-dark" id="aiCommentLength">0/260</span> 字
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
    
    // 更新当前学生ID和班级ID
    document.getElementById('currentStudentId').value = studentId;
    document.getElementById('currentClassId').value = classId;
    
    // 设置学生姓名
    document.getElementById('aiModalStudentName').textContent = studentName;
    
    // 清空生成的评语预览
    document.getElementById('aiCommentPreview').style.display = 'none';
    document.getElementById('aiCommentContent').textContent = '';
    
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
        const maxLength = parseInt(modal.querySelector('#aiMaxLengthInput').value);
        const personality = modal.querySelector('#aiPersonalityInput').value;
        const studyPerformance = modal.querySelector('#aiStudyInput').value;
        const hobbies = modal.querySelector('#aiHobbiesInput').value;
        const improvement = modal.querySelector('#aiImprovementInput').value;
        const additionalInstructions = '';

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
                personality: personality,
                study_performance: studyPerformance,
                hobbies: hobbies,
                improvement: improvement,
                additional_instructions: additionalInstructions
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP错误! 状态: ${response.status}`);
        }

        const data = await response.json();
        console.log('评语生成结果:', data);

        if (data.status === 'ok') {
            // 显示生成的评语
            const aiCommentContent = modal.querySelector('#aiCommentContent');
            const aiCommentLength = modal.querySelector('#aiCommentLength');
            
            if (aiCommentContent) {
                aiCommentContent.textContent = data.comment;
            }
            
            if (aiCommentLength) {
                aiCommentLength.textContent = `${data.comment.length}/${maxLength}`;
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
        console.error('生成AI评语时出错:', error);
        
        // 获取模态框和元素
        const modal = document.getElementById('aiCommentAssistantModal');
        const aiGeneratingIndicator = modal?.querySelector('#aiGeneratingIndicator');
        
        // 隐藏加载指示器
        if (aiGeneratingIndicator) {
            aiGeneratingIndicator.style.display = 'none';
        }
        
        showNotification('生成AI评语失败: ' + error.message, 'error');
    } finally {
        // 恢复生成按钮状态
        const modal = document.getElementById('aiCommentAssistantModal');
        const generateBtn = modal?.querySelector('#generateAICommentBtn');
        
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="bx bx-magic"></i> 生成AI评语';
        }
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
            content: aiCommentContent,
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
                    content: aiCommentContent,
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
            showNotification(`保存评语失败: ${error.message}`, 'error');
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
