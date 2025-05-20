// @charset UTF-8
// 初始化页面时加载信息
document.addEventListener('DOMContentLoaded', function() {
    // 创建样式元素
    const style = document.createElement('style');
    style.textContent = `
        .toast {
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }
        .toast.show {
            opacity: 1;
        }
    `;
    document.head.appendChild(style);
    
    // 初始化设置
    loadSettings();
    
    // 绑定事件监听
    bindEventListeners();
    
    // 检查是否需要滚动到Deepseek API设置
    if (sessionStorage.getItem('scrollToDeepseekApi') === 'true') {
        // 清除会话存储变量
        sessionStorage.removeItem('scrollToDeepseekApi');
        
        // 激活安全设置选项卡（假设Deepseek API设置在此选项卡下）
        setTimeout(() => {
            // 找到API设置所在的卡片
            const apiCard = document.querySelector('.card-header:has(h5:contains("AI评语设置"))') || 
                            document.querySelector('h5:contains("AI评语设置")').closest('.card');
            
            if (apiCard) {
                // 滚动到API设置卡片
                apiCard.scrollIntoView({ behavior: 'smooth' });
                
                // 高亮显示API设置卡片
                apiCard.classList.add('border-primary');
                apiCard.style.boxShadow = '0 0 15px rgba(52, 152, 219, 0.6)';
                
                // 高亮显示DeepseekApiKey输入框
                const apiKeyInput = document.getElementById('deepseekApiKey');
                if (apiKeyInput) {
                    apiKeyInput.focus();
                    apiKeyInput.classList.add('border-primary');
                }
                
                // 3秒后移除高亮效果
                setTimeout(() => {
                    apiCard.classList.remove('border-primary');
                    apiCard.style.boxShadow = '';
                    if (apiKeyInput) {
                        apiKeyInput.classList.remove('border-primary');
                    }
                }, 3000);
            }
        }, 500); // 延迟半秒确保DOM已完全加载
    }
});

// 加载设置
function loadSettings() {
    // 获取保存的API设置
    const apiKey = localStorage.getItem('deepseekApiKey') || '';
    const apiKeyInput = document.getElementById('deepseekApiKey');
    if (apiKeyInput) {
        apiKeyInput.value = apiKey;
    }
    
    // 获取保存的AI评语设置
    const commentLength = localStorage.getItem('commentLength') || 'medium';
    const commentStyle = localStorage.getItem('commentStyle') || 'encouraging';
    const commentLengthSelect = document.getElementById('commentLength');
    const commentStyleSelect = document.getElementById('commentStyle');
    
    if (commentLengthSelect) {
        commentLengthSelect.value = commentLength;
    }
    
    if (commentStyleSelect) {
        commentStyleSelect.value = commentStyle;
    }
    
    // 获取保存的重点关注设置
    const focusSettings = JSON.parse(localStorage.getItem('focusSettings') || '{"academic":true,"behavior":true,"activity":true,"suggestion":true}');
    
    const focusAcademic = document.getElementById('focusAcademic');
    const focusBehavior = document.getElementById('focusBehavior');
    const focusActivity = document.getElementById('focusActivity');
    const focusSuggestion = document.getElementById('focusSuggestion');
    
    if (focusAcademic) focusAcademic.checked = focusSettings.academic !== false;
    if (focusBehavior) focusBehavior.checked = focusSettings.behavior !== false;
    if (focusActivity) focusActivity.checked = focusSettings.activity !== false;
    if (focusSuggestion) focusSuggestion.checked = focusSettings.suggestion !== false;

    // 加载轮播设置
    getCarouselSettings();
    
    // 加载学期设置
    loadSemesterSettings();
}

// 绑定事件监听
function bindEventListeners() {
    // 保存DeepSeek API设置
    const saveDeepseekApiBtn = document.getElementById('saveDeepseekApiBtn');
    if (saveDeepseekApiBtn) {
        saveDeepseekApiBtn.addEventListener('click', saveDeepseekApiSettings);
    }
    
    // 测试DeepSeek API连接
    const testDeepseekApiBtn = document.getElementById('testDeepseekApiBtn');
    if (testDeepseekApiBtn) {
        testDeepseekApiBtn.addEventListener('click', function() {
            const apiKey = document.getElementById('deepseekApiKey').value.trim();
            
            if (!apiKey) {
                showToast('请先输入API密钥', 'warning');
                return;
            }
            
            // 测试API连接
            const apiStatus = document.getElementById('apiStatus');
            if (apiStatus) {
                apiStatus.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> 正在测试连接...';
                apiStatus.className = 'api-status mt-2';
                apiStatus.style.display = 'block';
                apiStatus.style.backgroundColor = '#f8f9fa';
            }
            
            // 发送测试请求到服务器
            fetch('/api/test-deepseek-api', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ api_key: apiKey })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    if (apiStatus) {
                        apiStatus.innerHTML = '<i class="bx bx-check-circle"></i> 连接成功';
                        apiStatus.className = 'api-status success mt-2';
                    }
                    showToast('API连接测试成功', 'success');
                } else {
                    if (apiStatus) {
                        apiStatus.innerHTML = `<i class="bx bx-error-circle"></i> 连接失败: ${data.message}`;
                        apiStatus.className = 'api-status error mt-2';
                    }
                    showToast('API连接测试失败: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('测试API连接出错:', error);
                if (apiStatus) {
                    apiStatus.innerHTML = '<i class="bx bx-error-circle"></i> 连接错误: 服务器请求失败';
                    apiStatus.className = 'api-status error mt-2';
                }
                showToast('测试API连接出错: 无法连接到服务器', 'error');
            });
        });
    }

    // 保存AI评语设置
    const saveAiSettingsBtn = document.getElementById('saveAiSettingsBtn');
    if (saveAiSettingsBtn) {
        saveAiSettingsBtn.addEventListener('click', saveAiCommentSettings);
    }

    // 保存学期设置
    const saveSemesterSettingsBtn = document.getElementById('saveSemesterSettingsBtn');
    if (saveSemesterSettingsBtn) {
        saveSemesterSettingsBtn.addEventListener('click', saveSemesterSettings);
    }

    // 切换DeepSeek API密钥显示/隐藏
    const toggleDeepseekKeyBtn = document.getElementById('toggleDeepseekKeyBtn');
    if (toggleDeepseekKeyBtn) {
        toggleDeepseekKeyBtn.addEventListener('click', function() {
            const apiKeyInput = document.getElementById('deepseekApiKey');
            if (apiKeyInput) {
                if (apiKeyInput.type === 'password') {
                    apiKeyInput.type = 'text';
                    toggleDeepseekKeyBtn.innerHTML = '<i class="bx bx-hide"></i>';
                } else {
                    apiKeyInput.type = 'password';
                    toggleDeepseekKeyBtn.innerHTML = '<i class="bx bx-show"></i>';
                }
            }
        });
    }

    // 设置版权年份
    const copyrightYearElem = document.getElementById('copyrightYear');
    if (copyrightYearElem) {
        copyrightYearElem.textContent = new Date().getFullYear();
    }
    
    // 设置最后更新时间
    const lastUpdateTimeElem = document.getElementById('lastUpdateTime');
    if (lastUpdateTimeElem) {
        // 获取最后更新时间，如果没有则使用当前时间
        const lastUpdate = localStorage.getItem('lastUpdateTime') || new Date().toISOString();
        lastUpdateTimeElem.textContent = new Date(lastUpdate).toLocaleDateString();
    }
}

// 添加通知样式
function addToastStyles() {
    const style = document.createElement('style');
    style.textContent = `
        #toastContainer {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
        }
        #toastContainer .toast {
            margin-bottom: 10px;
            opacity: 0;
            transition: opacity 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-radius: 6px;
            overflow: hidden;
        }
    `;
    document.head.appendChild(style);
}

// 显示toast通知
function showToast(message, type = 'info') {
    // 创建通知容器
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        document.body.appendChild(toastContainer);
    }
    
    // 创建新的toast元素
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.minWidth = '300px';
    
    // 设置背景颜色和图标
    let backgroundColor, icon;
    switch (type) {
        case 'success':
            backgroundColor = '#4caf50';
            icon = 'bx-check-circle';
            break;
        case 'error':
            backgroundColor = '#f44336';
            icon = 'bx-error-circle';
            break;
        case 'warning':
            backgroundColor = '#ff9800';
            icon = 'bx-error';
            break;
        default:
            backgroundColor = '#2196f3';
            icon = 'bx-info-circle';
    }
    
    // 设置toast内容
    toast.innerHTML = `
        <div style="display: flex; align-items: center; padding: 12px 15px; color: white; background-color: ${backgroundColor};">
            <i class='bx ${icon}' style="font-size: 20px; margin-right: 10px;"></i>
            <div>${message}</div>
        </div>
    `;
    
    // 添加到容器
    toastContainer.appendChild(toast);
    
    // 显示通知
    setTimeout(() => {
        toast.style.opacity = '1';
    }, 10);
    
    // 3秒后自动关闭
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300);
    }, 3000);
}

// 加载轮播设置
function getCarouselSettings() {
    // Implementation of getCarouselSettings function
}

// 加载学期设置
function loadSemesterSettings() {
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                const settings = data.settings || {};
                
                // 设置学年
                if (settings.school_year) {
                    document.getElementById('schoolYearSetting').value = settings.school_year;
                }
                
                // 设置学期
                if (settings.semester) {
                    document.getElementById('semesterSetting').value = settings.semester;
                }
                
                // 设置开学时间
                if (settings.start_date) {
                    document.getElementById('startDateSetting').value = settings.start_date;
                }
            }
        })
        .catch(error => {
            console.error('获取学期设置失败:', error);
            showToast('error', '获取学期设置失败: ' + error.message);
        });
}

// 保存学期设置
function saveSemesterSettings() {
    // 获取表单数据
    const schoolYear = document.getElementById('schoolYearSetting').value;
    const semester = document.getElementById('semesterSetting').value;
    const startDate = document.getElementById('startDateSetting').value;
    
    // 验证数据
    if (!schoolYear || !semester || !startDate) {
        showToast('error', '请填写所有必填字段');
        return;
    }
    
    // 验证学年格式
    const yearPattern = /^\d{4}-\d{4}$/;
    if (!yearPattern.test(schoolYear)) {
        showToast('error', '学年格式不正确，应为YYYY-YYYY，例如：2024-2025');
        return;
    }
    
    // 显示保存中状态
    const statusElement = document.getElementById('semesterSettingsStatus');
    if (statusElement) {
        statusElement.innerHTML = '<div class="alert alert-info">正在保存设置...</div>';
    }
    
    // 禁用保存按钮
    const saveBtn = document.getElementById('saveSemesterSettingsBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
    }
    
    // 发送请求
    fetch('/api/settings/semester', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            school_year: schoolYear,
            semester: semester,
            start_date: startDate
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            if (statusElement) {
                statusElement.innerHTML = '<div class="alert alert-success">设置已保存</div>';
            }
            showToast('success', '学期设置已保存');
        } else {
            if (statusElement) {
                statusElement.innerHTML = `<div class="alert alert-danger">保存失败: ${data.message}</div>`;
            }
            showToast('error', data.message || '保存设置失败');
        }
    })
    .catch(error => {
        console.error('保存学期设置失败:', error);
        if (statusElement) {
            statusElement.innerHTML = `<div class="alert alert-danger">保存失败: ${error.message}</div>`;
        }
        showToast('error', '保存设置失败: ' + error.message);
    })
    .finally(() => {
        // 恢复按钮状态
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bx bx-save"></i> 保存设置';
        }
        
        // 3秒后清除状态消息
        setTimeout(() => {
            if (statusElement) {
                statusElement.innerHTML = '';
            }
        }, 3000);
    });
}

// 保存DeepSeek API设置
function saveDeepseekApiSettings() {
    const apiKey = document.getElementById('deepseekApiKey').value.trim();
    
    // 显示保存中状态
    const statusElement = document.getElementById('apiStatus');
    if (statusElement) {
        statusElement.innerHTML = '<div class="alert alert-info">正在保存设置...</div>';
    }
    
    // 禁用保存按钮
    const saveBtn = document.getElementById('saveDeepseekApiBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
    }
    
    // 发送请求
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
            if (statusElement) {
                statusElement.innerHTML = '<div class="alert alert-success">设置已保存</div>';
            }
            showToast('success', 'DeepSeek API设置已保存');
        } else {
            if (statusElement) {
                statusElement.innerHTML = `<div class="alert alert-danger">保存失败: ${data.message}</div>`;
            }
            showToast('error', data.message || '保存设置失败');
        }
    })
    .catch(error => {
        console.error('保存API设置失败:', error);
        if (statusElement) {
            statusElement.innerHTML = `<div class="alert alert-danger">保存失败: ${error.message}</div>`;
        }
        showToast('error', '保存设置失败: ' + error.message);
    })
    .finally(() => {
        // 恢复按钮状态
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bx bx-save"></i> 保存设置';
        }
        
        // 3秒后清除状态消息
        setTimeout(() => {
            if (statusElement) {
                statusElement.innerHTML = '';
            }
        }, 3000);
    });
}

// 保存AI评语设置
function saveAiCommentSettings() {
    // 获取设置
    const commentLength = document.getElementById('commentLength').value;
    const commentStyle = document.getElementById('commentStyle').value;
    const focusAcademic = document.getElementById('focusAcademic').checked;
    const focusBehavior = document.getElementById('focusBehavior').checked;
    const focusActivity = document.getElementById('focusActivity').checked;
    const focusSuggestion = document.getElementById('focusSuggestion').checked;
    
    // 构建设置对象
    const settings = {
        length: commentLength,
        style: commentStyle,
        focus_academic: focusAcademic,
        focus_behavior: focusBehavior,
        focus_activity: focusActivity,
        focus_suggestion: focusSuggestion
    };
    
    // 显示保存中状态
    const statusElement = document.getElementById('aiSettingsStatus');
    if (statusElement) {
        statusElement.innerHTML = '<div class="alert alert-info">正在保存设置...</div>';
    }
    
    // 禁用保存按钮
    const saveBtn = document.getElementById('saveAiSettingsBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
    }
    
    // 发送请求
    fetch('/api/settings/ai-comments', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            if (statusElement) {
                statusElement.innerHTML = '<div class="alert alert-success">设置已保存</div>';
            }
            showToast('success', 'AI评语设置已保存');
        } else {
            if (statusElement) {
                statusElement.innerHTML = `<div class="alert alert-danger">保存失败: ${data.message}</div>`;
            }
            showToast('error', data.message || '保存设置失败');
        }
    })
    .catch(error => {
        console.error('保存AI评语设置失败:', error);
        if (statusElement) {
            statusElement.innerHTML = `<div class="alert alert-danger">保存失败: ${error.message}</div>`;
        }
        showToast('error', '保存设置失败: ' + error.message);
    })
    .finally(() => {
        // 恢复按钮状态
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bx bx-save"></i> 保存设置';
        }
        
        // 3秒后清除状态消息
        setTimeout(() => {
            if (statusElement) {
                statusElement.innerHTML = '';
            }
        }, 3000);
    });
} 