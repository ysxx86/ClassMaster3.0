// 班主任绩效考核管理系统 - 前端脚本

let currentUser = null;
let teachers = [];
let items = [];
let evaluators = [];
let autoRefreshInterval = null; // 自动刷新定时器
let lastDataHash = null; // 用于检测数据变化

// 页面加载完成后初始化
$(document).ready(function() {
    // 获取当前用户信息
    getCurrentUser();
    
    // 绑定事件
    $('#score-semester').change(loadScoreMatrix);
    $('#result-semester').change(loadResults);
    $('#calculate-btn').click(calculateResults);
    $('#add-item-btn').click(showAddItemModal);
    $('#add-evaluator-btn').click(showAddEvaluatorModal);
    $('#refresh-btn').click(function() {
        loadScoreMatrix();
        showToast('数据已刷新', 'success');
    });
    
    // 标签切换事件
    $('button[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        const target = $(e.target).attr('data-bs-target');
        if (target === '#item-panel') {
            loadItems();
            stopAutoRefresh(); // 停止自动刷新
        } else if (target === '#evaluator-panel') {
            loadEvaluators();
            stopAutoRefresh();
        } else if (target === '#teacher-panel') {
            loadTeachers();
            stopAutoRefresh();
        } else if (target === '#result-panel') {
            loadResults();
            stopAutoRefresh();
        } else if (target === '#score-panel') {
            loadScoreMatrix();
            startAutoRefresh(); // 启动自动刷新
        }
    });
    
    // 初始加载评分矩阵
    loadScoreMatrix();
    
    // 启动自动刷新（仅在评分页面）
    startAutoRefresh();
    
    // 页面失去焦点时停止刷新，获得焦点时恢复
    $(window).on('blur', function() {
        stopAutoRefresh();
    });
    
    $(window).on('focus', function() {
        // 检查当前是否在评分标签页
        if ($('#score-panel').hasClass('active')) {
            startAutoRefresh();
            loadScoreMatrix(); // 立即刷新一次
        }
    });
});

// 启动自动刷新
function startAutoRefresh() {
    // 先清除已有的定时器
    stopAutoRefresh();
    
    // 每30秒自动刷新一次
    autoRefreshInterval = setInterval(function() {
        console.log('自动刷新数据...');
        loadScoreMatrixSilent(); // 静默刷新，不显示加载动画
    }, 30000); // 30秒
    
    console.log('✅ 自动刷新已启动（每30秒）');
}

// 停止自动刷新
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('⏸️  自动刷新已停止');
    }
}

// 静默加载评分矩阵（不显示加载动画）
function loadScoreMatrixSilent() {
    const semester = $('#score-semester').val();
    
    $.ajax({
        url: `/api/performance/scores/${semester}`,
        method: 'GET',
        success: function(response) {
            if (response.status === 'success') {
                // 计算数据哈希值，检测是否有变化
                const newDataHash = JSON.stringify({
                    teacherCount: response.teachers.length,
                    teacherIds: response.teachers.map(t => t.id).sort().join(',')
                });
                
                // 如果数据有变化，才更新界面
                if (newDataHash !== lastDataHash) {
                    console.log('🔄 检测到数据变化，更新界面');
                    lastDataHash = newDataHash;
                    renderScoreMatrix(response.teachers, response.items, response.scores, semester);
                    showToast('数据已自动更新', 'info');
                } else {
                    console.log('✓ 数据无变化');
                }
            }
        },
        error: function() {
            console.error('自动刷新失败');
        }
    });
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 创建toast元素（如果不存在）
    if ($('#auto-refresh-toast').length === 0) {
        $('body').append(`
            <div id="auto-refresh-toast" class="toast-container position-fixed bottom-0 end-0 p-3" style="z-index: 9999;">
                <div class="toast" role="alert">
                    <div class="toast-header">
                        <i class='bx bx-info-circle me-2'></i>
                        <strong class="me-auto">系统提示</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                    </div>
                    <div class="toast-body"></div>
                </div>
            </div>
        `);
    }
    
    const $toast = $('#auto-refresh-toast .toast');
    const $body = $toast.find('.toast-body');
    
    // 设置消息和样式
    $body.text(message);
    $toast.removeClass('bg-success bg-info bg-warning bg-danger');
    
    if (type === 'success') {
        $toast.addClass('bg-success text-white');
    } else if (type === 'info') {
        $toast.addClass('bg-info text-white');
    } else if (type === 'warning') {
        $toast.addClass('bg-warning');
    } else if (type === 'danger') {
        $toast.addClass('bg-danger text-white');
    }
    
    // 显示toast
    const toast = new bootstrap.Toast($toast[0], {
        autohide: true,
        delay: 3000
    });
    toast.show();
}

// 获取当前用户信息
function getCurrentUser() {
    $.ajax({
        url: '/api/current-user',
        method: 'GET',
        success: function(response) {
            if (response.status === 'success') {
                currentUser = response.user;
                
                // 如果是管理员，显示管理标签
                if (currentUser.is_admin) {
                    $('#admin-tabs, #admin-tabs2, #admin-tabs3').show();
                    $('#calculate-btn').show();
                }
                
                // 加载初始数据
                loadScoreMatrix();
                loadResults();
            }
        },
        error: function() {
            alert('获取用户信息失败');
        }
    });
}

// ==================== 评分录入（矩阵式） ====================

function loadScoreMatrix() {
    const semester = $('#score-semester').val();
    
    $('#score-content').html('<div class="loading"><i class="bx bx-loader-alt bx-spin"></i><p>加载中...</p></div>');
    
    $.ajax({
        url: `/api/performance/scores/${semester}`,
        method: 'GET',
        success: function(response) {
            if (response.status === 'success') {
                // 更新数据哈希
                lastDataHash = JSON.stringify({
                    teacherCount: response.teachers.length,
                    teacherIds: response.teachers.map(t => t.id).sort().join(',')
                });
                
                renderScoreMatrix(response.teachers, response.items, response.scores, semester);
            }
        },
        error: function() {
            $('#score-content').html('<div class="alert alert-danger">加载评分表失败</div>');
        }
    });
}

function renderScoreMatrix(teachers, items, scores, semester) {
    if (teachers.length === 0) {
        $('#score-content').html(`
            <div class="empty-state">
                <i class='bx bx-user-circle'></i>
                <p>暂无正班主任，请先在教师管理中设置教师角色</p>
            </div>
        `);
        return;
    }
    
    // 构建表格
    let html = '<div class="table-responsive"><table class="table table-bordered table-hover table-sm">';
    
    // 表头 - 第一行：类别
    html += '<thead><tr><th rowspan="2" class="text-center align-middle" style="min-width:100px;">教师</th>';
    
    let currentCategory = '';
    let categorySpan = 0;
    let categoryPositions = [];
    
    items.forEach(function(item, index) {
        if (item.category !== currentCategory) {
            if (currentCategory !== '') {
                categoryPositions.push({category: currentCategory, span: categorySpan});
            }
            currentCategory = item.category;
            categorySpan = 1;
        } else {
            categorySpan++;
        }
        
        if (index === items.length - 1) {
            categoryPositions.push({category: currentCategory, span: categorySpan});
        }
    });
    
    categoryPositions.forEach(function(cat) {
        html += `<th colspan="${cat.span}" class="text-center category-header">${cat.category}</th>`;
    });
    html += '</tr>';
    
    // 表头 - 第二行：项目名称
    html += '<tr>';
    items.forEach(function(item) {
        html += `<th class="text-center" style="min-width:120px;" title="${item.item_name}">${item.item_name.replace(/\d+%/, '')}<br><small>(${item.weight}%)</small></th>`;
    });
    html += '</tr></thead>';
    
    // 表体 - 每个教师一行
    html += '<tbody>';
    teachers.forEach(function(teacher) {
        html += `<tr>`;
        html += `<td class="text-center align-middle"><strong>${teacher.username}</strong><br><small class="text-muted">${teacher.class_name || '-'}</small></td>`;
        
        items.forEach(function(item) {
            const key = `${teacher.id}_${item.id}`;
            const scoreData = scores[key] || [];
            
            // 显示已有评分
            let scoreDisplay = '';
            if (scoreData.length > 0) {
                scoreDisplay = scoreData.map(s => `<div class="score-item" title="${s.evaluator_name}">${s.score}</div>`).join('');
            }
            
            html += `<td class="text-center score-cell" data-teacher-id="${teacher.id}" data-item-id="${item.id}">`;
            html += `<div class="score-display">${scoreDisplay}</div>`;
            html += `<input type="number" class="form-control form-control-sm score-input" 
                           data-teacher-id="${teacher.id}" 
                           data-item-id="${item.id}"
                           min="0" max="100" step="0.1" 
                           placeholder="评分"
                           style="display:none;">`;
            html += `<button class="btn btn-sm btn-primary btn-score-edit mt-1" 
                            data-teacher-id="${teacher.id}" 
                            data-item-id="${item.id}">
                        <i class='bx bx-edit'></i>
                     </button>`;
            html += `</td>`;
        });
        
        html += `</tr>`;
    });
    html += '</tbody></table></div>';
    
    $('#score-content').html(html);
    
    // 绑定编辑按钮事件
    $('.btn-score-edit').click(function() {
        const teacherId = $(this).data('teacher-id');
        const itemId = $(this).data('item-id');
        const $cell = $(this).closest('.score-cell');
        const $input = $cell.find('.score-input');
        const $display = $cell.find('.score-display');
        
        if ($input.is(':visible')) {
            // 保存评分
            const score = $input.val();
            if (score) {
                saveScore(teacherId, itemId, score, semester, function() {
                    loadScoreMatrix(); // 重新加载
                });
            } else {
                $input.hide();
                $display.show();
                $(this).html('<i class="bx bx-edit"></i>');
            }
        } else {
            // 显示输入框
            $input.show().focus();
            $display.hide();
            $(this).html('<i class="bx bx-save"></i>');
        }
    });
}

function saveScore(teacherId, itemId, score, semester, callback) {
    $.ajax({
        url: '/api/performance/scores',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            teacher_id: teacherId,
            item_id: itemId,
            score: parseFloat(score),
            semester: semester
        }),
        success: function(response) {
            if (response.status === 'success') {
                if (callback) callback();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '保存评分失败');
        }
    });
}

// ==================== 考核结果 ====================

function loadResults() {
    const semester = $('#result-semester').val();
    
    $('#result-content').html('<div class="loading"><i class="bx bx-loader-alt bx-spin"></i><p>加载中...</p></div>');
    
    $.ajax({
        url: `/api/performance/results/${semester}`,
        method: 'GET',
        success: function(response) {
            if (response.status === 'success') {
                renderResults(response.results);
            }
        },
        error: function() {
            $('#result-content').html('<div class="alert alert-danger">加载考核结果失败</div>');
        }
    });
}

function renderResults(results) {
    if (results.length === 0) {
        $('#result-content').html(`
            <div class="empty-state">
                <i class='bx bx-bar-chart-alt-2'></i>
                <p>暂无考核结果，请先完成评分并计算结果</p>
            </div>
        `);
        return;
    }
    
    let html = '<table class="table table-bordered table-hover">';
    html += `
        <thead>
            <tr>
                <th width="10%">排名</th>
                <th width="20%">教师姓名</th>
                <th width="15%">角色</th>
                <th width="25%">班级</th>
                <th width="15%">总分</th>
                <th width="15%">年段排名</th>
            </tr>
        </thead>
        <tbody>
    `;
    
    results.forEach(function(result) {
        let rankBadge = '';
        if (result.rank === 1) {
            rankBadge = '<span class="badge rank-1 rank-badge">🥇 第1名</span>';
        } else if (result.rank === 2) {
            rankBadge = '<span class="badge rank-2 rank-badge">🥈 第2名</span>';
        } else if (result.rank === 3) {
            rankBadge = '<span class="badge rank-3 rank-badge">🥉 第3名</span>';
        } else {
            rankBadge = `<span class="badge bg-secondary rank-badge">第${result.rank}名</span>`;
        }
        
        html += `
            <tr>
                <td class="text-center">${rankBadge}</td>
                <td>${result.teacher_name}</td>
                <td><span class="badge bg-info">${result.role}</span></td>
                <td>${result.class_name || '-'}</td>
                <td class="text-center"><strong>${result.total_score}</strong></td>
                <td class="text-center">${result.rank}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    
    $('#result-content').html(html);
}

function calculateResults() {
    const semester = $('#result-semester').val();
    
    if (!confirm('确定要重新计算考核结果吗？这将覆盖现有结果。')) {
        return;
    }
    
    $.ajax({
        url: `/api/performance/calculate/${semester}`,
        method: 'POST',
        success: function(response) {
            if (response.status === 'success') {
                alert('考核结果计算完成');
                loadResults();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '计算考核结果失败');
        }
    });
}

// ==================== 考核项目管理 ====================

function loadItems() {
    $('#item-content').html('<div class="loading"><i class="bx bx-loader-alt bx-spin"></i><p>加载中...</p></div>');
    
    $.ajax({
        url: '/api/performance/items',
        method: 'GET',
        success: function(response) {
            if (response.status === 'success') {
                items = response.items;
                renderItems(items);
            }
        },
        error: function() {
            $('#item-content').html('<div class="alert alert-danger">加载考核项目失败</div>');
        }
    });
}

function renderItems(items) {
    let html = '<table class="table table-bordered table-hover">';
    html += `
        <thead>
            <tr>
                <th width="15%">类别</th>
                <th width="30%">项目名称</th>
                <th width="10%">权重</th>
                <th width="30%">说明</th>
                <th width="15%">操作</th>
            </tr>
        </thead>
        <tbody>
    `;
    
    let currentCategory = '';
    items.forEach(function(item) {
        if (item.category !== currentCategory) {
            html += `<tr class="category-header"><td colspan="5">${item.category}</td></tr>`;
            currentCategory = item.category;
        }
        
        html += `
            <tr>
                <td>${item.category}</td>
                <td>${item.item_name}</td>
                <td>${item.weight}%</td>
                <td>${item.description || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-warning edit-item-btn" data-id="${item.id}">
                        <i class='bx bx-edit'></i> 编辑
                    </button>
                    <button class="btn btn-sm btn-danger delete-item-btn" data-id="${item.id}">
                        <i class='bx bx-trash'></i> 删除
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    
    $('#item-content').html(html);
    
    // 绑定按钮事件
    $('.edit-item-btn').click(function() {
        const itemId = $(this).data('id');
        editItem(itemId);
    });
    
    $('.delete-item-btn').click(function() {
        const itemId = $(this).data('id');
        deleteItem(itemId);
    });
}

function showAddItemModal() {
    // 这里可以使用Bootstrap Modal，简化起见使用prompt
    const category = prompt('请输入类别（如：计划总结、常规教育等）：');
    if (!category) return;
    
    const itemName = prompt('请输入项目名称：');
    if (!itemName) return;
    
    const weight = prompt('请输入权重（百分比）：');
    if (!weight) return;
    
    const description = prompt('请输入说明（可选）：') || '';
    
    $.ajax({
        url: '/api/performance/items',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            category: category,
            item_name: itemName,
            weight: parseFloat(weight),
            description: description
        }),
        success: function(response) {
            if (response.status === 'success') {
                alert('考核项目添加成功');
                loadItems();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '添加考核项目失败');
        }
    });
}

function editItem(itemId) {
    const item = items.find(i => i.id === itemId);
    if (!item) return;
    
    const category = prompt('请输入类别：', item.category);
    if (!category) return;
    
    const itemName = prompt('请输入项目名称：', item.item_name);
    if (!itemName) return;
    
    const weight = prompt('请输入权重：', item.weight);
    if (!weight) return;
    
    const description = prompt('请输入说明：', item.description || '') || '';
    
    $.ajax({
        url: `/api/performance/items/${itemId}`,
        method: 'PUT',
        contentType: 'application/json',
        data: JSON.stringify({
            category: category,
            item_name: itemName,
            weight: parseFloat(weight),
            description: description
        }),
        success: function(response) {
            if (response.status === 'success') {
                alert('考核项目更新成功');
                loadItems();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '更新考核项目失败');
        }
    });
}

function deleteItem(itemId) {
    if (!confirm('确定要删除这个考核项目吗？')) return;
    
    $.ajax({
        url: `/api/performance/items/${itemId}`,
        method: 'DELETE',
        success: function(response) {
            if (response.status === 'success') {
                alert('考核项目已删除');
                loadItems();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '删除考核项目失败');
        }
    });
}

// ==================== 评分人员管理 ====================

function loadEvaluators() {
    $('#evaluator-content').html('<div class="loading"><i class="bx bx-loader-alt bx-spin"></i><p>加载中...</p></div>');
    
    $.ajax({
        url: '/api/performance/evaluators',
        method: 'GET',
        success: function(response) {
            if (response.status === 'success') {
                evaluators = response.evaluators;
                renderEvaluators(evaluators);
            }
        },
        error: function() {
            $('#evaluator-content').html('<div class="alert alert-danger">加载评分人员失败</div>');
        }
    });
}

function renderEvaluators(evaluators) {
    let html = '<table class="table table-bordered table-hover">';
    html += `
        <thead>
            <tr>
                <th width="25%">用户名</th>
                <th width="35%">可评分项目</th>
                <th width="20%">权限范围</th>
                <th width="20%">操作</th>
            </tr>
        </thead>
        <tbody>
    `;
    
    if (evaluators.length === 0) {
        html += '<tr><td colspan="4" class="text-center text-muted">暂无评分人员</td></tr>';
    } else {
        evaluators.forEach(function(evaluator) {
            html += `
                <tr>
                    <td>${evaluator.username}</td>
                    <td>${evaluator.item_name || '所有项目'}</td>
                    <td>
                        ${evaluator.can_evaluate_all ? 
                            '<span class="badge bg-success">全部</span>' : 
                            '<span class="badge bg-info">指定项目</span>'}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-danger delete-evaluator-btn" data-id="${evaluator.id}">
                            <i class='bx bx-trash'></i> 删除
                        </button>
                    </td>
                </tr>
            `;
        });
    }
    
    html += '</tbody></table>';
    
    $('#evaluator-content').html(html);
    
    // 绑定删除按钮事件
    $('.delete-evaluator-btn').click(function() {
        const evaluatorId = $(this).data('id');
        deleteEvaluator(evaluatorId);
    });
}

function showAddEvaluatorModal() {
    // 简化版本，实际应该使用Modal
    alert('请在用户管理中设置评分权限，或联系管理员');
}

function deleteEvaluator(evaluatorId) {
    if (!confirm('确定要删除这个评分人员吗？')) return;
    
    $.ajax({
        url: `/api/performance/evaluators/${evaluatorId}`,
        method: 'DELETE',
        success: function(response) {
            if (response.status === 'success') {
                alert('评分人员已删除');
                loadEvaluators();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '删除评分人员失败');
        }
    });
}

// ==================== 教师管理 ====================

function loadTeachers() {
    $('#teacher-content').html('<div class="loading"><i class="bx bx-loader-alt bx-spin"></i><p>加载中...</p></div>');
    
    $.ajax({
        url: '/api/performance/teachers',
        method: 'GET',
        success: function(response) {
            if (response.status === 'success') {
                renderTeachers(response.teachers);
            }
        },
        error: function() {
            $('#teacher-content').html('<div class="alert alert-danger">加载教师列表失败</div>');
        }
    });
}

function renderTeachers(teachers) {
    let html = '<table class="table table-bordered table-hover">';
    html += `
        <thead>
            <tr>
                <th width="25%">教师姓名</th>
                <th width="25%">班级</th>
                <th width="25%">角色</th>
                <th width="25%">操作</th>
            </tr>
        </thead>
        <tbody>
    `;
    
    teachers.forEach(function(teacher) {
        html += `
            <tr>
                <td>${teacher.username}</td>
                <td>${teacher.class_name || '-'}</td>
                <td>
                    <select class="form-select teacher-role-select" data-id="${teacher.id}">
                        <option value="正班主任" ${teacher.role === '正班主任' ? 'selected' : ''}>正班主任</option>
                        <option value="副班主任" ${teacher.role === '副班主任' ? 'selected' : ''}>副班主任</option>
                        <option value="科任老师" ${teacher.role === '科任老师' ? 'selected' : ''}>科任老师</option>
                        <option value="行政" ${teacher.role === '行政' ? 'selected' : ''}>行政</option>
                        <option value="校级领导" ${teacher.role === '校级领导' ? 'selected' : ''}>校级领导</option>
                        <option value="超级管理员" ${teacher.role === '超级管理员' ? 'selected' : ''}>超级管理员</option>
                    </select>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary save-teacher-role-btn" data-id="${teacher.id}">
                        <i class='bx bx-save'></i> 保存
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    
    $('#teacher-content').html(html);
    
    // 绑定保存按钮事件
    $('.save-teacher-role-btn').click(function() {
        const teacherId = $(this).data('id');
        const role = $(`.teacher-role-select[data-id="${teacherId}"]`).val();
        updateTeacherRole(teacherId, role);
    });
}

function updateTeacherRole(teacherId, role) {
    $.ajax({
        url: `/api/performance/teachers/${teacherId}/role`,
        method: 'PUT',
        contentType: 'application/json',
        data: JSON.stringify({
            role: role
        }),
        success: function(response) {
            if (response.status === 'success') {
                alert('教师角色更新成功');
                loadTeachers();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            alert(response ? response.message : '更新教师角色失败');
        }
    });
}
