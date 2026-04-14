// DOM 元素
const userTable = document.getElementById('userList');
const userTableEmpty = document.getElementById('userTableEmpty');
const userTableLoading = document.getElementById('userTableLoading');
const toastNotification = document.getElementById('toastNotification');
const toastMessage = document.getElementById('toastMessage');
const toast = new bootstrap.Toast(toastNotification);

// 立即执行权限检查，确保只有管理员可访问此页面
(function checkAdminPermission() {
    // 立即重定向到首页的函数
    function redirectToHome() {
        try {
            if (window.top !== window.self) {
                // 如果在iframe中
                window.top.location.href = '/';
            } else {
                // 如果是直接访问
                window.location.href = '/';
            }
        } catch (e) {
            // 如果无法访问top（例如因为跨域限制），则尝试使用当前窗口重定向
            window.location.href = '/';
        }
    }

    // 向服务器请求当前用户信息
    fetch('/api/current-user')
        .then(response => {
            if (response.status !== 200) {
                throw new Error('验证权限失败');
            }
            return response.json();
        })
        .then(data => {
            if (data.status !== 'ok' || !data.user || !data.user.is_admin) {
                // 如果不是管理员，重定向到首页
                redirectToHome();
            }
        })
        .catch(error => {
            console.error('权限验证失败:', error);
            // 出错同样重定向到首页
            redirectToHome();
        });
})();

// 格式化日期时间
function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return '';
    const date = new Date(dateTimeStr);
    if (isNaN(date.getTime())) {
        // 如果是数据库原始格式，直接返回
        return dateTimeStr;
    }
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 显示提示消息
function showToast(message, type = 'success') {
    toastMessage.textContent = message;
    toastNotification.classList.remove('bg-success', 'bg-danger', 'bg-warning');
    
    switch (type) {
        case 'success':
            toastNotification.classList.add('bg-success', 'text-white');
            break;
        case 'error':
            toastNotification.classList.add('bg-danger', 'text-white');
            break;
        case 'warning':
            toastNotification.classList.add('bg-warning', 'text-dark');
            break;
    }
    
    toast.show();
}

// 加载用户列表函数
function loadUsers() {
    // 显示加载状态
    userTableLoading.classList.remove('d-none');
    userTableEmpty.classList.add('d-none');
    userTable.innerHTML = '';
    
    fetch('/api/users')
    .then(response => {
        if (response.status === 403) {
            throw new Error('权限不足：只有管理员可以访问用户管理功能');
        }
        return response.json();
    })
    .then(data => {
        // 隐藏加载状态
        userTableLoading.classList.add('d-none');
        
        if (data.status === 'ok' && data.users && data.users.length > 0) {
            // 渲染用户列表
            renderUserTable(data.users);
        } else {
            // 显示空数据提示
            userTableEmpty.classList.remove('d-none');
        }
    })
    .catch(error => {
        userTableLoading.classList.add('d-none');
        userTableEmpty.classList.remove('d-none');
        userTableEmpty.textContent = `加载失败: ${error.message}`;
        userTableEmpty.classList.add('alert-danger');
        console.error('加载用户列表失败:', error);
    });
}

// 渲染用户表格
function renderUserTable(users) {
    userTable.innerHTML = '';
    
    users.forEach(user => {
        const row = document.createElement('tr');
        
        // 创建表格单元格
        const idCell = document.createElement('td');
        idCell.textContent = user.id;
        
        const usernameCell = document.createElement('td');
        usernameCell.textContent = user.username;
        
        const passwordCell = document.createElement('td');
        passwordCell.innerHTML = `
            <div class="d-flex align-items-center">
                <span class="text-success fw-bold me-2">${user.reset_password || '[已加密]'}</span>
                <button class="btn btn-sm btn-outline-warning reset-password" data-id="${user.id}" title="重置密码">
                    <i class='bx bx-reset'></i> 重置密码
                </button>
            </div>
        `;
        
        const classCell = document.createElement('td');
        classCell.textContent = user.class_id || '无';
        
        const typeCell = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = 'badge ' + (user.is_admin ? 'admin-badge' : 'teacher-badge');
        badge.textContent = user.is_admin ? '管理员' : '班主任';
        typeCell.appendChild(badge);
        
        const createdAtCell = document.createElement('td');
        createdAtCell.textContent = formatDateTime(user.created_at);
        
        const actionsCell = document.createElement('td');
        actionsCell.className = 'user-actions';
        
        // 编辑按钮
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary me-1';
        editBtn.innerHTML = '<i class="bx bx-edit"></i>';
        editBtn.title = '编辑用户';
        editBtn.onclick = function() {
            openEditModal(user);
        };
        
        // 删除按钮
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger';
        deleteBtn.innerHTML = '<i class="bx bx-trash"></i>';
        deleteBtn.title = '删除用户';
        deleteBtn.onclick = function() {
            openDeleteModal(user);
        };
        
        actionsCell.appendChild(editBtn);
        actionsCell.appendChild(deleteBtn);
        
        // 添加所有单元格到行
        row.appendChild(idCell);
        row.appendChild(usernameCell);
        row.appendChild(passwordCell);
        row.appendChild(classCell);
        row.appendChild(typeCell);
        row.appendChild(createdAtCell);
        row.appendChild(actionsCell);
        
        // 添加行到表格
        userTable.appendChild(row);
    });
    
    // 添加显示密码的事件监听
    document.querySelectorAll('.show-password').forEach(button => {
        button.addEventListener('click', function() {
            const passwordSpan = this.previousElementSibling;
            const password = this.dataset.password;
            if (passwordSpan.textContent === '••••••') {
                passwordSpan.textContent = password;
                this.querySelector('i').classList.replace('bx-show', 'bx-hide');
            } else {
                passwordSpan.textContent = '••••••';
                this.querySelector('i').classList.replace('bx-hide', 'bx-show');
            }
        });
    });
    
    // 初始化重置密码按钮
    initResetPasswordButtons();
}

// 打开编辑模态框
function openEditModal(user) {
    document.getElementById('editUserId').value = user.id;
    document.getElementById('editUsername').value = user.username;
    document.getElementById('editPassword').value = ''; // 密码输入框保持为空
    document.getElementById('editUserClassId').value = user.class_id || '';
    document.getElementById('editIsAdmin').checked = user.is_admin;
    
    const editModal = new bootstrap.Modal(document.getElementById('editUserModal'));
    editModal.show();
}

// 打开删除确认模态框
function openDeleteModal(user) {
    document.getElementById('deleteUserId').value = user.id;
    document.getElementById('deleteUserName').textContent = user.username;
    
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteUserModal'));
    deleteModal.show();
}

// 添加用户
document.getElementById('saveUserBtn').addEventListener('click', function() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const class_id = document.getElementById('class_id').value;
    const is_admin = document.getElementById('is_admin').checked;
    
    if (!username || !password) {
        showToast('用户名和密码不能为空', 'warning');
        return;
    }
    
    // 禁用按钮防止重复提交
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
    
    fetch('/api/users', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: username,
            password: password,
            class_id: class_id || null,
            is_admin: is_admin
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('addUserModal')).hide();
            
            // 显示成功消息
            showToast(data.message, 'success');
            
            // 重新加载用户列表
            loadUsers();
            
            // 重置表单
            document.getElementById('addUserForm').reset();
        } else {
            showToast(`添加用户失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        showToast(`添加用户失败: ${error.message}`, 'error');
        console.error('添加用户失败:', error);
    })
    .finally(() => {
        // 恢复按钮状态
        this.disabled = false;
        this.innerHTML = '保存';
    });
});

// 更新用户
document.getElementById('updateUserBtn').addEventListener('click', function() {
    const userId = document.getElementById('editUserId').value;
    const username = document.getElementById('editUsername').value;
    const password = document.getElementById('editPassword').value;
    const class_id = document.getElementById('editUserClassId').value;
    const is_admin = document.getElementById('editIsAdmin').checked;
    
    if (!username) {
        showToast('用户名不能为空', 'warning');
        return;
    }
    
    // 禁用按钮防止重复提交
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 更新中...';
    
    const userData = {
        username: username,
        class_id: class_id || null,
        is_admin: is_admin
    };
    
    // 仅当密码不为空时才包含密码字段
    if (password) {
        userData.password = password;
    }
    
    fetch(`/api/users/${userId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('editUserModal')).hide();
            
            // 显示成功消息
            showToast(data.message, 'success');
            
            // 重新加载用户列表
            loadUsers();
        } else {
            showToast(`更新用户失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        showToast(`更新用户失败: ${error.message}`, 'error');
        console.error('更新用户失败:', error);
    })
    .finally(() => {
        // 恢复按钮状态
        this.disabled = false;
        this.innerHTML = '更新';
    });
});

// 删除用户
document.getElementById('confirmDeleteBtn').addEventListener('click', function() {
    const userId = document.getElementById('deleteUserId').value;
    
    // 禁用按钮防止重复提交
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 删除中...';
    
    fetch(`/api/users/${userId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('deleteUserModal')).hide();
            
            // 显示成功消息
            showToast(data.message, 'success');
            
            // 重新加载用户列表
            loadUsers();
        } else {
            showToast(`删除用户失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        showToast(`删除用户失败: ${error.message}`, 'error');
        console.error('删除用户失败:', error);
    })
    .finally(() => {
        // 恢复按钮状态
        this.disabled = false;
        this.innerHTML = '删除';
    });
});

// 提交Excel导入
document.getElementById('importExcelBtn').addEventListener('click', function() {
    document.getElementById('importExcelForm').style.display = 'block';
});

document.getElementById('cancelImportBtn').addEventListener('click', function() {
    document.getElementById('importExcelForm').style.display = 'none';
});

// 文件选择事件 - 预览Excel数据
document.getElementById('excelFile').addEventListener('change', function() {
    previewExcelData();
});

// 确认导入按钮事件
document.getElementById('confirmImportBtn').addEventListener('click', function() {
    confirmImport();
});

// 预览Excel数据函数
function previewExcelData() {
    const fileInput = document.getElementById('excelFile');
    if (!fileInput.files.length) {
            return;
        }
        
    const file = fileInput.files[0];
    
    // 检查文件类型
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        showToast('请上传Excel文件（.xlsx或.xls格式）', 'warning');
        return;
    }
    
    // 显示加载状态
    document.getElementById('previewLoading').style.display = 'block';
    document.getElementById('previewArea').style.display = 'none';
    document.getElementById('confirmImportBtn').style.display = 'none';
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);
    
    // 发送预览请求
    fetch('/api/users/preview-import', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // 隐藏加载状态
        document.getElementById('previewLoading').style.display = 'none';
        
        if (data.status === 'ok') {
            // 显示预览数据
            renderPreviewData(data);
            
            // 保存文件路径
            document.getElementById('importFilePath').value = data.file_path;
            
            // 显示确认导入按钮
            document.getElementById('confirmImportBtn').style.display = 'inline-block';
                } else {
            showToast(`预览失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        document.getElementById('previewLoading').style.display = 'none';
        showToast(`预览失败: ${error.message}`, 'error');
        console.error('预览Excel数据失败:', error);
    });
}

// 渲染预览数据
function renderPreviewData(data) {
    const previewArea = document.getElementById('previewArea');
    const previewTableBody = document.getElementById('previewTableBody');
    const previewStats = document.getElementById('previewStats');
    const previewMessage = document.getElementById('previewMessage');
    
    // 清空现有预览数据
    previewTableBody.innerHTML = '';
    
    // 设置预览统计信息
    previewStats.textContent = `(共 ${data.stats.total} 条，有效 ${data.stats.valid} 条，无效 ${data.stats.invalid} 条)`;
    
    // 设置预览消息
    previewMessage.textContent = data.message;
    
    // 添加预览数据行
    data.preview.forEach(item => {
        const row = document.createElement('tr');
        
        // 设置行样式
        if (!item.is_valid) {
            row.className = 'table-danger';
        }
        
        // 添加单元格
        const rowNumCell = document.createElement('td');
        rowNumCell.textContent = item.row;
        
        const usernameCell = document.createElement('td');
        usernameCell.textContent = item.username;
        
        const classCell = document.createElement('td');
        classCell.textContent = item.class_name;
        
        const statusCell = document.createElement('td');
        statusCell.textContent = item.status;
        
        const reasonCell = document.createElement('td');
        reasonCell.textContent = item.reason || '-';
        
        // 添加单元格到行
        row.appendChild(rowNumCell);
        row.appendChild(usernameCell);
        row.appendChild(classCell);
        row.appendChild(statusCell);
        row.appendChild(reasonCell);
        
        // 添加行到表格
        previewTableBody.appendChild(row);
    });
    
    // 显示预览区域
    previewArea.style.display = 'block';
}

// 确认导入
function confirmImport() {
    const filePath = document.getElementById('importFilePath').value;
    
    if (!filePath) {
        showToast('没有可导入的数据，请先选择Excel文件', 'warning');
        return;
    }
    
    // 禁用按钮防止重复提交
    const confirmBtn = document.getElementById('confirmImportBtn');
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 导入中...';
    
    // 发送确认导入请求
    fetch('/api/users/confirm-import', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            file_path: filePath
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 显示密码信息
            document.getElementById('importSuccessMessage').textContent = 
                `成功导入 ${data.added_count} 个班主任账户${data.skipped_count > 0 ? '，' + data.skipped_count + ' 个账户被跳过' : ''}`;
            
            // 显示密码信息
            const passwordTableBody = document.getElementById('passwordTableBody');
            passwordTableBody.innerHTML = '';
            
            data.passwords.forEach(item => {
                const row = document.createElement('tr');
                
                const usernameCell = document.createElement('td');
                usernameCell.textContent = item.username;
                
                const classCell = document.createElement('td');
                classCell.textContent = item.class_id;
                
                const passwordCell = document.createElement('td');
                passwordCell.textContent = item.password;
                passwordCell.style.fontFamily = 'monospace';
                
                row.appendChild(usernameCell);
                row.appendChild(classCell);
                row.appendChild(passwordCell);
                
                passwordTableBody.appendChild(row);
            });
            
            // 显示跳过的账户信息
            if (data.skipped && data.skipped.length > 0) {
                const skippedTableBody = document.getElementById('skippedTableBody');
                skippedTableBody.innerHTML = '';
                
                data.skipped.forEach(item => {
                    const row = document.createElement('tr');
                    
                    const usernameCell = document.createElement('td');
                    usernameCell.textContent = item.username;
                    
                    const classCell = document.createElement('td');
                    classCell.textContent = item.class_id;
                    
                    const reasonCell = document.createElement('td');
                    reasonCell.textContent = item.reason;
                    reasonCell.className = 'text-danger';
                    
                    row.appendChild(usernameCell);
                    row.appendChild(classCell);
                    row.appendChild(reasonCell);
                    
                    skippedTableBody.appendChild(row);
                });
                
                document.getElementById('importSkippedContainer').style.display = 'block';
            } else {
                document.getElementById('importSkippedContainer').style.display = 'none';
            }
            
            // 显示结果模态框
            const importResultModal = new bootstrap.Modal(document.getElementById('importResultModal'));
            importResultModal.show();
            
            // 隐藏导入表单
            document.getElementById('importExcelForm').style.display = 'none';
            
            // 清空文件输入
            document.getElementById('excelFile').value = '';
            document.getElementById('previewArea').style.display = 'none';
            document.getElementById('importFilePath').value = '';
            
            // 重新加载用户列表
            loadUsers();
        } else {
            showToast(`导入失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        showToast(`导入失败: ${error.message}`, 'error');
        console.error('确认导入班主任失败:', error);
    })
    .finally(() => {
        // 恢复按钮状态
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="bx bx-upload"></i> 确认导入';
    });
}

// 添加重置密码的功能
// 初始化重置密码按钮
function initResetPasswordButtons() {
    document.querySelectorAll('.reset-password').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.id;
            const userName = this.closest('tr').querySelector('td:nth-child(2)').textContent;
            
            if (confirm(`确定要为用户 ${userName} 重置密码吗？`)) {
                // 禁用按钮
                this.disabled = true;
                this.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i>';
                
                // 发送重置密码请求
                fetch(`/api/users/reset-password/${userId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({}) // 发送空对象作为请求体
                })
                .then(response => {
                    console.log('重置密码响应状态:', response.status);
                    if (!response.ok) {
                        throw new Error(`服务器返回错误: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'ok') {
                        // 显示新密码
                        const passwordDisplay = this.previousElementSibling;
                        passwordDisplay.textContent = data.new_password;
                        passwordDisplay.className = 'text-success fw-bold me-2';
                        
                        // 更改按钮为已重置
                        this.innerHTML = '<i class="bx bx-check"></i> 已重置';
                        this.className = 'btn btn-sm btn-success';
                        this.disabled = true;
                        
                        showToast(`用户 ${userName} 的密码已重置为: ${data.new_password}`, 'success');
                    } else {
                        showToast(`重置密码失败: ${data.message}`, 'error');
                        this.disabled = false;
                        this.innerHTML = '<i class="bx bx-reset"></i> 重置密码';
                    }
                })
                .catch(error => {
                    showToast(`重置密码失败: ${error.message}`, 'error');
                    this.disabled = false;
                    this.innerHTML = '<i class="bx bx-reset"></i> 重置密码';
                });
            }
        });
    });
}

// 添加重置密码事件监听器
document.addEventListener('click', function(e) {
    if (e.target.closest('.reset-password')) {
        const userId = e.target.closest('.reset-password').dataset.id;
        resetPassword(userId);
    }
});

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 加载用户列表
    loadUsers();
    
    // 加载班级列表
    loadClasses();
    
    // 监听选项卡切换事件
    document.getElementById('classes-tab').addEventListener('click', function() {
        loadClasses();
    });
});

// 班级管理相关的JavaScript代码
// 加载班级列表函数
function loadClasses() {
    // 显示加载状态
    const classTableLoading = document.getElementById('classTableLoading');
    const classTableEmpty = document.getElementById('classTableEmpty');
    const classList = document.getElementById('classList');
    
    classTableLoading.classList.remove('d-none');
    classTableEmpty.classList.add('d-none');
    classList.innerHTML = '';
    
    console.log('开始加载班级列表...');
    
    fetch('/api/classes')
    .then(response => {
        console.log('班级列表API响应状态:', response.status);
        if (response.status === 403) {
            throw new Error('权限不足：只有管理员可以访问班级管理功能');
        }
        return response.json();
    })
    .then(data => {
        // 隐藏加载状态
        classTableLoading.classList.add('d-none');
        console.log('班级列表API返回数据:', data);
        
        if (data.status === 'ok' && data.classes && data.classes.length > 0) {
            // 渲染班级列表
            console.log(`渲染${data.classes.length}个班级`);
            renderClassTable(data.classes);
        } else {
            // 显示空数据提示
            console.log('班级数据为空');
            classTableEmpty.classList.remove('d-none');
        }
    })
    .catch(error => {
        classTableLoading.classList.add('d-none');
        classTableEmpty.classList.remove('d-none');
        classTableEmpty.textContent = `加载失败: ${error.message}`;
        classTableEmpty.classList.add('alert-danger');
        console.error('加载班级列表失败:', error);
    });
}

// 渲染班级表格
function renderClassTable(classes) {
    const classList = document.getElementById('classList');
    classList.innerHTML = '';
    
    classes.forEach(classItem => {
        const row = document.createElement('tr');
        
        // 创建表格单元格
        const idCell = document.createElement('td');
        idCell.textContent = classItem.id;
        
        const nameCell = document.createElement('td');
        nameCell.textContent = classItem.class_name;
        
        const teacherCell = document.createElement('td');
        teacherCell.textContent = classItem.teacher_name || '未分配';
        
        const studentCountCell = document.createElement('td');
        studentCountCell.textContent = classItem.student_count || 0;
        
        const createdAtCell = document.createElement('td');
        createdAtCell.textContent = formatDateTime(classItem.created_at);
        
        const actionsCell = document.createElement('td');
        actionsCell.className = 'class-actions';
        
        // 编辑按钮
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary me-1';
        editBtn.innerHTML = '<i class="bx bx-edit"></i>';
        editBtn.title = '编辑班级';
        editBtn.onclick = function() {
            openEditClassModal(classItem);
        };
        
        // 分配班主任按钮
        const assignBtn = document.createElement('button');
        assignBtn.className = 'btn btn-sm btn-outline-info me-1';
        assignBtn.innerHTML = '<i class="bx bx-user-check"></i>';
        assignBtn.title = '分配班主任';
        assignBtn.onclick = function() {
            openAssignTeacherModal(classItem);
        };
        
        // 删除按钮
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger';
        deleteBtn.innerHTML = '<i class="bx bx-trash"></i>';
        deleteBtn.title = '删除班级';
        deleteBtn.onclick = function() {
            openDeleteClassModal(classItem);
        };
        
        actionsCell.appendChild(editBtn);
        actionsCell.appendChild(assignBtn);
        actionsCell.appendChild(deleteBtn);
        
        // 添加所有单元格到行
        row.appendChild(idCell);
        row.appendChild(nameCell);
        row.appendChild(teacherCell);
        row.appendChild(studentCountCell);
        row.appendChild(createdAtCell);
        row.appendChild(actionsCell);
        
        // 添加行到表格
        classList.appendChild(row);
    });
}

// 打开编辑班级模态框
function openEditClassModal(classItem) {
    document.getElementById('editClassId').value = classItem.id;
    document.getElementById('editClassName').value = classItem.class_name;
    
    const editModal = new bootstrap.Modal(document.getElementById('editClassModal'));
    editModal.show();
}

// 打开删除班级确认模态框
function openDeleteClassModal(classItem) {
    document.getElementById('deleteClassId').value = classItem.id;
    document.getElementById('deleteClassName').textContent = classItem.class_name;
    
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteClassModal'));
    deleteModal.show();
}

// 添加班级
document.getElementById('saveClassBtn').addEventListener('click', function() {
    const className = document.getElementById('className').value;
    
    if (!className) {
        showToast('班级名称不能为空', 'warning');
        return;
    }
    
    // 禁用按钮防止重复提交
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
    
    fetch('/api/classes', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            class_name: className
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('addClassModal')).hide();
            
            // 显示成功消息
            showToast(data.message || '添加班级成功', 'success');
            
            // 重新加载班级列表
            loadClasses();
            
            // 重置表单
            document.getElementById('addClassForm').reset();
        } else {
            showToast(`添加班级失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        showToast(`添加班级失败: ${error.message}`, 'error');
        console.error('添加班级失败:', error);
    })
    .finally(() => {
        // 恢复按钮状态
        this.disabled = false;
        this.innerHTML = '保存';
    });
});

// 更新班级
document.getElementById('updateClassBtn').addEventListener('click', function() {
    const classId = document.getElementById('editClassId').value;
    const className = document.getElementById('editClassName').value;
    
    if (!className) {
        showToast('班级名称不能为空', 'warning');
        return;
    }
    
    // 禁用按钮防止重复提交
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 更新中...';
    
    fetch(`/api/classes/${classId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            class_name: className
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('editClassModal')).hide();
            
            // 显示成功消息
            showToast(data.message || '更新班级成功', 'success');
            
            // 重新加载班级列表
            loadClasses();
        } else {
            showToast(`更新班级失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        showToast(`更新班级失败: ${error.message}`, 'error');
        console.error('更新班级失败:', error);
    })
    .finally(() => {
        // 恢复按钮状态
        this.disabled = false;
        this.innerHTML = '更新';
    });
});

// 删除班级
document.getElementById('confirmDeleteClassBtn').addEventListener('click', function() {
    const classId = document.getElementById('deleteClassId').value;
    
    // 禁用按钮防止重复提交
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 删除中...';
    
    fetch(`/api/classes/${classId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('deleteClassModal')).hide();
            
            // 显示成功消息
            showToast(data.message || '删除班级成功', 'success');
            
            // 重新加载班级列表
            loadClasses();
        } else {
            showToast(`删除班级失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        showToast(`删除班级失败: ${error.message}`, 'error');
        console.error('删除班级失败:', error);
    })
    .finally(() => {
        // 恢复按钮状态
        this.disabled = false;
        this.innerHTML = '删除';
    });
});

// 批量创建班级-显示模态框
document.getElementById('batchClassBtn').addEventListener('click', function() {
    const batchClassModal = new bootstrap.Modal(document.getElementById('batchClassModal'));
    
    // 重置所有选择
    document.querySelectorAll('.grade-option, .class-option, #gradeSelectAll, #classSelectAll').forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // 重置预览区域
    document.getElementById('classPreviewArea').style.display = 'none';
    document.getElementById('classPreviewLoading').style.display = 'none';
    document.getElementById('confirmClassBtn').style.display = 'none';
    document.getElementById('selectedClassCount').textContent = '已选择 0 个班级';
    
    batchClassModal.show();
    
    // 初始化年级和班级勾选逻辑
    initClassCheckboxes();
});

// 初始化年级和班级勾选逻辑
function initClassCheckboxes() {
    // 定义每个年级的班级数量
    const gradeClassCounts = {
        '一年级': 8,
        '二年级': 6,
        '三年级': 7,
        '四年级': 8,
        '五年级': 6,
        '六年级': 7,
        '初一': 12,
        '初二': 10,
        '初三': 10,
        '高一': 15,
        '高二': 12,
        '高三': 10
    };
    
    // 年级全选/全不选
    document.getElementById('gradeSelectAll').addEventListener('change', function() {
        const isChecked = this.checked;
        document.querySelectorAll('.grade-option').forEach(checkbox => {
            checkbox.checked = isChecked;
        });
        updateGradeClassesContainer();
        updateClassNamePreview();
        updateSelectedClassCount();
    });
    
    // 单个年级勾选变化
    document.querySelectorAll('.grade-option').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            // 更新班级选择区域
            updateGradeClassesContainer();
            
            // 更新班级名称预览
            updateClassNamePreview();
            updateSelectedClassCount();
            
            // 检查是否所有年级都被选中
            const allGrades = document.querySelectorAll('.grade-option');
            const checkedGrades = document.querySelectorAll('.grade-option:checked');
            
            document.getElementById('gradeSelectAll').checked = 
                allGrades.length === checkedGrades.length && allGrades.length > 0;
        });
    });
    
    // 更新年级对应的班级选择区域
    function updateGradeClassesContainer() {
        const gradeClassesContainer = document.getElementById('gradeClassesContainer');
        const noGradeSelectedMsg = document.getElementById('noGradeSelected');
        
        // 获取选中的年级
        const selectedGrades = Array.from(document.querySelectorAll('.grade-option:checked'))
            .map(el => el.dataset.grade);
        
        // 清空现有班级选项
        gradeClassesContainer.innerHTML = '';
        
        // 如果没有选择年级，显示提示信息
        if (selectedGrades.length === 0) {
            gradeClassesContainer.appendChild(noGradeSelectedMsg);
            return;
        }
        
        // 为每个选中的年级创建班级选择区域
        selectedGrades.forEach(grade => {
            // 年级区域标题
            const gradeTitle = document.createElement('h6');
            gradeTitle.className = 'mt-3 mb-2 border-bottom pb-2';
            gradeTitle.innerHTML = `<i class='bx bx-chevron-right'></i> ${grade}`;
            gradeClassesContainer.appendChild(gradeTitle);
            
            // 该年级的全选/全不选
            const selectAllDiv = document.createElement('div');
            selectAllDiv.className = 'form-check mb-2';
            
            const selectAllCheckbox = document.createElement('input');
            selectAllCheckbox.type = 'checkbox';
            selectAllCheckbox.className = 'form-check-input grade-class-select-all';
            selectAllCheckbox.id = `selectAll_${grade}`;
            selectAllCheckbox.dataset.grade = grade;
            
            const selectAllLabel = document.createElement('label');
            selectAllLabel.className = 'form-check-label';
            selectAllLabel.htmlFor = `selectAll_${grade}`;
            selectAllLabel.textContent = '全选/全不选';
            
            selectAllDiv.appendChild(selectAllCheckbox);
            selectAllDiv.appendChild(selectAllLabel);
            gradeClassesContainer.appendChild(selectAllDiv);
            
            // 班级选项容器
            const classesContainer = document.createElement('div');
            classesContainer.className = 'row';
            classesContainer.id = `classes_${grade}`;
            gradeClassesContainer.appendChild(classesContainer);
            
            // 获取该年级的班级数量
            const classCount = gradeClassCounts[grade] || 10; // 默认10个班
            
            // 创建该年级的班级选项
            for (let i = 1; i <= classCount; i++) {
                const colDiv = document.createElement('div');
                colDiv.className = 'col-sm-4';
                
                const formCheck = document.createElement('div');
                formCheck.className = 'form-check';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = `form-check-input class-option ${grade}-class`;
                checkbox.id = `class_${grade}_${i}`;
                checkbox.dataset.grade = grade;
                checkbox.dataset.class = i + '班';
                
                const label = document.createElement('label');
                label.className = 'form-check-label';
                label.htmlFor = `class_${grade}_${i}`;
                label.textContent = i + '班';
                
                formCheck.appendChild(checkbox);
                formCheck.appendChild(label);
                colDiv.appendChild(formCheck);
                classesContainer.appendChild(colDiv);
            }
            
            // 为年级全选/全不选添加事件监听
            selectAllCheckbox.addEventListener('change', function() {
                const isChecked = this.checked;
                const gradeClasses = document.querySelectorAll(`.${grade}-class`);
                gradeClasses.forEach(checkbox => {
                    checkbox.checked = isChecked;
                });
                updateClassNamePreview();
                updateSelectedClassCount();
            });
        });
        
        // 为所有新创建的班级选项添加事件监听
        document.querySelectorAll('.class-option').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                updateClassNamePreview();
                updateSelectedClassCount();
                
                // 更新该年级的全选按钮状态
                const grade = this.dataset.grade;
                const gradeClasses = document.querySelectorAll(`.${grade}-class`);
                const checkedGradeClasses = document.querySelectorAll(`.${grade}-class:checked`);
                
                const gradeSelectAll = document.getElementById(`selectAll_${grade}`);
                if (gradeSelectAll) {
                    gradeSelectAll.checked = gradeClasses.length === checkedGradeClasses.length && gradeClasses.length > 0;
                }
            });
        });
    }
    
    // 初始化班级选择区域
    updateGradeClassesContainer();
}

// 更新班级名称预览
function updateClassNamePreview() {
    // 获取所有选中的班级
    const selectedClasses = Array.from(document.querySelectorAll('.class-option:checked'));
    
    if (selectedClasses.length === 0) {
        document.getElementById('classNamePreview').textContent = '年级+班号';
        return;
    }
    
    // 获取第一个选中的班级数据
    const firstClass = selectedClasses[0];
    const previewText = `${firstClass.dataset.grade}${firstClass.dataset.class}`;
    
    document.getElementById('classNamePreview').textContent = 
        selectedClasses.length > 1 ? previewText + '等' : previewText;
}

// 更新已选择班级数量
function updateSelectedClassCount() {
    const selectedClasses = document.querySelectorAll('.class-option:checked').length;
    document.getElementById('selectedClassCount').textContent = `已选择 ${selectedClasses} 个班级`;
}

// 批量创建班级-预览
document.getElementById('previewClassBtn').addEventListener('click', function() {
    previewClasses();
});

// 批量创建班级-确认创建
document.getElementById('confirmClassBtn').addEventListener('click', function() {
    confirmCreateClasses();
});

// 预览班级函数
function previewClasses() {
    // 获取所有选中的班级
    const selectedClassOptions = document.querySelectorAll('.class-option:checked');
    
    if (selectedClassOptions.length === 0) {
        showToast('请至少选择一个班级', 'warning');
        return;
    }
    
    // 生成班级名称列表
    const classNames = Array.from(selectedClassOptions).map(option => 
        `${option.dataset.grade}${option.dataset.class}`
    );
    
    // 显示加载状态
    document.getElementById('classPreviewLoading').style.display = 'block';
    document.getElementById('classPreviewArea').style.display = 'none';
    document.getElementById('confirmClassBtn').style.display = 'none';
    
    // 发送预览请求
    fetch('/api/classes/preview', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            class_names: classNames
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                try {
                    return Promise.reject(JSON.parse(text));
                } catch (e) {
                    return Promise.reject({ 
                        status: 'error', 
                        message: `服务器返回错误 (${response.status}): ${text.substring(0, 100)}...`
                    });
                }
            });
        }
        return response.json();
    })
    .then(data => {
        // 隐藏加载状态
        document.getElementById('classPreviewLoading').style.display = 'none';
        
        if (data.status === 'ok') {
            // 显示预览数据
            renderClassPreview(data);
            
            // 显示确认创建按钮
            document.getElementById('confirmClassBtn').style.display = 'inline-block';
        } else {
            showToast('预览失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        document.getElementById('classPreviewLoading').style.display = 'none';
        
        console.error('预览班级数据出错:', error);
        
        let errorMsg = '预览失败';
        if (error.message) {
            errorMsg += ': ' + error.message;
        } else if (typeof error === 'string') {
            errorMsg += ': ' + error;
        }
        
        showToast(errorMsg, 'error');
    });
}

// 渲染班级预览
function renderClassPreview(response) {
    const previewArea = document.getElementById('classPreviewArea');
    const previewTableBody = document.getElementById('classPreviewTableBody');
    const previewStats = document.getElementById('classPreviewStats');
    const previewMessage = document.getElementById('classPreviewMessage');
    
    // 清空现有预览数据
    previewTableBody.innerHTML = '';
    
    // 设置预览统计信息
    const totalClasses = response.preview.length;
    const newCount = response.preview.filter(item => item.status === '新建').length;
    const existCount = response.preview.filter(item => item.status === '已存在').length;
    
    previewStats.textContent = `(共 ${totalClasses} 个，新建 ${newCount} 个，已存在 ${existCount} 个)`;
    
    // 设置预览消息
    previewMessage.textContent = response.message || `找到 ${totalClasses} 个班级，将创建 ${newCount} 个新班级，跳过 ${existCount} 个已存在的班级。`;
    
    // 添加预览数据行
    response.preview.forEach((item, index) => {
        const row = document.createElement('tr');
        
        // 设置行样式
        if (item.status === '已存在') {
            row.className = 'table-warning';
        } else if (item.status === '新建') {
            row.className = 'table-success';
        }
        
        // 添加单元格
        const indexCell = document.createElement('td');
        indexCell.textContent = index + 1;
        
        const nameCell = document.createElement('td');
        nameCell.textContent = item.class_name;
        
        const statusCell = document.createElement('td');
        statusCell.textContent = item.status;
        
        const noteCell = document.createElement('td');
        noteCell.textContent = item.note || '-';
        
        // 添加单元格到行
        row.appendChild(indexCell);
        row.appendChild(nameCell);
        row.appendChild(statusCell);
        row.appendChild(noteCell);
        
        // 添加行到表格
        previewTableBody.appendChild(row);
    });
    
    // 显示预览区域
    previewArea.style.display = 'block';
}

// 确认创建班级
function confirmCreateClasses() {
    // 获取所有选中的班级
    const selectedClassOptions = document.querySelectorAll('.class-option:checked');
    
    if (selectedClassOptions.length === 0) {
        showToast('请至少选择一个班级', 'warning');
        return;
    }
    
    // 生成班级名称列表
    const classNames = Array.from(selectedClassOptions).map(option => 
        `${option.dataset.grade}${option.dataset.class}`
    );
    
    // 禁用按钮防止重复提交
    const confirmBtn = document.getElementById('confirmClassBtn');
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 创建中...';
    
    // 发送创建请求
    fetch('/api/classes/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            class_names: classNames
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                try {
                    return Promise.reject(JSON.parse(text));
                } catch (e) {
                    return Promise.reject({ 
                        status: 'error', 
                        message: `服务器返回错误 (${response.status}): ${text.substring(0, 100)}...`
                    });
                }
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'ok') {
            // 关闭当前模态框
            bootstrap.Modal.getInstance(document.getElementById('batchClassModal')).hide();
            
            // 显示创建结果
            showClassResults(data);
            
            // 重新加载班级列表
            loadClasses();
        } else {
            showToast('创建班级失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('创建班级时出错:', error);
        
        let errorMsg = '创建班级失败';
        if (error.message) {
            errorMsg += ': ' + error.message;
        } else if (typeof error === 'string') {
            errorMsg += ': ' + error;
        }
        
        showToast(errorMsg, 'error');
    })
    .finally(() => {
        // 恢复按钮状态
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="bx bx-plus"></i> 确认创建';
    });
}

// 显示班级创建结果
function showClassResults(response) {
    // 设置成功消息
    document.getElementById('classSuccessMessage').textContent = response.message || '班级创建成功！';
    
    // 清空结果表格
    const resultTableBody = document.getElementById('classResultTableBody');
    resultTableBody.innerHTML = '';
    
    // 添加创建的班级
    if (response.created && response.created.length > 0) {
        response.created.forEach(item => {
            const row = document.createElement('tr');
            row.className = 'table-success';
            
            const idCell = document.createElement('td');
            idCell.textContent = item.id;
            
            const nameCell = document.createElement('td');
            nameCell.textContent = item.class_name;
            
            const statusCell = document.createElement('td');
            statusCell.textContent = '创建成功';
            
            row.appendChild(idCell);
            row.appendChild(nameCell);
            row.appendChild(statusCell);
            
            resultTableBody.appendChild(row);
        });
    }
    
    // 显示跳过的班级
    if (response.skipped && response.skipped.length > 0) {
        const skippedTableBody = document.getElementById('classSkippedTableBody');
        skippedTableBody.innerHTML = '';
        
        response.skipped.forEach(item => {
            const row = document.createElement('tr');
            
            const nameCell = document.createElement('td');
            nameCell.textContent = item.class_name;
            
            const reasonCell = document.createElement('td');
            reasonCell.textContent = item.reason || '已存在';
            
            row.appendChild(nameCell);
            row.appendChild(reasonCell);
            
            skippedTableBody.appendChild(row);
        });
        
        document.getElementById('classSkippedContainer').style.display = 'block';
    } else {
        document.getElementById('classSkippedContainer').style.display = 'none';
    }
    
    // 显示结果模态框
    const classResultModal = new bootstrap.Modal(document.getElementById('classResultModal'));
    classResultModal.show();
}

// 打开删除班级确认模态框
function openDeleteClassModal(classItem) {
    document.getElementById('deleteClassId').value = classItem.id;
    document.getElementById('deleteClassName').textContent = classItem.class_name;
    
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteClassModal'));
    deleteModal.show();
}

// 打开分配班主任模态框
function openAssignTeacherModal(classItem) {
    document.getElementById('assignClassId').value = classItem.id;
    document.getElementById('assignClassName').textContent = classItem.class_name;
    document.getElementById('currentTeacherName').textContent = classItem.teacher_name || '未分配';
    
    // 显示加载状态
    document.getElementById('teacherLoading').style.display = 'block';
    document.getElementById('teacherSelect').disabled = true;
    
    // 清空选择框，只保留默认选项
    const teacherSelect = document.getElementById('teacherSelect');
    teacherSelect.innerHTML = '<option value="">-- 取消分配班主任 --</option>';
    
    // 加载教师列表
    fetch('/api/teachers')
        .then(response => response.json())
        .then(data => {
            document.getElementById('teacherLoading').style.display = 'none';
            document.getElementById('teacherSelect').disabled = false;
            
            if (data.status === 'ok' && data.teachers) {
                // 填充教师选项
                data.teachers.forEach(teacher => {
                    const option = document.createElement('option');
                    option.value = teacher.id;
                    option.textContent = `${teacher.username}${teacher.class_id ? ' (已分配给: ' + teacher.class_name + ')' : ''}`;
                    
                    // 如果是当前班级的班主任，则选中该选项
                    if (teacher.class_id === classItem.id) {
                        option.selected = true;
                    }
                    
                    teacherSelect.appendChild(option);
                });
            } else {
                teacherSelect.innerHTML += '<option value="" disabled>加载教师列表失败</option>';
                showToast('加载教师列表失败：' + (data.message || '未知错误'), 'error');
            }
        })
        .catch(error => {
            document.getElementById('teacherLoading').style.display = 'none';
            document.getElementById('teacherSelect').disabled = false;
            teacherSelect.innerHTML += '<option value="" disabled>加载失败</option>';
            showToast('加载教师列表出错：' + error.message, 'error');
            console.error('加载教师列表失败:', error);
        });
    
    const assignModal = new bootstrap.Modal(document.getElementById('assignTeacherModal'));
    assignModal.show();
}

// 处理分配班主任的事件
document.getElementById('confirmAssignBtn').addEventListener('click', function() {
    const classId = document.getElementById('assignClassId').value;
    const teacherId = document.getElementById('teacherSelect').value;
    const className = document.getElementById('assignClassName').textContent;
    
    // 禁用按钮防止重复提交
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
    
    fetch(`/api/classes/${classId}/assign-teacher`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            teacher_id: teacherId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('assignTeacherModal')).hide();
            
            // 显示成功消息
            showToast(data.message || '班主任分配成功', 'success');
            
            // 重新加载班级列表
            loadClasses();
        } else {
            showToast(`班主任分配失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        showToast(`班主任分配失败: ${error.message}`, 'error');
        console.error('班主任分配失败:', error);
    })
    .finally(() => {
        // 恢复按钮状态
        this.disabled = false;
        this.innerHTML = '保存';
    });
});

// 处理导出用户按钮点击
document.getElementById('exportUsersBtn').addEventListener('click', function() {
    // 显示导出模态框
    const exportModal = new bootstrap.Modal(document.getElementById('exportUsersModal'));
    
    // 重置模态框状态
    document.getElementById('exportResult').style.display = 'none';
    document.getElementById('exportLoading').style.display = 'none';
    document.getElementById('confirmExportBtn').style.display = 'inline-block';
    document.getElementById('downloadExportBtn').style.display = 'none';
    
    exportModal.show();
});

// 处理确认导出按钮点击
document.getElementById('confirmExportBtn').addEventListener('click', function() {
    // 获取导出选项
    const onlyTeachers = document.getElementById('onlyTeachers').checked;
    const includeAdmin = document.getElementById('includeAdmin').checked;
    
    // 显示加载状态
    document.getElementById('exportLoading').style.display = 'block';
    document.getElementById('exportResult').style.display = 'none';
    
    // 禁用按钮防止重复提交
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 导出中...';
    
    // 构建API URL
    const apiUrl = `/api/users/export?only_teachers=${onlyTeachers}&include_admin=${includeAdmin}`;
    
    // 发送导出请求
    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            // 隐藏加载状态
            document.getElementById('exportLoading').style.display = 'none';
            
            if (data.status === 'ok' && data.users && data.users.length > 0) {
                // 显示导出结果
                renderExportResults(data.users);
                
                // 更新导出信息文本
                document.getElementById('exportInfoText').textContent = 
                    `成功导出 ${data.users.length} 个用户账号。请妥善保管密码信息。`;
                
                // 显示下载按钮
                document.getElementById('downloadExportBtn').style.display = 'inline-block';
                
                // 保存导出数据，用于下载
                window.exportData = data.users;
            } else {
                // 显示空结果
                document.getElementById('exportResult').style.display = 'block';
                document.getElementById('exportTableBody').innerHTML = '<tr><td colspan="4" class="text-center">没有符合条件的用户数据</td></tr>';
                document.getElementById('exportInfoText').textContent = '未找到符合条件的用户数据';
            }
        })
        .catch(error => {
            document.getElementById('exportLoading').style.display = 'none';
            showToast(`导出用户列表失败: ${error.message}`, 'error');
            console.error('导出用户列表失败:', error);
        })
        .finally(() => {
            // 恢复按钮状态
            this.disabled = false;
            this.innerHTML = '<i class="bx bx-export"></i> 导出';
            
            // 隐藏此按钮，避免重复点击
            this.style.display = 'none';
        });
});

// 渲染导出结果
function renderExportResults(users) {
    const tableBody = document.getElementById('exportTableBody');
    tableBody.innerHTML = '';
    
    users.forEach(user => {
        const row = document.createElement('tr');
        
        const usernameCell = document.createElement('td');
        usernameCell.textContent = user.username;
        
        const passwordCell = document.createElement('td');
        passwordCell.textContent = user.password;
        passwordCell.className = 'font-monospace';
        
        const classCell = document.createElement('td');
        classCell.textContent = user.class_name || '-';
        
        const roleCell = document.createElement('td');
        roleCell.textContent = user.is_admin;
        
        row.appendChild(usernameCell);
        row.appendChild(passwordCell);
        row.appendChild(classCell);
        row.appendChild(roleCell);
        
        tableBody.appendChild(row);
    });
    
    // 显示结果区域
    document.getElementById('exportResult').style.display = 'block';
}

// 处理下载Excel按钮点击
document.getElementById('downloadExportBtn').addEventListener('click', function() {
    if (!window.exportData || window.exportData.length === 0) {
        showToast('没有可供下载的数据', 'warning');
        return;
    }
    
    // 获取导出选项
    const onlyTeachers = document.getElementById('onlyTeachers').checked;
    const includeAdmin = document.getElementById('includeAdmin').checked;
    
    // 构建下载URL
    const url = `/api/users/export-excel?only_teachers=${onlyTeachers}&include_admin=${includeAdmin}`;
    
    // 创建临时下载链接
    const link = document.createElement('a');
    link.href = url;
    link.style.display = 'none';
    document.body.appendChild(link);
    
    // 触发下载并清理
    link.click();
    setTimeout(() => {
        document.body.removeChild(link);
    }, 100);
}); 