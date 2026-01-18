// 教师分配管理 - 拖拽式角色和班级分配

// 全局变量
let teachers = [];
let roles = ['正班主任', '副班主任', '科任老师', '行政', '校级领导'];
let classes = [];
let currentTab = 'role'; // 'role' 或 'class'

// Toast通知
const toastEl = document.getElementById('toastNotification');
const toast = new bootstrap.Toast(toastEl);

// 显示提示消息
function showToast(message, type = 'success') {
    const toastMessage = document.getElementById('toastMessage');
    toastMessage.textContent = message;
    
    toastEl.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'text-white');
    
    if (type === 'success') {
        toastEl.classList.add('bg-success', 'text-white');
    } else if (type === 'error') {
        toastEl.classList.add('bg-danger', 'text-white');
    } else if (type === 'warning') {
        toastEl.classList.add('bg-warning');
    }
    
    toast.show();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 监听选项卡切换
    document.getElementById('role-tab').addEventListener('click', function() {
        currentTab = 'role';
        loadRoleAssignment();
    });
    
    document.getElementById('class-tab').addEventListener('click', function() {
        currentTab = 'class';
        loadClassAssignment();
    });
    
    // 初始加载角色分配
    loadRoleAssignment();
});

// 加载角色分配
async function loadRoleAssignment() {
    try {
        // 加载教师列表
        await loadTeachers();
        
        // 渲染教师卡片
        renderTeacherCards('teachersArea');
        
        // 渲染角色分配区域
        renderRoleBoxes();
        
        // 初始化拖拽功能
        initDragAndDrop('role');
        
    } catch (error) {
        console.error('加载角色分配失败:', error);
        showToast('加载失败: ' + error.message, 'error');
    }
}

// 加载班级分配
async function loadClassAssignment() {
    try {
        // 加载教师列表
        await loadTeachers();
        
        // 加载班级列表
        await loadClasses();
        
        // 渲染教师卡片
        renderTeacherCards('teachersArea2');
        
        // 渲染班级分配区域
        renderClassBoxes();
        
        // 初始化拖拽功能
        initDragAndDrop('class');
        
    } catch (error) {
        console.error('加载班级分配失败:', error);
        showToast('加载失败: ' + error.message, 'error');
    }
}

// 加载教师列表
async function loadTeachers() {
    const response = await fetch('/api/users');
    const data = await response.json();
    
    if (data.status === 'ok') {
        // 过滤掉超级管理员
        teachers = data.users.filter(user => !user.is_admin);
        return teachers;
    } else {
        throw new Error(data.message || '加载教师列表失败');
    }
}

// 加载班级列表
async function loadClasses() {
    const response = await fetch('/api/classes');
    const data = await response.json();
    
    if (data.status === 'ok') {
        classes = data.classes || [];
        return classes;
    } else {
        throw new Error(data.message || '加载班级列表失败');
    }
}

// 渲染教师卡片
function renderTeacherCards(containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (teachers.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">暂无教师数据</p>';
        return;
    }
    
    teachers.forEach(teacher => {
        const card = createTeacherCard(teacher);
        container.appendChild(card);
    });
    
    // 更新教师总数
    const countId = containerId === 'teachersArea' ? 'totalTeachersCount' : 'totalTeachersCount2';
    document.getElementById(countId).textContent = teachers.length;
}

// 创建教师卡片
function createTeacherCard(teacher) {
    const card = document.createElement('div');
    card.className = 'teacher-card';
    card.draggable = true;
    card.dataset.teacherId = teacher.id;
    card.dataset.teacherName = teacher.username;
    card.dataset.currentRole = teacher.primary_role || '科任老师';
    card.dataset.currentClass = teacher.class_id || '';
    
    let infoText = '';
    if (currentTab === 'role') {
        infoText = teacher.primary_role || '未分配角色';
    } else {
        infoText = teacher.class_name || '未分配班级';
    }
    
    card.innerHTML = `
        <span class="teacher-name">${teacher.username}</span>
        <span class="teacher-info">${infoText}</span>
    `;
    
    return card;
}

// 渲染角色分配区域
function renderRoleBoxes() {
    const grid = document.getElementById('roleAssignmentGrid');
    grid.innerHTML = '';
    
    roles.forEach(role => {
        const box = createRoleBox(role);
        grid.appendChild(box);
    });
}

// 创建角色框
function createRoleBox(role) {
    const box = document.createElement('div');
    box.className = 'assignment-box role-box';
    box.dataset.role = role;
    box.setAttribute('data-role', role);
    
    // 统计该角色的教师数量
    const teachersInRole = teachers.filter(t => (t.primary_role || '科任老师') === role);
    
    box.innerHTML = `
        <div class="assignment-box-header">
            <span class="assignment-box-title">${role}</span>
            <span class="assignment-count">${teachersInRole.length}</span>
        </div>
        <div class="assigned-teachers" data-role="${role}">
            ${teachersInRole.map(t => createAssignedTeacherTag(t, 'role')).join('')}
        </div>
    `;
    
    return box;
}

// 渲染班级分配区域
function renderClassBoxes() {
    const grid = document.getElementById('classAssignmentGrid');
    grid.innerHTML = '';
    
    if (classes.length === 0) {
        grid.innerHTML = '<p class="text-muted text-center">暂无班级数据，请先创建班级</p>';
        return;
    }
    
    classes.forEach(classItem => {
        const box = createClassBox(classItem);
        grid.appendChild(box);
    });
}

// 创建班级框
function createClassBox(classItem) {
    const box = document.createElement('div');
    box.className = 'assignment-box class-box';
    box.dataset.classId = classItem.id;
    
    // 找到分配到该班级的教师
    const teachersInClass = teachers.filter(t => t.class_id == classItem.id);
    
    box.innerHTML = `
        <div class="class-box-header">
            <span class="assignment-box-title">${classItem.class_name}</span>
            <span class="assignment-count">${teachersInClass.length}</span>
        </div>
        <div class="assigned-teachers" data-class-id="${classItem.id}">
            ${teachersInClass.map(t => createAssignedTeacherTag(t, 'class')).join('')}
        </div>
    `;
    
    return box;
}

// 创建已分配教师标签
function createAssignedTeacherTag(teacher, type) {
    return `
        <div class="assigned-teacher" data-teacher-id="${teacher.id}">
            <span class="assigned-teacher-name">${teacher.username}</span>
            <button class="remove-btn" onclick="removeAssignment('${teacher.id}', '${type}')" title="移除">×</button>
        </div>
    `;
}

// 初始化拖拽功能
function initDragAndDrop(type) {
    // 获取所有教师卡片
    const teacherCards = document.querySelectorAll('.teacher-card');
    
    teacherCards.forEach(card => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
    });
    
    // 获取所有分配框
    const assignmentBoxes = document.querySelectorAll('.assignment-box');
    
    assignmentBoxes.forEach(box => {
        box.addEventListener('dragover', handleDragOver);
        box.addEventListener('dragleave', handleDragLeave);
        box.addEventListener('drop', (e) => handleDrop(e, type));
    });
}

// 拖拽开始
function handleDragStart(e) {
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.innerHTML);
    e.dataTransfer.setData('teacherId', e.target.dataset.teacherId);
    e.dataTransfer.setData('teacherName', e.target.dataset.teacherName);
}

// 拖拽结束
function handleDragEnd(e) {
    e.target.classList.remove('dragging');
}

// 拖拽经过
function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    e.currentTarget.classList.add('drag-over');
    return false;
}

// 拖拽离开
function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

// 放下
async function handleDrop(e, type) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    e.preventDefault();
    
    e.currentTarget.classList.remove('drag-over');
    
    const teacherId = e.dataTransfer.getData('teacherId');
    const teacherName = e.dataTransfer.getData('teacherName');
    
    if (!teacherId) return;
    
    if (type === 'role') {
        const role = e.currentTarget.dataset.role;
        await assignRole(teacherId, teacherName, role);
    } else if (type === 'class') {
        const classId = e.currentTarget.dataset.classId;
        await assignClass(teacherId, teacherName, classId);
    }
    
    return false;
}

// 分配角色
async function assignRole(teacherId, teacherName, role) {
    try {
        const response = await fetch(`/api/users/${teacherId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                primary_role: role
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            showToast(`已将 ${teacherName} 的角色设置为 ${role}`, 'success');
            
            // 更新本地数据
            const teacher = teachers.find(t => t.id == teacherId);
            if (teacher) {
                teacher.primary_role = role;
            }
            
            // 重新渲染
            renderTeacherCards('teachersArea');
            renderRoleBoxes();
            initDragAndDrop('role');
        } else {
            showToast('分配失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('分配角色失败:', error);
        showToast('分配失败: ' + error.message, 'error');
    }
}

// 分配班级
async function assignClass(teacherId, teacherName, classId) {
    try {
        const response = await fetch(`/api/users/${teacherId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                class_id: classId
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            const className = classes.find(c => c.id == classId)?.class_name || '未知班级';
            showToast(`已将 ${teacherName} 分配到 ${className}`, 'success');
            
            // 更新本地数据
            const teacher = teachers.find(t => t.id == teacherId);
            if (teacher) {
                teacher.class_id = classId;
                teacher.class_name = className;
            }
            
            // 重新渲染
            renderTeacherCards('teachersArea2');
            renderClassBoxes();
            initDragAndDrop('class');
        } else {
            showToast('分配失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('分配班级失败:', error);
        showToast('分配失败: ' + error.message, 'error');
    }
}

// 移除分配
async function removeAssignment(teacherId, type) {
    const teacher = teachers.find(t => t.id == teacherId);
    if (!teacher) return;
    
    const confirmMsg = type === 'role' 
        ? `确定要移除 ${teacher.username} 的角色吗？` 
        : `确定要移除 ${teacher.username} 的班级分配吗？`;
    
    if (!confirm(confirmMsg)) return;
    
    try {
        const updateData = type === 'role' 
            ? { primary_role: '科任老师' }  // 移除角色时设为默认角色
            : { class_id: null };  // 移除班级
        
        const response = await fetch(`/api/users/${teacherId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            showToast(`已移除 ${teacher.username} 的${type === 'role' ? '角色' : '班级'}分配`, 'success');
            
            // 更新本地数据
            if (type === 'role') {
                teacher.primary_role = '科任老师';
                renderTeacherCards('teachersArea');
                renderRoleBoxes();
                initDragAndDrop('role');
            } else {
                teacher.class_id = null;
                teacher.class_name = null;
                renderTeacherCards('teachersArea2');
                renderClassBoxes();
                initDragAndDrop('class');
            }
        } else {
            showToast('移除失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('移除分配失败:', error);
        showToast('移除失败: ' + error.message, 'error');
    }
}


// ==================== 学科班级分配功能 ====================

let subjects = [];
let currentSelectedTeacher = null;

// 监听学科班级分配标签页
document.getElementById('subject-class-tab').addEventListener('click', function() {
    loadSubjectClassAssignment();
});

// 监听全部分配标签页
document.getElementById('all-assignments-tab').addEventListener('click', function() {
    loadAllAssignments();
});

// 加载学科班级分配
async function loadSubjectClassAssignment() {
    try {
        // 加载教师列表
        await loadTeachers();
        
        // 加载学科列表
        await loadSubjects();
        
        // 加载班级列表
        await loadClasses();
        
        // 填充教师下拉框
        populateTeacherSelect();
        
        // 填充学科下拉框
        populateSubjectSelect();
        
        // 绑定事件
        bindSubjectClassEvents();
        
    } catch (error) {
        console.error('加载学科班级分配失败:', error);
        showToast('加载失败: ' + error.message, 'error');
    }
}

// 加载学科列表
async function loadSubjects() {
    const response = await fetch('/api/subjects');
    const data = await response.json();
    
    if (data.status === 'ok') {
        subjects = data.subjects || [];
        return subjects;
    } else {
        throw new Error(data.message || '加载学科列表失败');
    }
}

// 填充教师下拉框
function populateTeacherSelect() {
    const select = document.getElementById('selectTeacher');
    select.innerHTML = '<option value="">请选择教师</option>';
    
    teachers.forEach(teacher => {
        const option = document.createElement('option');
        option.value = teacher.id;
        option.textContent = `${teacher.username} (${teacher.primary_role || '科任老师'})`;
        option.dataset.role = teacher.primary_role || '科任老师';
        option.dataset.classId = teacher.class_id || '';
        select.appendChild(option);
    });
}

// 填充学科下拉框
function populateSubjectSelect() {
    const select = document.getElementById('selectSubject');
    select.innerHTML = '<option value="">请选择学科</option>';
    
    subjects.forEach(subject => {
        const option = document.createElement('option');
        option.value = subject.id;
        option.textContent = subject.name;
        select.appendChild(option);
    });
}

// 绑定学科班级分配事件
function bindSubjectClassEvents() {
    const teacherSelect = document.getElementById('selectTeacher');
    const subjectSelect = document.getElementById('selectSubject');
    const assignBtn = document.getElementById('btnAssignSubjectClass');
    
    // 教师选择变化
    teacherSelect.addEventListener('change', async function() {
        const teacherId = this.value;
        currentSelectedTeacher = teacherId;
        
        if (teacherId) {
            // 加载该教师的分配情况
            await loadTeacherAssignments(teacherId);
            
            // 检查是否是正班主任
            const selectedOption = this.options[this.selectedIndex];
            const role = selectedOption.dataset.role;
            const classId = selectedOption.dataset.classId;
            
            if (role === '正班主任' && classId) {
                // 正班主任：隐藏班级选择
                document.getElementById('classCheckboxContainer').style.display = 'none';
                showToast('正班主任会自动分配到自己班级的所有学科，无需手动分配', 'info');
            } else {
                // 其他角色：显示班级复选框
                document.getElementById('classCheckboxContainer').style.display = 'block';
                if (subjectSelect.value) {
                    renderClassCheckboxes();
                }
            }
        } else {
            currentSelectedTeacher = null;
            document.getElementById('currentAssignments').innerHTML = '<p class="text-muted text-center py-4">请先选择教师查看分配情况</p>';
            document.getElementById('classCheckboxContainer').style.display = 'none';
        }
    });
    
    // 学科选择变化
    subjectSelect.addEventListener('change', function() {
        if (currentSelectedTeacher && this.value) {
            const teacherSelect = document.getElementById('selectTeacher');
            const selectedOption = teacherSelect.options[teacherSelect.selectedIndex];
            const role = selectedOption.dataset.role;
            
            if (role !== '正班主任') {
                renderClassCheckboxes();
            }
        }
    });
    
    // 分配按钮点击
    assignBtn.addEventListener('click', async function() {
        await assignSubjectToClasses();
    });
}

// 渲染班级复选框
function renderClassCheckboxes() {
    const container = document.getElementById('classCheckboxList');
    container.innerHTML = '';
    
    if (classes.length === 0) {
        container.innerHTML = '<div class="col-12"><p class="text-muted">暂无班级数据</p></div>';
        return;
    }
    
    classes.forEach(classItem => {
        const col = document.createElement('div');
        col.className = 'col-md-3 col-sm-4 col-6';
        
        col.innerHTML = `
            <div class="form-check">
                <input class="form-check-input class-checkbox" type="checkbox" value="${classItem.id}" id="class_${classItem.id}">
                <label class="form-check-label" for="class_${classItem.id}">
                    ${classItem.class_name}
                </label>
            </div>
        `;
        
        container.appendChild(col);
    });
}

// 加载教师的分配情况
async function loadTeacherAssignments(teacherId) {
    try {
        console.log('加载教师分配情况，教师ID:', teacherId);
        const response = await fetch(`/api/teacher-classes/${teacherId}`);
        const data = await response.json();
        
        console.log('API返回数据:', data);
        
        if (data.status === 'ok') {
            renderTeacherAssignments(data.assignments || []);
        } else {
            console.error('API返回错误:', data.message);
            showToast('加载失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('加载教师分配失败:', error);
        showToast('加载失败: ' + error.message, 'error');
    }
}

// 渲染教师分配情况
function renderTeacherAssignments(assignments) {
    const container = document.getElementById('currentAssignments');
    
    console.log('渲染分配情况，数据条数:', assignments.length);
    
    if (assignments.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-4">该教师暂无学科班级分配</p>';
        return;
    }
    
    // 按学科分组
    const groupedBySubject = {};
    assignments.forEach(assignment => {
        const subjectName = assignment.subject_name;
        if (!groupedBySubject[subjectName]) {
            groupedBySubject[subjectName] = [];
        }
        groupedBySubject[subjectName].push(assignment);
    });
    
    console.log('按学科分组后:', groupedBySubject);
    
    let html = '<div class="table-responsive"><table class="table table-hover table-bordered">';
    html += '<thead class="table-light"><tr><th style="width: 150px;">学科</th><th>任教班级</th><th style="width: 100px;">操作</th></tr></thead><tbody>';
    
    for (const subjectName in groupedBySubject) {
        const subjectAssignments = groupedBySubject[subjectName];
        const classNames = subjectAssignments.map(a => a.class_name).join('、');
        const assignmentIds = subjectAssignments.map(a => a.id);
        
        html += `
            <tr>
                <td><strong>${subjectName}</strong></td>
                <td>${classNames}</td>
                <td class="text-center">
                    <button class="btn btn-sm btn-danger" onclick="removeSubjectAssignments([${assignmentIds.join(',')}])">
                        <i class='bx bx-trash'></i> 移除
                    </button>
                </td>
            </tr>
        `;
    }
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// 分配学科到班级
async function assignSubjectToClasses() {
    const teacherId = document.getElementById('selectTeacher').value;
    const subjectId = document.getElementById('selectSubject').value;
    
    if (!teacherId) {
        showToast('请选择教师', 'warning');
        return;
    }
    
    if (!subjectId) {
        showToast('请选择学科', 'warning');
        return;
    }
    
    // 获取选中的班级（从复选框）
    const checkboxes = document.querySelectorAll('.class-checkbox:checked');
    const selectedClasses = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedClasses.length === 0) {
        showToast('请至少选择一个班级', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/teacher-classes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                teacher_id: teacherId,
                subject_id: subjectId,
                class_ids: selectedClasses
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            showToast(data.message || '分配成功', 'success');
            
            // 重新加载教师的分配情况
            await loadTeacherAssignments(teacherId);
            
            // 清空复选框选择
            checkboxes.forEach(cb => cb.checked = false);
        } else {
            showToast('分配失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('分配失败:', error);
        showToast('分配失败: ' + error.message, 'error');
    }
}

// 移除学科分配
async function removeSubjectAssignments(assignmentIds) {
    if (!confirm('确定要移除这些分配吗？')) {
        return;
    }
    
    try {
        // 逐个删除
        for (const id of assignmentIds) {
            const response = await fetch(`/api/teacher-classes/${id}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            if (data.status !== 'ok') {
                throw new Error(data.message);
            }
        }
        
        showToast('移除成功', 'success');
        
        // 重新加载教师的分配情况
        if (currentSelectedTeacher) {
            await loadTeacherAssignments(currentSelectedTeacher);
        }
    } catch (error) {
        console.error('移除失败:', error);
        showToast('移除失败: ' + error.message, 'error');
    }
}


// ==================== 全部分配功能 ====================

let allAssignmentsData = [];

// 加载全部分配
async function loadAllAssignments() {
    try {
        const container = document.getElementById('allAssignmentsList');
        container.innerHTML = '<div class="loading"><div class="spinner"></div><p>加载分配数据中...</p></div>';
        
        // 获取所有教师的分配数据
        const response = await fetch('/api/all-teacher-assignments');
        const data = await response.json();
        
        if (data.status === 'ok') {
            allAssignmentsData = data.assignments || [];
            renderAllAssignments(allAssignmentsData);
            
            // 绑定筛选和搜索事件
            bindAllAssignmentsFilters();
        } else {
            container.innerHTML = `<p class="text-danger text-center py-4">加载失败: ${data.message}</p>`;
        }
    } catch (error) {
        console.error('加载全部分配失败:', error);
        const container = document.getElementById('allAssignmentsList');
        container.innerHTML = `<p class="text-danger text-center py-4">加载失败: ${error.message}</p>`;
    }
}

// 渲染全部分配
function renderAllAssignments(assignments) {
    const container = document.getElementById('allAssignmentsList');
    
    if (assignments.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-4">暂无分配数据</p>';
        return;
    }
    
    let html = '<div class="table-responsive">';
    html += '<table class="table table-hover table-bordered">';
    html += '<thead class="table-light">';
    html += '<tr>';
    html += '<th style="width: 120px;">教师姓名</th>';
    html += '<th style="width: 100px;">角色</th>';
    html += '<th style="width: 120px;">班级</th>';
    html += '<th style="width: 200px;">任教学科</th>';
    html += '<th>学科班级分配</th>';
    html += '</tr>';
    html += '</thead>';
    html += '<tbody>';
    
    assignments.forEach(teacher => {
        html += '<tr>';
        html += `<td><strong>${teacher.username}</strong></td>`;
        html += `<td>`;
        html += `<span class="badge bg-${getRoleBadgeColor(teacher.role)}">${teacher.role}</span>`;
        html += `</td>`;
        html += `<td>${teacher.class_name || '<span class="text-muted">未分配</span>'}</td>`;
        
        // 任教学科列（来自 teacher_subjects 表）
        html += '<td>';
        if (teacher.teacher_subjects && teacher.teacher_subjects.length > 0) {
            html += teacher.teacher_subjects.map(s => `<span class="badge bg-secondary me-1">${s}</span>`).join('');
        } else {
            html += '<span class="text-muted">未分配</span>';
        }
        html += '</td>';
        
        // 学科班级分配列（来自 teaching_assignments 表）
        html += '<td>';
        if (teacher.subject_assignments && teacher.subject_assignments.length > 0) {
            const assignmentTexts = teacher.subject_assignments.map(assignment => {
                const classText = assignment.classes.join('、');
                let style = '';
                let suffix = '';
                
                if (!assignment.has_class_assignment) {
                    // 未分配班级，灰色显示
                    style = 'color: #999;';
                } else if (assignment.auto_assigned) {
                    // 自动分配（正副班主任），添加标识
                    suffix = ' <small class="text-muted">(自动)</small>';
                }
                
                return `<div style="${style}"><strong>${assignment.subject_name}:</strong> ${classText}${suffix}</div>`;
            });
            html += assignmentTexts.join('');
        } else {
            html += '<span class="text-muted">未分配</span>';
        }
        html += '</td>';
        
        html += '</tr>';
    });
    
    html += '</tbody>';
    html += '</table>';
    html += '</div>';
    
    // 添加说明
    html += '<div class="alert alert-info mt-3">';
    html += '<small>';
    html += '<strong>说明：</strong><br>';
    html += '• <strong>任教学科</strong>：教师可以任教的学科（在学科管理中分配）<br>';
    html += '• <strong>学科班级分配</strong>：教师在具体哪些班级任教哪些学科<br>';
    html += '• 正班主任和副班主任的任教学科会自动关联到其班级（标记为"自动"）<br>';
    html += '• 如需在其他班级任教，请在"学科班级分配"标签页中额外添加<br>';
    html += '• 灰色文字表示学科已分配但未指定具体班级';
    html += '</small>';
    html += '</div>';
    
    container.innerHTML = html;
}

// 获取角色徽章颜色
function getRoleBadgeColor(role) {
    const colorMap = {
        '正班主任': 'primary',
        '副班主任': 'info',
        '科任老师': 'secondary',
        '行政': 'warning',
        '校级领导': 'success'
    };
    return colorMap[role] || 'secondary';
}

// 绑定全部分配的筛选和搜索事件
function bindAllAssignmentsFilters() {
    const filterRole = document.getElementById('filterRole');
    const searchTeacher = document.getElementById('searchTeacher');
    const btnRefresh = document.getElementById('btnRefreshAll');
    
    // 角色筛选
    filterRole.addEventListener('change', function() {
        filterAndRenderAssignments();
    });
    
    // 教师搜索
    searchTeacher.addEventListener('input', function() {
        filterAndRenderAssignments();
    });
    
    // 刷新按钮
    btnRefresh.addEventListener('click', function() {
        loadAllAssignments();
    });
}

// 筛选并渲染分配数据
function filterAndRenderAssignments() {
    const roleFilter = document.getElementById('filterRole').value;
    const searchText = document.getElementById('searchTeacher').value.trim().toLowerCase();
    
    let filtered = allAssignmentsData;
    
    // 按角色筛选
    if (roleFilter) {
        filtered = filtered.filter(t => t.role === roleFilter);
    }
    
    // 按姓名搜索
    if (searchText) {
        filtered = filtered.filter(t => t.username.toLowerCase().includes(searchText));
    }
    
    renderAllAssignments(filtered);
}
