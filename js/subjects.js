/**
 * 学科管理JavaScript - 拖拽版本
 */

// 全局变量
let allTeachers = [];
let allSubjects = [];
let teacherSubjects = {}; // {teacherId: [subjectIds]}

$(document).ready(function() {
    // 初始化
    loadSubjects();
    loadTeachers();
    
    // 标签页切换事件
    $('#subjects-tab').on('shown.bs.tab', function() {
        loadSubjects();
    });
    
    $('#assignments-tab').on('shown.bs.tab', function() {
        loadDragDropInterface();
    });
    
    // 添加学科按钮
    $('#add-subject-btn').click(function() {
        $('#subjectModalLabel').text('添加学科');
        $('#subject-form')[0].reset();
        $('#subject-id').val('');
        new bootstrap.Modal($('#subjectModal')).show();
    });
    
    // 保存学科
    $('#save-subject-btn').click(function() {
        saveSubject();
    });
});

// ==================== 学科管理 ====================

// 加载学科列表
function loadSubjects() {
    $.ajax({
        url: '/api/subjects',
        method: 'GET',
        success: function(response) {
            if (response.status === 'ok') {
                allSubjects = response.subjects;
                displaySubjects(response.subjects);
            } else {
                showError('加载学科列表失败');
            }
        },
        error: function() {
            showError('加载学科列表失败');
        }
    });
}

// 显示学科列表
function displaySubjects(subjects) {
    const tbody = $('#subjects-table-body');
    tbody.empty();
    
    if (subjects.length === 0) {
        tbody.append('<tr><td colspan="6" class="text-center text-muted">暂无学科</td></tr>');
        return;
    }
    
    subjects.forEach(function(subject) {
        // 获取任教教师数
        $.ajax({
            url: `/api/subject-teachers/${subject.id}`,
            method: 'GET',
            async: false,
            success: function(response) {
                subject.teacherCount = response.teachers ? response.teachers.length : 0;
            }
        });
        
        const row = `
            <tr>
                <td>${subject.id}</td>
                <td><strong>${subject.name}</strong></td>
                <td>${subject.description || '-'}</td>
                <td><span class="badge bg-info">${subject.teacherCount} 人</span></td>
                <td>${formatDateTime(subject.created_at)}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="editSubject(${subject.id}, '${escapeHtml(subject.name)}', '${escapeHtml(subject.description || '')}')">
                            <i class='bx bx-edit'></i> 编辑
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteSubject(${subject.id}, '${escapeHtml(subject.name)}', ${subject.teacherCount})">
                            <i class='bx bx-trash'></i> 删除
                        </button>
                    </div>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
}

// 编辑学科
function editSubject(id, name, description) {
    $('#subjectModalLabel').text('编辑学科');
    $('#subject-id').val(id);
    $('#subject-name').val(name);
    $('#subject-description').val(description);
    new bootstrap.Modal($('#subjectModal')).show();
}

// 保存学科
function saveSubject() {
    const id = $('#subject-id').val();
    const name = $('#subject-name').val().trim();
    const description = $('#subject-description').val().trim();
    
    if (!name) {
        alert('请输入学科名称');
        return;
    }
    
    const data = {
        name: name,
        description: description
    };
    
    const url = id ? `/api/subjects/${id}` : '/api/subjects';
    const method = id ? 'PUT' : 'POST';
    
    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(response) {
            if (response.status === 'ok') {
                bootstrap.Modal.getInstance($('#subjectModal')).hide();
                showSuccess(response.message);
                loadSubjects();
            } else {
                alert(response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '保存失败');
        }
    });
}

// 删除学科
function deleteSubject(id, name, teacherCount) {
    if (teacherCount > 0) {
        alert(`该学科有 ${teacherCount} 位教师任教，无法删除`);
        return;
    }
    
    if (!confirm(`确定要删除学科"${name}"吗？`)) {
        return;
    }
    
    $.ajax({
        url: `/api/subjects/${id}`,
        method: 'DELETE',
        success: function(response) {
            if (response.status === 'ok') {
                showSuccess(response.message);
                loadSubjects();
            } else {
                alert(response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '删除失败');
        }
    });
}

// ==================== 拖拽分配管理 ====================

// 加载教师列表
function loadTeachers() {
    $.ajax({
        url: '/api/users',
        method: 'GET',
        success: function(response) {
            if (response.status === 'ok') {
                allTeachers = response.users.filter(u => !u.is_admin);
            }
        }
    });
}

// 加载拖拽界面
function loadDragDropInterface() {
    // 加载教师卡片
    loadTeacherCards();
    
    // 加载学科区域
    loadSubjectBoxes();
}

// 加载教师卡片
function loadTeacherCards() {
    const container = $('#teachers-drag-list');
    container.html('<div class="text-center text-muted w-100"><div class="spinner-border spinner-border-sm"></div> 加载中...</div>');
    
    if (allTeachers.length === 0) {
        setTimeout(loadTeacherCards, 500);
        return;
    }
    
    container.empty();
    
    allTeachers.forEach(function(teacher) {
        const card = $(`
            <div class="teacher-card" draggable="true" data-teacher-id="${teacher.id}" data-teacher-name="${escapeHtml(teacher.username)}">
                ${teacher.username}
                <small class="ms-1 text-muted">(${teacher.primary_role || '科任老师'})</small>
            </div>
        `);
        
        // 拖拽开始
        card.on('dragstart', function(e) {
            $(this).addClass('dragging');
            e.originalEvent.dataTransfer.effectAllowed = 'copy';
            e.originalEvent.dataTransfer.setData('teacherId', teacher.id);
            e.originalEvent.dataTransfer.setData('teacherName', teacher.username);
        });
        
        // 拖拽结束
        card.on('dragend', function() {
            $(this).removeClass('dragging');
        });
        
        container.append(card);
    });
}

// 加载学科区域
function loadSubjectBoxes() {
    const container = $('#subjects-drop-area');
    container.html('<div class="col-12 text-center text-muted"><div class="spinner-border spinner-border-sm"></div> 加载中...</div>');
    
    if (allSubjects.length === 0) {
        setTimeout(loadSubjectBoxes, 500);
        return;
    }
    
    // 先加载所有教师的任教信息
    loadAllTeacherSubjects().then(function() {
        container.empty();
        
        allSubjects.forEach(function(subject) {
            const box = createSubjectBox(subject);
            container.append(box);
        });
    });
}

// 加载所有教师的任教信息
function loadAllTeacherSubjects() {
    const promises = allTeachers.map(teacher => {
        return $.ajax({
            url: `/api/teacher-subjects/${teacher.id}`,
            method: 'GET'
        }).then(response => {
            teacherSubjects[teacher.id] = response.subjects.map(s => s.id);
        });
    });
    
    return Promise.all(promises);
}

// 创建学科区域
function createSubjectBox(subject) {
    const col = $('<div class="col-md-6 col-lg-4"></div>');
    const box = $(`
        <div class="subject-box" data-subject-id="${subject.id}">
            <div class="subject-box-header">
                ${subject.name}
                <small class="text-muted ms-2">${subject.description || ''}</small>
            </div>
            <div class="subject-box-teachers" data-subject-id="${subject.id}">
                <div class="empty-hint">拖拽教师到这里</div>
            </div>
        </div>
    `);
    
    // 拖拽进入
    box.on('dragover', function(e) {
        e.preventDefault();
        e.originalEvent.dataTransfer.dropEffect = 'copy';
        $(this).addClass('drag-over');
    });
    
    // 拖拽离开
    box.on('dragleave', function() {
        $(this).removeClass('drag-over');
    });
    
    // 放下
    box.on('drop', function(e) {
        e.preventDefault();
        $(this).removeClass('drag-over');
        
        const teacherId = e.originalEvent.dataTransfer.getData('teacherId');
        const teacherName = e.originalEvent.dataTransfer.getData('teacherName');
        const subjectId = subject.id;
        
        assignTeacherToSubject(teacherId, teacherName, subjectId, subject.name);
    });
    
    // 加载已分配的教师
    loadSubjectTeachers(subject.id, box.find('.subject-box-teachers'));
    
    col.append(box);
    return col;
}

// 加载学科的教师
function loadSubjectTeachers(subjectId, container) {
    // 找出任教该学科的教师
    const teachers = allTeachers.filter(t => {
        return teacherSubjects[t.id] && teacherSubjects[t.id].includes(subjectId);
    });
    
    container.empty();
    
    if (teachers.length === 0) {
        container.append('<div class="empty-hint">拖拽教师到这里</div>');
        return;
    }
    
    teachers.forEach(function(teacher) {
        const tag = $(`
            <div class="teacher-tag">
                ${teacher.username}
                <span class="remove-btn" data-teacher-id="${teacher.id}" data-subject-id="${subjectId}">×</span>
            </div>
        `);
        
        // 移除按钮点击事件
        tag.find('.remove-btn').click(function() {
            const tid = $(this).data('teacher-id');
            const sid = $(this).data('subject-id');
            removeTeacherFromSubject(tid, sid);
        });
        
        container.append(tag);
    });
}

// 分配教师到学科
function assignTeacherToSubject(teacherId, teacherName, subjectId, subjectName) {
    // 检查是否已分配
    if (teacherSubjects[teacherId] && teacherSubjects[teacherId].includes(subjectId)) {
        showInfo(`${teacherName} 已任教 ${subjectName}`);
        return;
    }
    
    $.ajax({
        url: '/api/teacher-subjects',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            teacher_id: teacherId,
            subject_id: subjectId
        }),
        success: function(response) {
            if (response.status === 'ok') {
                // 更新本地数据
                if (!teacherSubjects[teacherId]) {
                    teacherSubjects[teacherId] = [];
                }
                teacherSubjects[teacherId].push(subjectId);
                
                // 刷新学科区域
                const container = $(`.subject-box-teachers[data-subject-id="${subjectId}"]`);
                loadSubjectTeachers(subjectId, container);
                
                showSuccess(`${teacherName} 已分配到 ${subjectName}`);
            } else {
                alert(response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '分配失败');
        }
    });
}

// 移除教师的学科
function removeTeacherFromSubject(teacherId, subjectId) {
    const teacher = allTeachers.find(t => t.id == teacherId);
    const subject = allSubjects.find(s => s.id == subjectId);
    
    if (!confirm(`确定要移除 ${teacher.username} 的 ${subject.name} 学科吗？`)) {
        return;
    }
    
    $.ajax({
        url: `/api/teacher-subjects/${teacherId}/${subjectId}`,
        method: 'DELETE',
        success: function(response) {
            if (response.status === 'ok') {
                // 更新本地数据
                if (teacherSubjects[teacherId]) {
                    teacherSubjects[teacherId] = teacherSubjects[teacherId].filter(id => id != subjectId);
                }
                
                // 刷新学科区域
                const container = $(`.subject-box-teachers[data-subject-id="${subjectId}"]`);
                loadSubjectTeachers(subjectId, container);
                
                showSuccess(response.message);
            } else {
                alert(response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '移除失败');
        }
    });
}

// ==================== 工具函数 ====================

// 格式化日期时间
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// HTML转义
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// 显示成功消息
function showSuccess(message) {
    showToast(message, 'success');
}

// 显示错误消息
function showError(message) {
    showToast(message, 'danger');
}

// 显示信息消息
function showInfo(message) {
    showToast(message, 'info');
}

// 显示Toast消息
function showToast(message, type) {
    const alert = $(`
        <div class="alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3" style="z-index: 9999;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    $('body').append(alert);
    setTimeout(() => alert.alert('close'), 3000);
}
