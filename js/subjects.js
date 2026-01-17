/**
 * 学科管理JavaScript
 */

$(document).ready(function() {
    // 初始化
    loadSubjects();
    loadTeachers();
    loadAssignments();
    
    // 标签页切换事件
    $('#subjects-tab').on('shown.bs.tab', function() {
        loadSubjects();
    });
    
    $('#assignments-tab').on('shown.bs.tab', function() {
        loadAssignments();
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
    
    // 分配学科按钮
    $('#assign-subject-btn').click(function() {
        loadTeachersForAssign();
        loadSubjectsForAssign();
        $('#assign-form')[0].reset();
        new bootstrap.Modal($('#assignModal')).show();
    });
    
    // 保存分配
    $('#save-assign-btn').click(function() {
        saveAssignment();
    });
    
    // 筛选器变化
    $('#filter-teacher, #filter-subject').change(function() {
        loadAssignments();
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
                displaySubjects(response.subjects);
                updateSubjectFilter(response.subjects);
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

// ==================== 任教分配管理 ====================

// 加载教师列表
let allTeachers = [];
function loadTeachers() {
    $.ajax({
        url: '/api/users',
        method: 'GET',
        success: function(response) {
            if (response.status === 'ok') {
                allTeachers = response.users.filter(u => !u.is_admin);
                updateTeacherFilter();
            }
        }
    });
}

// 更新教师筛选器
function updateTeacherFilter() {
    const select = $('#filter-teacher');
    select.find('option:not(:first)').remove();
    
    allTeachers.forEach(function(teacher) {
        select.append(`<option value="${teacher.id}">${teacher.username} (${teacher.primary_role || '科任老师'})</option>`);
    });
}

// 更新学科筛选器
function updateSubjectFilter(subjects) {
    const select = $('#filter-subject');
    select.find('option:not(:first)').remove();
    
    subjects.forEach(function(subject) {
        select.append(`<option value="${subject.id}">${subject.name}</option>`);
    });
}

// 加载任教分配列表
function loadAssignments() {
    const teacherId = $('#filter-teacher').val();
    const subjectId = $('#filter-subject').val();
    
    const tbody = $('#assignments-table-body');
    tbody.html('<tr><td colspan="5" class="text-center"><div class="spinner-border text-primary"></div></td></tr>');
    
    // 获取所有教师的任教信息
    const promises = allTeachers.map(teacher => {
        return $.ajax({
            url: `/api/teacher-subjects/${teacher.id}`,
            method: 'GET'
        }).then(response => {
            return {
                teacher: teacher,
                subjects: response.subjects || []
            };
        });
    });
    
    Promise.all(promises).then(results => {
        // 筛选
        let filtered = results;
        if (teacherId) {
            filtered = filtered.filter(r => r.teacher.id == teacherId);
        }
        if (subjectId) {
            filtered = filtered.filter(r => r.subjects.some(s => s.id == subjectId));
        }
        
        displayAssignments(filtered);
    });
}

// 显示任教分配列表
function displayAssignments(data) {
    const tbody = $('#assignments-table-body');
    tbody.empty();
    
    if (data.length === 0) {
        tbody.append('<tr><td colspan="5" class="text-center text-muted">暂无数据</td></tr>');
        return;
    }
    
    data.forEach(function(item) {
        const teacher = item.teacher;
        const subjects = item.subjects;
        
        const subjectBadges = subjects.map(s => 
            `<span class="badge bg-primary me-1">${s.name} <button type="button" class="btn-close btn-close-white" style="font-size: 0.6em;" onclick="removeSubject('${teacher.id}', ${s.id}, '${escapeHtml(teacher.username)}', '${escapeHtml(s.name)}')"></button></span>`
        ).join('');
        
        const row = `
            <tr>
                <td><strong>${teacher.username}</strong></td>
                <td><span class="badge ${getRoleBadgeClass(teacher)}">${teacher.primary_role || '科任老师'}</span></td>
                <td>${teacher.class_name || '-'}</td>
                <td>${subjectBadges || '<span class="text-muted">未分配学科</span>'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="quickAssign('${teacher.id}', '${escapeHtml(teacher.username)}')">
                        <i class='bx bx-plus'></i> 添加学科
                    </button>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
}

// 获取角色徽章样式
function getRoleBadgeClass(teacher) {
    if (teacher.is_admin) return 'bg-danger';
    
    const roleMap = {
        '正班主任': 'bg-primary',
        '副班主任': 'bg-info',
        '科任老师': 'bg-secondary',
        '行政': 'bg-warning',
        '校级领导': 'bg-success'
    };
    
    return roleMap[teacher.primary_role] || 'bg-secondary';
}

// 快速分配学科
function quickAssign(teacherId, teacherName) {
    loadSubjectsForAssign();
    $('#assign-teacher').val(teacherId);
    $('#assign-teacher').prop('disabled', true);
    $('#assignModal .modal-title').text(`为 ${teacherName} 分配学科`);
    new bootstrap.Modal($('#assignModal')).show();
    
    // 模态框关闭时恢复
    $('#assignModal').on('hidden.bs.modal', function() {
        $('#assign-teacher').prop('disabled', false);
        $('#assignModal .modal-title').text('分配学科');
    });
}

// 加载教师列表（用于分配）
function loadTeachersForAssign() {
    const select = $('#assign-teacher');
    select.find('option:not(:first)').remove();
    
    allTeachers.forEach(function(teacher) {
        select.append(`<option value="${teacher.id}">${teacher.username} (${teacher.primary_role || '科任老师'})</option>`);
    });
}

// 加载学科列表（用于分配）
function loadSubjectsForAssign() {
    $.ajax({
        url: '/api/subjects',
        method: 'GET',
        success: function(response) {
            if (response.status === 'ok') {
                const select = $('#assign-subject');
                select.find('option:not(:first)').remove();
                
                response.subjects.forEach(function(subject) {
                    select.append(`<option value="${subject.id}">${subject.name}</option>`);
                });
            }
        }
    });
}

// 保存分配
function saveAssignment() {
    const teacherId = $('#assign-teacher').val();
    const subjectId = $('#assign-subject').val();
    
    if (!teacherId || !subjectId) {
        alert('请选择教师和学科');
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
                bootstrap.Modal.getInstance($('#assignModal')).hide();
                showSuccess(response.message);
                loadAssignments();
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

// 移除学科
function removeSubject(teacherId, subjectId, teacherName, subjectName) {
    if (!confirm(`确定要移除 ${teacherName} 的 ${subjectName} 学科吗？`)) {
        return;
    }
    
    $.ajax({
        url: `/api/teacher-subjects/${teacherId}/${subjectId}`,
        method: 'DELETE',
        success: function(response) {
            if (response.status === 'ok') {
                showSuccess(response.message);
                loadAssignments();
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
    // 简单的提示，可以后续改为Toast
    const alert = $(`
        <div class="alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3" style="z-index: 9999;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    $('body').append(alert);
    setTimeout(() => alert.alert('close'), 3000);
}

// 显示错误消息
function showError(message) {
    const alert = $(`
        <div class="alert alert-danger alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3" style="z-index: 9999;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    $('body').append(alert);
    setTimeout(() => alert.alert('close'), 3000);
}
