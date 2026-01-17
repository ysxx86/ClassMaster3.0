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
