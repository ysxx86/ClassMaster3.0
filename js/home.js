// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 添加数据加载
    try {
        // 加载首页数据总览
    loadDashboardData();
        
        // 加载图表数据
        loadGradeDistribution();
        loadCommentsProgress();
    
    // 为快捷操作绑定点击事件
    setupQuickActions();
    
    // 动态加载待办事项和最近活动
    loadTodos();
    loadActivities();
    } catch (e) {
        console.error('初始化仪表盘出错:', e);
    }
});

// 加载首页基本数据
function loadDashboardData() {
    fetch('/api/dashboard/info')
        .then(response => {
            if (!response.ok) {
                throw new Error('API请求失败: ' + response.status);
            }
            return response.json();
        })
        .then(result => {
            if (result.status === 'success') {
                const data = result.data;
                
                // 更新班级和学期信息
                document.querySelector('.welcome-banner .col-md-6:first-child').innerHTML = `
                    <div class="d-flex align-items-center mb-3">
                        <i class='bx bx-user me-2'></i>
                        <span>当前班级：${data.current_class}</span>
                    </div>
                    <div class="d-flex align-items-center">
                        <i class='bx bx-calendar me-2'></i>
                        <span>学期：${data.current_semester}</span>
                    </div>
                `;
                
                // 更新数据概览 - 使用更具体的选择器
                const cards = document.querySelectorAll('.dashboard-card');
                // 学生总数 - 第一个卡片
                cards[0].querySelector('.dashboard-value').textContent = data.total_students;
                
                // 评语完成 - 第二个卡片
                cards[1].querySelector('.dashboard-value').textContent = data.comments_completed;
                cards[1].querySelector('.dashboard-desc').textContent = `已完成评语的学生数 (${data.comments_percentage}%)`;
                
                // 成绩录入 - 第三个卡片
                cards[2].querySelector('.dashboard-value').textContent = data.grades_completed;
                cards[2].querySelector('.dashboard-desc').textContent = `已录入成绩的学生数 (${data.grades_percentage}%)`;
                
                // 报告生成 - 第四个卡片
                cards[3].querySelector('.dashboard-value').textContent = data.reports_ready;
                cards[3].querySelector('.dashboard-desc').textContent = `已生成报告的学生数 (${data.reports_percentage}%)`;
            } else {
                console.error('获取仪表盘数据失败', result.message);
                showErrorMessage('获取数据失败，请刷新页面重试');
            }
        })
        .catch(error => {
            console.error('API请求失败', error);
            showErrorMessage('服务器连接失败，请检查网络连接');
            // 尝试从本地存储获取上次缓存的数据
            loadCachedDashboardData();
        });
}

// 从本地缓存加载数据
function loadCachedDashboardData() {
    const cachedData = localStorage.getItem('dashboard_data');
    if (cachedData) {
        try {
            const data = JSON.parse(cachedData);
            // 使用缓存数据更新UI，但显示提示表明这是缓存数据
            updateDashboardWithData(data);
            
            const warningMsg = document.createElement('div');
            warningMsg.className = 'alert alert-warning mt-3';
            warningMsg.innerHTML = '<i class="bx bx-info-circle"></i> 显示的是缓存数据，非实时信息';
            document.querySelector('.welcome-banner').after(warningMsg);
        } catch (e) {
            console.error('解析缓存数据出错:', e);
        }
    }
}

// 使用数据更新仪表盘
function updateDashboardWithData(data) {
    // 更新班级和学期信息
    const classInfo = document.querySelector('.welcome-banner .col-md-6:first-child');
    if (classInfo) {
        classInfo.innerHTML = `
            <div class="d-flex align-items-center mb-3">
                <i class='bx bx-user me-2'></i>
                <span>当前班级：${data.current_class || '未设置'}</span>
            </div>
            <div class="d-flex align-items-center">
                <i class='bx bx-calendar me-2'></i>
                <span>学期：${data.current_semester || '未设置'}</span>
            </div>
        `;
    }
    
    // 更新数据概览
    const cards = document.querySelectorAll('.dashboard-card');
    if (cards.length >= 4) {
        // 学生总数
        const studentCard = cards[0];
        studentCard.querySelector('.dashboard-value').textContent = data.total_students || '0';
        
        // 评语完成
        const commentCard = cards[1];
        commentCard.querySelector('.dashboard-value').textContent = data.comments_completed || '0';
        commentCard.querySelector('.dashboard-desc').textContent = 
            `已完成评语的学生数 (${data.comments_percentage || '0'}%)`;
        
        // 成绩录入
        const gradeCard = cards[2];
        gradeCard.querySelector('.dashboard-value').textContent = data.grades_completed || '0';
        gradeCard.querySelector('.dashboard-desc').textContent = 
            `已录入成绩的学生数 (${data.grades_percentage || '0'}%)`;
        
        // 报告生成
        const reportCard = cards[3];
        reportCard.querySelector('.dashboard-value').textContent = data.reports_ready || '0';
        reportCard.querySelector('.dashboard-desc').textContent = 
            `已生成报告的学生数 (${data.reports_percentage || '0'}%)`;
    }
}

// 显示错误信息
function showErrorMessage(message) {
    const errorMsg = document.createElement('div');
    errorMsg.className = 'alert alert-danger alert-dismissible fade show';
    errorMsg.innerHTML = `
        <i class="bx bx-error-circle me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.querySelector('.welcome-banner').after(errorMsg);
}

// 设置快捷操作的点击事件
function setupQuickActions() {
    const quickActions = document.querySelectorAll('.quick-action');
    quickActions.forEach(action => {
        action.addEventListener('click', function(e) {
            e.preventDefault();
            const actionText = this.querySelector('span').textContent.trim();
            
            // 根据操作文本跳转到相应页面
            switch(actionText) {
                case '添加新学生':
                    parent.document.querySelector('[data-iframe="pages/students.html"]').click();
                    break;
                case '批量添加评语':
                    parent.document.querySelector('[data-iframe="pages/comments.html"]').click();
                    break;
                case '录入学科成绩':
                    parent.document.querySelector('[data-iframe="pages/grades.html"]').click();
                    break;
                case '导出学生报告':
                    parent.document.querySelector('[data-iframe="pages/export.html"]').click();
                    break;
                case '系统设置':
                    parent.document.querySelector('[data-iframe="pages/settings.html"]').click();
                    break;
            }
        });
    });
    
    // 设置导入学生和导出报告按钮
    document.querySelector('.welcome-banner button:nth-child(1)').addEventListener('click', function() {
        parent.document.querySelector('[data-iframe="pages/students.html"]').click();
    });
    
    document.querySelector('.welcome-banner button:nth-child(2)').addEventListener('click', function() {
        parent.document.querySelector('[data-iframe="pages/export.html"]').click();
    });
}

// 加载待办事项
function loadTodos() {
    fetch('/api/dashboard/todos')
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                const todosContainer = document.querySelector('.col-md-4:nth-child(2) .list-group');
                todosContainer.innerHTML = '';
                
                result.data.forEach(todo => {
                    // 计算剩余天数
                    const today = new Date();
                    const deadline = new Date(todo.deadline);
                    const daysLeft = Math.ceil((deadline - today) / (1000 * 60 * 60 * 24));
                    
                    let badgeText = '';
                    let badgeClass = '';
                    
                    if (daysLeft === 0) {
                        badgeText = '今天';
                        badgeClass = 'bg-primary';
                    } else if (daysLeft === 1) {
                        badgeText = '明天';
                        badgeClass = 'bg-primary';
                    } else if (daysLeft > 1 && daysLeft <= 3) {
                        badgeText = daysLeft + '天后';
                        badgeClass = 'bg-warning';
                    } else if (daysLeft > 3 && daysLeft <= 7) {
                        badgeText = daysLeft + '天后';
                        badgeClass = 'bg-info';
                    } else {
                        badgeText = daysLeft + '天后';
                        badgeClass = 'bg-secondary';
                    }
                    
                    const todoItem = `
                        <div class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-bold">${todo.title}</div>
                                <small class="text-muted">截止日期：${todo.deadline}</small>
                            </div>
                            <span class="badge ${badgeClass} rounded-pill">${badgeText}</span>
                        </div>
                    `;
                    
                    todosContainer.innerHTML += todoItem;
                });
                
                // 添加"添加待办"按钮
                const addTodoButton = document.querySelector('.col-md-4:nth-child(2) .mt-3');
                addTodoButton.innerHTML = `
                    <button class="btn btn-sm btn-outline-primary" id="addTodoButton">
                        <i class='bx bx-plus'></i> 添加待办
                    </button>
                `;
                
                // 添加待办按钮
                document.getElementById('addTodoButton').addEventListener('click', function() {
                    // 创建表单
                    const todoForm = document.createElement('div');
                    todoForm.className = 'mt-3 p-3 border rounded';
                    todoForm.innerHTML = `
                        <div class="mb-2">
                            <input type="text" class="form-control form-control-sm" id="todoTitle" placeholder="待办事项标题">
                        </div>
                        <div class="mb-2">
                            <input type="text" class="form-control form-control-sm" id="todoDescription" placeholder="描述">
                        </div>
                        <div class="mb-2">
                            <input type="date" class="form-control form-control-sm" id="todoDeadline">
                        </div>
                        <div class="mb-2">
                            <select class="form-control form-control-sm" id="todoPriority">
                                <option value="high">高优先级</option>
                                <option value="medium" selected>中优先级</option>
                                <option value="low">低优先级</option>
                            </select>
                        </div>
                        <div class="d-flex justify-content-end">
                            <button class="btn btn-sm btn-secondary me-2" id="cancelTodo">取消</button>
                            <button class="btn btn-sm btn-primary" id="saveTodo">保存</button>
                        </div>
                    `;
                    
                    // 将表单添加到列表下方
                    document.querySelector('.col-md-4:nth-child(2) .list-group').after(todoForm);
                    
                    // 隐藏添加按钮
                    document.getElementById('addTodoButton').style.display = 'none';
                    
                    // 设置取消按钮事件
                    document.getElementById('cancelTodo').addEventListener('click', function() {
                        todoForm.remove();
                        document.getElementById('addTodoButton').style.display = 'inline-block';
                    });
                    
                    // 设置保存按钮事件
                    document.getElementById('saveTodo').addEventListener('click', function() {
                        const title = document.getElementById('todoTitle').value;
                        const description = document.getElementById('todoDescription').value;
                        const deadline = document.getElementById('todoDeadline').value;
                        const priority = document.getElementById('todoPriority').value;
                        
                        if (!title) {
                            alert('请输入待办事项标题');
                            return;
                        }
                        
                        // 发送请求添加待办事项
                        fetch('/api/todos', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                title: title,
                                description: description,
                                deadline: deadline,
                                priority: priority
                            })
                        })
                        .then(response => response.json())
                        .then(result => {
                            if (result.status === 'success') {
                                // 重新加载待办事项
                                loadTodos();
                                // 移除表单
                                todoForm.remove();
                                document.getElementById('addTodoButton').style.display = 'inline-block';
                            } else {
                                alert('添加待办事项失败: ' + result.message);
                            }
                        })
                        .catch(error => {
                            console.error('API请求失败', error);
                            alert('添加待办事项失败，请稍后重试');
                        });
                    });
                });
            } else {
                console.error('获取待办事项失败', result.message);
            }
        })
        .catch(error => {
            console.error('API请求失败', error);
        });
}

// 加载最近活动
function loadActivities() {
    fetch('/api/dashboard/activities')
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                const activitiesContainer = document.querySelector('.recent-activity');
                activitiesContainer.innerHTML = '';
                
                result.data.forEach(activity => {
                    let iconClass = 'bx-user';
                    
                    // 根据活动类型设置图标
                    switch(activity.type) {
                        case 'grade':
                            iconClass = 'bx-bar-chart-alt-2';
                            break;
                        case 'comment':
                            iconClass = 'bx-message-square-detail';
                            break;
                        case 'report':
                            iconClass = 'bx-export';
                            break;
                        case 'setting':
                            iconClass = 'bx-cog';
                            break;
                        case 'update':
                        default:
                            iconClass = 'bx-user';
                            break;
                    }
                    
                    const activityItem = `
                        <div class="activity-item">
                            <div class="activity-icon">
                                <i class='bx ${iconClass}'></i>
                            </div>
                            <div class="activity-content">
                                <div class="activity-title">${activity.content}</div>
                                <div class="activity-time">${activity.time}</div>
                            </div>
                        </div>
                    `;
                    
                    activitiesContainer.innerHTML += activityItem;
                });
            } else {
                console.error('获取最近活动失败', result.message);
            }
        })
        .catch(error => {
            console.error('API请求失败', error);
        });
}

// 加载成绩分布
function loadGradeDistribution() {
    // 检查图表元素是否存在
    const gradesCtx = document.getElementById('gradesChart');
    if (!gradesCtx) return;
    
    fetch('/api/dashboard/grade-distribution')
        .then(response => {
            if (!response.ok) {
                throw new Error('API请求失败:' + response.status);
            }
            return response.json();
        })
        .then(result => {
            if (result.status === 'success') {
                // 渲染图表并缓存数据
                renderGradeChart(result.data);
                localStorage.setItem('grade_distribution_data', JSON.stringify(result.data));
            } else {
                console.error('获取成绩分布失败', result.message);
                // 尝试使用缓存数据
                loadCachedGradeData();
            }
        })
        .catch(error => {
            console.error('API请求失败', error);
            // 尝试使用缓存数据
            loadCachedGradeData();
        });
}

// 从缓存加载成绩数据
function loadCachedGradeData() {
    const cachedData = localStorage.getItem('grade_distribution_data');
    if (cachedData) {
        try {
            const data = JSON.parse(cachedData);
            renderGradeChart(data);
            
            // 显示使用缓存数据的提示
            const gradeCard = document.querySelector('.col-md-6:nth-child(1) .dashboard-card');
            if (gradeCard && !gradeCard.querySelector('.cached-data-notice')) {
                const notice = document.createElement('div');
                notice.className = 'cached-data-notice text-muted small mt-2';
                notice.innerHTML = '<i class="bx bx-info-circle"></i> 显示的是缓存数据';
                gradeCard.appendChild(notice);
            }
        } catch (e) {
            console.error('解析缓存成绩数据出错:', e);
            showGradeDataError();
        }
    } else {
        showGradeDataError();
    }
}

// 显示成绩数据加载错误
function showGradeDataError() {
    const gradeCard = document.querySelector('.col-md-6:nth-child(1) .dashboard-card');
    if (gradeCard) {
        const chartContainer = gradeCard.querySelector('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = `
                <div class="alert alert-warning text-center py-5">
                    <i class="bx bx-error-circle fs-1"></i>
                    <p class="mt-3">无法加载成绩数据</p>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="loadGradeDistribution()">
                        <i class="bx bx-refresh"></i> 重试
                    </button>
                </div>
            `;
        }
    }
}

// 渲染成绩图表
function renderGradeChart(data) {
    const gradesCtx = document.getElementById('gradesChart').getContext('2d');
                const subjects = Object.keys(data);
                const excellentRates = subjects.map(subject => data[subject].excellent_rate);
                
                // 销毁旧图表（如果存在）
    if (window.gradesChart && typeof window.gradesChart.destroy === 'function') {
                    window.gradesChart.destroy();
                }
                
                // 创建新图表
                window.gradesChart = new Chart(gradesCtx, {
                    type: 'bar',
                    data: {
                        labels: subjects,
                        datasets: [{
                            label: '优秀率(%)',
                            data: excellentRates,
                            backgroundColor: [
                                'rgba(52, 152, 219, 0.7)',
                                'rgba(46, 204, 113, 0.7)',
                                'rgba(155, 89, 182, 0.7)',
                                'rgba(52, 73, 94, 0.7)',
                                'rgba(243, 156, 18, 0.7)',
                    'rgba(231, 76, 60, 0.7)'
                            ],
                            borderColor: [
                                'rgba(52, 152, 219, 1)',
                                'rgba(46, 204, 113, 1)',
                                'rgba(155, 89, 182, 1)',
                                'rgba(52, 73, 94, 1)',
                                'rgba(243, 156, 18, 1)',
                    'rgba(231, 76, 60, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100
                            }
                        }
                    }
                });
                
                // 添加总结信息
                const gradeCard = document.querySelector('.col-md-6:nth-child(1) .dashboard-card');
    if (gradeCard) {
                const existingSummary = gradeCard.querySelector('.grade-summary');
                if (existingSummary) {
                    existingSummary.remove();
                }
                
                // 计算总体优秀率
                const totalExcellent = subjects.reduce((sum, subject) => sum + data[subject].excellent, 0);
                const totalStudents = subjects.reduce((sum, subject) => sum + data[subject].total, 0);
                const overallRate = totalStudents > 0 ? Math.round(totalExcellent / totalStudents * 100) : 0;
                
                const summary = document.createElement('div');
                summary.className = 'mt-3 text-center grade-summary';
                summary.innerHTML = `
                    <hr>
                    <p class="mb-1">总体优秀率: <strong>${overallRate}%</strong></p>
                    <p class="small text-muted">共有 ${totalExcellent} 名学生成绩达到优秀标准</p>
                `;
                
                gradeCard.appendChild(summary);
            }
}

// 加载评语完成情况
function loadCommentsProgress() {
    // 检查图表元素是否存在
    const commentsCtx = document.getElementById('commentsChart');
    if (!commentsCtx) return;
    
    fetch('/api/dashboard/comments')
        .then(response => {
            if (!response.ok) {
                throw new Error('API请求失败:' + response.status);
            }
            return response.json();
        })
        .then(result => {
            if (result.status === 'success') {
                // 渲染图表并缓存数据
                renderCommentsChart(result.data);
                localStorage.setItem('comments_progress_data', JSON.stringify(result.data));
            } else {
                console.error('获取评语完成情况失败', result.message);
                // 尝试使用缓存数据
                loadCachedCommentsData();
            }
        })
        .catch(error => {
            console.error('API请求失败', error);
            // 尝试使用缓存数据
            loadCachedCommentsData();
        });
}

// 从缓存加载评语数据
function loadCachedCommentsData() {
    const cachedData = localStorage.getItem('comments_progress_data');
    if (cachedData) {
        try {
            const data = JSON.parse(cachedData);
            renderCommentsChart(data);
            
            // 显示使用缓存数据的提示
            const commentsCard = document.querySelector('.col-md-6:nth-child(2) .dashboard-card');
            if (commentsCard && !commentsCard.querySelector('.cached-data-notice')) {
                const notice = document.createElement('div');
                notice.className = 'cached-data-notice text-muted small mt-2';
                notice.innerHTML = '<i class="bx bx-info-circle"></i> 显示的是缓存数据';
                commentsCard.appendChild(notice);
            }
        } catch (e) {
            console.error('解析缓存评语数据出错:', e);
            showCommentsDataError();
        }
    } else {
        showCommentsDataError();
    }
}

// 显示评语数据加载错误
function showCommentsDataError() {
    const commentsCard = document.querySelector('.col-md-6:nth-child(2) .dashboard-card');
    if (commentsCard) {
        const chartContainer = commentsCard.querySelector('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = `
                <div class="alert alert-warning text-center py-5">
                    <i class="bx bx-error-circle fs-1"></i>
                    <p class="mt-3">无法加载评语完成数据</p>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="loadCommentsProgress()">
                        <i class="bx bx-refresh"></i> 重试
                    </button>
                </div>
            `;
        }
    }
}

// 渲染评语图表
function renderCommentsChart(data) {
                const commentsCtx = document.getElementById('commentsChart').getContext('2d');
                
                // 销毁旧图表（如果存在）
    if (window.commentsChart && typeof window.commentsChart.destroy === 'function') {
                    window.commentsChart.destroy();
                }
                
                // 创建新图表
                window.commentsChart = new Chart(commentsCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['已完成', '未完成'],
                        datasets: [{
                            data: [data.completed, data.incomplete],
                            backgroundColor: [
                                'rgba(46, 204, 113, 0.7)',
                                'rgba(231, 76, 60, 0.7)'
                            ],
                            borderColor: [
                                'rgba(46, 204, 113, 1)',
                                'rgba(231, 76, 60, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom'
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.raw || 0;
                                        const total = data.total;
                                        const percentage = Math.round((value / total) * 100);
                                        return `${label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
                
                // 如果有未完成的评语，显示未完成的学生列表
                const cardElement = document.querySelector('.col-md-6:nth-child(2) .dashboard-card');
    if (cardElement) {
                const existingList = cardElement.querySelector('.incomplete-list');
                if (existingList) {
                    existingList.remove();
                }
                
                if (data.incomplete_students && data.incomplete_students.length > 0) {
                    const incompleteList = document.createElement('div');
                    incompleteList.className = 'mt-3 small incomplete-list';
                    incompleteList.innerHTML = '<p class="mb-1">未完成评语的学生：</p>';
                    
                    const studentsList = document.createElement('ul');
                    studentsList.className = 'list-unstyled';
                    
                    data.incomplete_students.slice(0, 5).forEach(student => {
                        const listItem = document.createElement('li');
                        listItem.innerHTML = `<i class='bx bx-user-x text-danger'></i> ${student.name}`;
                        studentsList.appendChild(listItem);
                    });
                    
                    if (data.incomplete_students.length > 5) {
                        const moreItem = document.createElement('li');
                        moreItem.className = 'text-muted';
                        moreItem.textContent = `等 ${data.incomplete_students.length - 5} 名学生...`;
                        studentsList.appendChild(moreItem);
                    }
                    
                    incompleteList.appendChild(studentsList);
                    cardElement.appendChild(incompleteList);
                }
            }
}