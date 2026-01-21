/**
 * 智能成绩导入模块
 * 支持多班级、多学科、权限验证、详细错误提示
 */

console.log('smart-grade-import.js 开始加载...');

// 存储预览结果
let currentPreviewResult = null;

console.log('smart-grade-import.js 加载完成，准备定义函数...');

/**
 * 初始化智能成绩导入
 */
function initSmartGradeImport() {
    console.log('初始化智能成绩导入...');
    
    const fileInput = document.getElementById('gradeFile');
    const importArea = document.querySelector('.import-area');
    const downloadTemplateBtn = document.getElementById('downloadTemplateBtn');
    const confirmImportBtn = document.getElementById('confirmImportGrades');
    const importModal = document.getElementById('importGradesModal');
    
    // 文件选择事件
    if (fileInput) {
        console.log('绑定文件选择事件');
        fileInput.addEventListener('change', function(e) {
            console.log('文件选择事件触发');
            const file = e.target.files[0];
            if (file) {
                console.log('选择的文件:', file.name);
                handleFileSelected(file);
            }
        });
    } else {
        console.error('未找到文件输入框 #gradeFile');
    }
    
    // 拖放区域事件
    if (importArea) {
        console.log('绑定拖放事件');
        importArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.add('drag-over');
        });
        
        importArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('drag-over');
        });
        
        importArea.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelected(files[0]);
            }
        });
    }
    
    // 下载模板按钮
    if (downloadTemplateBtn) {
        console.log('绑定下载模板按钮');
        downloadTemplateBtn.addEventListener('click', function() {
            window.open('/api/grades/template', '_blank');
        });
    }
    
    // 确认导入按钮
    if (confirmImportBtn) {
        console.log('绑定确认导入按钮');
        confirmImportBtn.addEventListener('click', confirmSmartImport);
    }
    
    // 模态框关闭时重置
    if (importModal) {
        console.log('绑定模态框关闭事件');
        importModal.addEventListener('hidden.bs.modal', resetSmartImportModal);
    }
    
    console.log('智能成绩导入初始化完成');
}

/**
 * 处理文件选择
 */
function handleFileSelected(file) {
    console.log('文件已选择:', file.name);
    
    // 显示文件名
    const fileNameDisplay = document.getElementById('selectedFileName');
    if (fileNameDisplay) {
        fileNameDisplay.textContent = file.name;
        fileNameDisplay.style.color = '#28a745';
        fileNameDisplay.style.fontWeight = 'bold';
    }
    
    // 检查文件类型
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        showNotification('只支持Excel文件格式 (.xlsx, .xls)', 'error');
        return;
    }
    
    console.log('文件类型验证通过，准备预览...');
    
    // 自动触发预览
    setTimeout(() => {
        console.log('触发预览...');
        previewSmartImport();
    }, 100);
}

/**
 * 预览智能导入
 */
async function previewSmartImport() {
    const fileInput = document.getElementById('gradeFile');
    const previewContainer = document.getElementById('previewContent') || document.getElementById('importPreview');
    const confirmBtn = document.getElementById('confirmImportGrades');
    
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        showNotification('请先选择要导入的文件', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    
    // 显示加载状态
    if (previewContainer) {
        previewContainer.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">正在分析文件...</span>
                </div>
                <p class="mt-3 text-muted">正在分析文件，请稍候...</p>
            </div>
        `;
    }
    
    // 禁用确认按钮
    if (confirmBtn) {
        confirmBtn.disabled = true;
    }
    
    try {
        // 获取当前学期
        const semesterSelect = document.getElementById('semesterSelect');
        const importSemester = document.getElementById('importSemester');
        const semester = semesterSelect ? semesterSelect.textContent.trim() : (importSemester ? importSemester.value : '上学期');
        
        console.log('预览导入 - 学期:', semester);
        
        // 构建表单数据
        const formData = new FormData();
        formData.append('file', file);
        formData.append('semester', semester);
        
        // 发送预览请求
        const response = await fetch('/api/grades/preview-import', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        console.log('预览结果:', result);
        console.log('预览结果类型:', typeof result);
        console.log('预览结果的键:', Object.keys(result));
        
        if (result.status === 'ok') {
            // 保存预览结果 - 保存完整的result对象
            currentPreviewResult = result;
            console.log('已保存预览结果到 currentPreviewResult');
            console.log('currentPreviewResult:', currentPreviewResult);
            
            // 显示预览内容
            if (previewContainer) {
                previewContainer.innerHTML = result.html_preview;
            }
            
            // 启用确认按钮
            if (confirmBtn) {
                confirmBtn.disabled = false;
            }
            
            // 显示成功提示
            showNotification(result.message, 'success');
        } else {
            // 显示错误
            if (previewContainer) {
                displayPreviewError(result, previewContainer);
            }
            
            // 禁用确认按钮
            if (confirmBtn) {
                confirmBtn.disabled = true;
            }
            
            // 显示错误提示
            showNotification(result.message || '预览失败', 'error');
        }
        
    } catch (error) {
        console.error('预览导入时出错:', error);
        
        if (previewContainer) {
            previewContainer.innerHTML = `
                <div class="alert alert-danger">
                    <h5><i class="bx bx-error-circle"></i> 预览失败</h5>
                    <p>${error.message || '网络错误，请重试'}</p>
                </div>
            `;
        }
        
        if (confirmBtn) {
            confirmBtn.disabled = true;
        }
        showNotification('预览失败，请重试', 'error');
    }
}

/**
 * 显示预览错误
 */
function displayPreviewError(result, container) {
    let html = '<div class="alert alert-danger">';
    html += '<h5><i class="bx bx-error-circle"></i> 导入验证失败</h5>';
    html += `<p class="mb-3">${result.message}</p>`;
    
    // 显示错误列表
    if (result.errors && result.errors.length > 0) {
        html += '<h6>错误详情：</h6>';
        html += '<ul class="mb-0">';
        result.errors.forEach(error => {
            html += `<li>${error}</li>`;
        });
        html += '</ul>';
    }
    
    // 显示警告列表
    if (result.warnings && result.warnings.length > 0) {
        html += '<h6 class="mt-3">警告信息：</h6>';
        html += '<ul class="mb-0">';
        result.warnings.forEach(warning => {
            html += `<li>${warning}</li>`;
        });
        html += '</ul>';
    }
    
    html += '</div>';
    
    // 如果有HTML预览，也显示出来
    if (result.html_preview) {
        html += result.html_preview;
    }
    
    container.innerHTML = html;
}

/**
 * 确认智能导入
 */
async function confirmSmartImport() {
    console.log('========== 开始确认导入 ==========');
    console.log('currentPreviewResult:', currentPreviewResult);
    console.log('currentPreviewResult类型:', typeof currentPreviewResult);
    
    if (currentPreviewResult) {
        console.log('currentPreviewResult的键:', Object.keys(currentPreviewResult));
        console.log('status:', currentPreviewResult.status);
        console.log('preview_data:', currentPreviewResult.preview_data);
        console.log('file_path:', currentPreviewResult.file_path);
    }
    
    if (!currentPreviewResult) {
        console.error('currentPreviewResult 为空！');
        showNotification('请先预览导入数据', 'warning');
        return;
    }
    
    if (currentPreviewResult.status !== 'ok') {
        console.error('预览状态不是ok:', currentPreviewResult.status);
        showNotification('当前预览数据无效，无法导入', 'error');
        return;
    }
    
    const confirmBtn = document.getElementById('confirmImportGrades');
    const originalText = confirmBtn.innerHTML;
    
    // 显示加载状态
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>正在导入...';
    
    try {
        console.log('准备发送确认导入请求...');
        
        // 直接发送整个预览结果
        const requestData = {
            preview_result: currentPreviewResult
        };
        
        console.log('请求数据:', requestData);
        console.log('请求数据JSON:', JSON.stringify(requestData, null, 2));
        
        // 发送确认导入请求
        const response = await fetch('/api/grades/confirm-import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        console.log('响应状态:', response.status);
        console.log('响应头:', response.headers);
        
        const result = await response.json();
        console.log('响应结果:', result);
        
        if (result.status === 'ok') {
            // 导入成功
            console.log('✅ 导入成功！');
            showNotification(result.message, 'success');
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('importGradesModal'));
            if (modal) {
                modal.hide();
            }
            
            // 重新加载成绩列表
            if (typeof loadGrades === 'function') {
                setTimeout(() => {
                    loadGrades();
                }, 500);
            }
            
            // 重置导入状态
            resetSmartImportModal();
            
        } else {
            // 导入失败
            console.error('❌ 导入失败:', result.message);
            showNotification(result.message || '导入失败', 'error');
            
            // 恢复按钮状态
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
        }
        
    } catch (error) {
        console.error('❌ 确认导入时出错:', error);
        console.error('错误堆栈:', error.stack);
        showNotification('导入失败：' + (error.message || '网络错误'), 'error');
        
        // 恢复按钮状态
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalText;
    }
    
    console.log('========== 确认导入结束 ==========');
}

/**
 * 重置智能导入模态框
 */
function resetSmartImportModal() {
    // 清空文件选择
    const fileInput = document.getElementById('gradeFile');
    if (fileInput) {
        fileInput.value = '';
    }
    
    // 清空文件名显示
    const fileNameDisplay = document.getElementById('selectedFileName');
    if (fileNameDisplay) {
        fileNameDisplay.textContent = '';
    }
    
    // 清空预览容器
    const previewContainer = document.getElementById('previewContent') || document.getElementById('importPreview');
    if (previewContainer) {
        previewContainer.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="bx bx-upload" style="font-size: 48px;"></i>
                <p class="mt-3">请选择Excel文件进行预览</p>
            </div>
        `;
    }
    
    // 禁用确认按钮
    const confirmBtn = document.getElementById('confirmImportGrades');
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '确认导入';
    }
    
    // 清空预览结果
    currentPreviewResult = null;
}

/**
 * 显示通知
 */
function showNotification(message, type = 'info') {
    // 如果页面有showNotification函数，使用它
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
        return;
    }
    
    // 否则使用简单的alert
    if (type === 'error') {
        alert('错误：' + message);
    } else if (type === 'success') {
        alert('成功：' + message);
    } else {
        alert(message);
    }
}

// 导出函数供外部使用
if (typeof window !== 'undefined') {
    window.initSmartGradeImport = initSmartGradeImport;
    window.previewSmartImport = previewSmartImport;
    window.confirmSmartImport = confirmSmartImport;
    window.resetSmartImportModal = resetSmartImportModal;
    
    console.log('智能导入函数已导出到window对象');
    console.log('- initSmartGradeImport:', typeof window.initSmartGradeImport);
    console.log('- previewSmartImport:', typeof window.previewSmartImport);
    console.log('- confirmSmartImport:', typeof window.confirmSmartImport);
    console.log('- resetSmartImportModal:', typeof window.resetSmartImportModal);
}
