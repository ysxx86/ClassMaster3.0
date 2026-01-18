/**
 * 教师信息确认组件
 * 用于教师登录后确认和修改任教信息
 */

// 全局变量
let teacherInfo = null;
let allSubjects = [];
let allClasses = [];

// 检查是否需要确认信息
async function checkTeacherInfoConfirmation() {
    try {
        const response = await fetch('/api/teacher-info/check-confirmation');
        const data = await response.json();
        
        if (data.status === 'ok' && data.need_confirm) {
            // 需要确认，显示弹窗
            await showTeacherInfoModal(data.reason, data.current_semester);
        }
    } catch (error) {
        console.error('检查教师信息确认状态失败:', error);
    }
}

// 显示教师信息确认弹窗
async function showTeacherInfoModal(reason, currentSemester) {
    try {
        // 加载教师信息
        await loadTeacherInfo();
        
        // 加载学科和班级列表
        await loadSubjectsAndClasses();
        
        // 创建并显示模态框
        createTeacherInfoModal(reason, currentSemester);
        
        const modal = new bootstrap.Modal(document.getElementById('teacherInfoModal'), {
            backdrop: 'static',  // 不允许点击背景关闭
            keyboard: false      // 不允许ESC关闭
        });
        modal.show();
        
    } catch (error) {
        console.error('显示教师信息弹窗失败:', error);
    }
}

// 加载教师信息
async function loadTeacherInfo() {
    const response = await fetch('/api/teacher-info/my-info');
    const data = await response.json();
    
    if (data.status === 'ok') {
        teacherInfo = data.info;
    } else {
        throw new Error(data.message);
    }
}

// 加载学科和班级列表
async function loadSubjectsAndClasses() {
    // 加载学科
    const subjectsResponse = await fetch('/api/subjects');
    const subjectsData = await subjectsResponse.json();
    if (subjectsData.status === 'ok') {
        allSubjects = subjectsData.subjects;
    }
    
    // 加载班级
    const classesResponse = await fetch('/api/classes');
    const classesData = await classesResponse.json();
    if (classesData.status === 'ok') {
        allClasses = classesData.classes;
    }
}

// 创建教师信息模态框
function createTeacherInfoModal(reason, currentSemester) {
    // 如果已存在，先删除
    const existingModal = document.getElementById('teacherInfoModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 根据原因显示不同的提示
    let reasonText = '';
    if (reason === 'never_confirmed') {
        reasonText = '欢迎使用系统！请确认您的任教信息。';
    } else if (reason === 'semester_changed') {
        reasonText = '新学期开始了！请确认您本学期的任教信息。';
    } else if (reason === 'long_time_no_confirm') {
        reasonText = '距离上次确认已超过90天，请重新确认您的任教信息。';
    }
    
    const modalHTML = `
        <div class="modal fade" id="teacherInfoModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class='bx bx-user-check'></i> 确认任教信息 - ${currentSemester}
                        </h5>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <i class='bx bx-info-circle'></i> ${reasonText} 请查看您的任教信息，如需修改请点击"修改"按钮，不需要修改直接点击"关闭"即可。
                        </div>
                        
                        <!-- 基本信息 -->
                        <div class="info-section mb-4">
                            <h6 class="section-title">基本信息</h6>
                            <div class="row">
                                <div class="col-md-6 mb-2">
                                    <strong>教师姓名：</strong>${teacherInfo.username}
                                </div>
                                <div class="col-md-6 mb-2">
                                    <strong>角色：</strong>
                                    <span class="badge bg-primary">${teacherInfo.role}</span>
                                </div>
                                <div class="col-md-12 mb-2">
                                    <strong>班级：</strong>${teacherInfo.class_name || '<span class="text-muted">未分配</span>'}
                                </div>
                            </div>
                        </div>
                        
                        <!-- 任教学科 -->
                        <div class="info-section mb-4">
                            <h6 class="section-title">
                                任教学科
                                <button class="btn btn-sm btn-outline-primary float-end" onclick="editSubjects()">
                                    <i class='bx bx-edit'></i> 修改
                                </button>
                            </h6>
                            <div id="subjectsDisplay">
                                ${renderSubjectsDisplay()}
                            </div>
                            <div id="subjectsEdit" style="display: none;">
                                ${renderSubjectsEdit()}
                            </div>
                        </div>
                        
                        <!-- 学科班级分配 -->
                        <div class="info-section mb-4">
                            <h6 class="section-title">
                                学科班级分配
                                <button class="btn btn-sm btn-outline-primary float-end" onclick="editAssignments()">
                                    <i class='bx bx-edit'></i> 修改
                                </button>
                            </h6>
                            <div id="assignmentsDisplay">
                                ${renderAssignmentsDisplay()}
                            </div>
                            <div id="assignmentsEdit" style="display: none;">
                                ${renderAssignmentsEdit()}
                            </div>
                        </div>
                        
                        <div class="alert alert-warning">
                            <i class='bx bx-error-circle'></i> 
                            <strong>重要提示：</strong>请仔细核对以上信息，确保准确无误。如有错误，请点击"修改"按钮进行更正。
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="handleModalClose()">
                            <i class='bx bx-x'></i> 关闭
                        </button>
                        <button type="button" class="btn btn-primary" onclick="saveChanges()">
                            <i class='bx bx-save'></i> 保存修改
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// 渲染学科显示
function renderSubjectsDisplay() {
    if (!teacherInfo.subjects || teacherInfo.subjects.length === 0) {
        return '<p class="text-muted">暂无任教学科</p>';
    }
    
    return teacherInfo.subjects.map(s => 
        `<span class="badge bg-secondary me-2 mb-2">${s.name}</span>`
    ).join('');
}

// 渲染学科编辑
function renderSubjectsEdit() {
    let html = '<div class="row">';
    
    allSubjects.forEach(subject => {
        const checked = teacherInfo.subjects.some(s => s.id === subject.id);
        html += `
            <div class="col-md-4 col-sm-6 mb-2">
                <div class="form-check">
                    <input class="form-check-input subject-checkbox" type="checkbox" 
                           value="${subject.id}" id="subject_${subject.id}" ${checked ? 'checked' : ''}>
                    <label class="form-check-label" for="subject_${subject.id}">
                        ${subject.name}
                    </label>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    html += `
        <div class="mt-3">
            <button class="btn btn-sm btn-success" onclick="saveSubjects()">
                <i class='bx bx-save'></i> 保存
            </button>
            <button class="btn btn-sm btn-secondary" onclick="cancelEditSubjects()">
                <i class='bx bx-x'></i> 取消
            </button>
        </div>
    `;
    
    return html;
}

// 渲染学科班级分配显示
function renderAssignmentsDisplay() {
    if (!teacherInfo.assignments || teacherInfo.assignments.length === 0) {
        return '<p class="text-muted">暂无学科班级分配</p>';
    }
    
    // 按学科分组
    const grouped = {};
    teacherInfo.assignments.forEach(a => {
        if (!grouped[a.subject]) {
            grouped[a.subject] = [];
        }
        grouped[a.subject].push(a.class_name);
    });
    
    let html = '<div class="table-responsive"><table class="table table-sm table-bordered">';
    html += '<thead><tr><th>学科</th><th>任教班级</th></tr></thead><tbody>';
    
    for (const [subject, classes] of Object.entries(grouped)) {
        html += `<tr><td><strong>${subject}</strong></td><td>${classes.join('、')}</td></tr>`;
    }
    
    html += '</tbody></table></div>';
    return html;
}

// 渲染学科班级分配编辑
function renderAssignmentsEdit() {
    let html = '<div id="assignmentEditArea">';
    html += '<p class="text-muted">请为每个学科选择任教的班级：</p>';
    
    // 为每个选中的学科创建班级选择器
    teacherInfo.subjects.forEach(subject => {
        const subjectAssignments = teacherInfo.assignments.filter(a => a.subject === subject.name);
        const selectedClasses = subjectAssignments.map(a => a.class_id);
        
        html += `
            <div class="mb-3 p-3 border rounded">
                <h6>${subject.name}</h6>
                <div class="row">
        `;
        
        allClasses.forEach(cls => {
            const checked = selectedClasses.includes(String(cls.id));
            html += `
                <div class="col-md-3 col-sm-4 col-6 mb-2">
                    <div class="form-check">
                        <input class="form-check-input assignment-checkbox" type="checkbox" 
                               value="${cls.id}" id="assign_${subject.id}_${cls.id}" 
                               data-subject="${subject.name}" ${checked ? 'checked' : ''}>
                        <label class="form-check-label" for="assign_${subject.id}_${cls.id}">
                            ${cls.class_name}
                        </label>
                    </div>
                </div>
            `;
        });
        
        html += '</div></div>';
    });
    
    html += '</div>';
    html += `
        <div class="mt-3">
            <button class="btn btn-sm btn-success" onclick="saveAssignments()">
                <i class='bx bx-save'></i> 保存
            </button>
            <button class="btn btn-sm btn-secondary" onclick="cancelEditAssignments()">
                <i class='bx bx-x'></i> 取消
            </button>
        </div>
    `;
    
    return html;
}

// 编辑学科
function editSubjects() {
    document.getElementById('subjectsDisplay').style.display = 'none';
    document.getElementById('subjectsEdit').style.display = 'block';
}

// 取消编辑学科
function cancelEditSubjects() {
    document.getElementById('subjectsDisplay').style.display = 'block';
    document.getElementById('subjectsEdit').style.display = 'none';
}

// 保存学科
async function saveSubjects() {
    const checkboxes = document.querySelectorAll('.subject-checkbox:checked');
    const selectedSubjects = Array.from(checkboxes).map(cb => ({
        id: parseInt(cb.value),
        name: allSubjects.find(s => s.id === parseInt(cb.value)).name
    }));
    
    if (selectedSubjects.length === 0) {
        alert('请至少选择一个学科');
        return;
    }
    
    // 更新本地数据
    teacherInfo.subjects = selectedSubjects;
    
    // 重新渲染
    document.getElementById('subjectsDisplay').innerHTML = renderSubjectsDisplay();
    document.getElementById('subjectsDisplay').style.display = 'block';
    document.getElementById('subjectsEdit').style.display = 'none';
    
    // 同时更新学科班级分配编辑区域
    document.getElementById('assignmentsEdit').innerHTML = renderAssignmentsEdit();
}

// 编辑学科班级分配
function editAssignments() {
    if (!teacherInfo.subjects || teacherInfo.subjects.length === 0) {
        alert('请先选择任教学科');
        return;
    }
    
    document.getElementById('assignmentsDisplay').style.display = 'none';
    document.getElementById('assignmentsEdit').style.display = 'block';
}

// 取消编辑学科班级分配
function cancelEditAssignments() {
    document.getElementById('assignmentsDisplay').style.display = 'block';
    document.getElementById('assignmentsEdit').style.display = 'none';
}

// 保存学科班级分配
async function saveAssignments() {
    const checkboxes = document.querySelectorAll('.assignment-checkbox:checked');
    const assignments = Array.from(checkboxes).map(cb => ({
        class_id: parseInt(cb.value),
        class_name: allClasses.find(c => c.id === parseInt(cb.value)).class_name,
        subject: cb.dataset.subject
    }));
    
    // 更新本地数据
    teacherInfo.assignments = assignments;
    
    // 重新渲染
    document.getElementById('assignmentsDisplay').innerHTML = renderAssignmentsDisplay();
    document.getElementById('assignmentsDisplay').style.display = 'block';
    document.getElementById('assignmentsEdit').style.display = 'none';
}

// 显示修改选项
function showModifyOptions() {
    alert('请点击各部分的"修改"按钮进行编辑');
}

// 处理模态框关闭
function handleModalClose() {
    // 标记为已查看（即使没有修改）
    markAsViewed();
    
    // 添加右上角按钮
    addTeacherInfoButton();
}

// 标记为已查看
async function markAsViewed() {
    try {
        const response = await fetch('/api/teacher-info/mark-viewed', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status === 'ok') {
            console.log('已标记为已查看');
        }
    } catch (error) {
        console.error('标记失败:', error);
    }
}

// 保存修改
async function saveChanges() {
    try {
        // 保存修改
        const subjectIds = teacherInfo.subjects.map(s => s.id);
        const assignments = teacherInfo.assignments.map(a => ({
            class_id: a.class_id,
            subject_name: a.subject
        }));
        
        console.log('准备保存的数据:', {
            subjects: subjectIds,
            assignments: assignments
        });
        
        // 更新信息
        const updateResponse = await fetch('/api/teacher-info/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                subjects: subjectIds,
                assignments: assignments
            })
        });
        
        const updateData = await updateResponse.json();
        console.log('更新响应:', updateData);
        
        if (updateData.status !== 'ok') {
            throw new Error(updateData.message);
        }
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('teacherInfoModal'));
        modal.hide();
        
        // 显示成功提示
        showSuccessToast('任教信息保存成功！');
        
        // 添加右上角按钮
        addTeacherInfoButton();
        
    } catch (error) {
        console.error('保存失败:', error);
        alert('保存失败: ' + error.message);
    }
}

// 确认教师信息（保留用于兼容）
async function confirmTeacherInfo() {
    await saveChanges();
}

// 显示成功提示
function showSuccessToast(message) {
    // 如果页面有Toast组件，使用它
    if (typeof showToast === 'function') {
        showToast(message, 'success');
    } else {
        alert(message);
    }
}

// 页面加载完成后检查
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(checkTeacherInfoConfirmation, 1000);
    });
} else {
    setTimeout(checkTeacherInfoConfirmation, 1000);
}


// 添加右上角任教信息按钮
function addTeacherInfoButton() {
    // 检查是否已存在
    if (document.getElementById('teacherInfoButton')) {
        return;
    }
    
    const buttonHTML = `
        <div class="teacher-info-button-container" id="teacherInfoButton">
            <button class="teacher-info-btn" onclick="openTeacherInfoModal()" title="我的任教信息">
                <i class='bx bx-user-check'></i>
                <span>任教信息</span>
            </button>
        </div>
    `;
    
    // 添加到页面右上角
    document.body.insertAdjacentHTML('beforeend', buttonHTML);
}

// 打开任教信息模态框（用于再次修改）
async function openTeacherInfoModal() {
    try {
        // 重新加载最新数据
        await loadTeacherInfo();
        await loadSubjectsAndClasses();
        
        // 创建模态框（允许修改）
        createEditableTeacherInfoModal();
        
        const modal = new bootstrap.Modal(document.getElementById('teacherInfoModal'));
        modal.show();
        
    } catch (error) {
        console.error('打开任教信息失败:', error);
        alert('打开失败: ' + error.message);
    }
}

// 创建可编辑的教师信息模态框
function createEditableTeacherInfoModal() {
    // 如果已存在，先删除
    const existingModal = document.getElementById('teacherInfoModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    const modalHTML = `
        <div class="modal fade" id="teacherInfoModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class='bx bx-user-check'></i> 我的任教信息 - ${teacherInfo.teacher_semester || '当前学期'}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="关闭"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <i class='bx bx-info-circle'></i> 您可以随时修改任教信息，修改后会立即生效。
                        </div>
                        
                        <!-- 基本信息 -->
                        <div class="info-section mb-4">
                            <h6 class="section-title">基本信息</h6>
                            <div class="row">
                                <div class="col-md-6 mb-2">
                                    <strong>教师姓名：</strong>${teacherInfo.username}
                                </div>
                                <div class="col-md-6 mb-2">
                                    <strong>角色：</strong>
                                    <span class="badge bg-primary">${teacherInfo.role}</span>
                                </div>
                                <div class="col-md-12 mb-2">
                                    <strong>班级：</strong>${teacherInfo.class_name || '<span class="text-muted">未分配</span>'}
                                </div>
                            </div>
                        </div>
                        
                        <!-- 任教学科 -->
                        <div class="info-section mb-4">
                            <h6 class="section-title">
                                任教学科
                                <button class="btn btn-sm btn-outline-primary float-end" onclick="editSubjects()">
                                    <i class='bx bx-edit'></i> 修改
                                </button>
                            </h6>
                            <div id="subjectsDisplay">
                                ${renderSubjectsDisplay()}
                            </div>
                            <div id="subjectsEdit" style="display: none;">
                                ${renderSubjectsEdit()}
                            </div>
                        </div>
                        
                        <!-- 学科班级分配 -->
                        <div class="info-section mb-4">
                            <h6 class="section-title">
                                学科班级分配
                                <button class="btn btn-sm btn-outline-primary float-end" onclick="editAssignments()">
                                    <i class='bx bx-edit'></i> 修改
                                </button>
                            </h6>
                            <div id="assignmentsDisplay">
                                ${renderAssignmentsDisplay()}
                            </div>
                            <div id="assignmentsEdit" style="display: none;">
                                ${renderAssignmentsEdit()}
                            </div>
                        </div>
                        
                        <div class="alert alert-success">
                            <i class='bx bx-check-circle'></i> 
                            <strong>最后确认时间：</strong>${teacherInfo.last_confirmed_date || '未确认'}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class='bx bx-x'></i> 关闭
                        </button>
                        <button type="button" class="btn btn-primary" onclick="saveAndConfirmInfo()">
                            <i class='bx bx-save'></i> 保存修改
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// 保存并确认信息（用于再次修改）
async function saveAndConfirmInfo() {
    await confirmTeacherInfo();
}

// 页面加载时检查是否已确认，如果已确认则添加按钮
async function checkAndAddButton() {
    try {
        const response = await fetch('/api/teacher-info/check-confirmation');
        const data = await response.json();
        
        // 如果不需要确认（已确认过），添加按钮
        if (data.status === 'ok' && !data.need_confirm) {
            addTeacherInfoButton();
        }
    } catch (error) {
        console.error('检查确认状态失败:', error);
    }
}

// 修改页面加载逻辑
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            checkTeacherInfoConfirmation();
            checkAndAddButton();
        }, 1000);
    });
} else {
    setTimeout(() => {
        checkTeacherInfoConfirmation();
        checkAndAddButton();
    }, 1000);
}
