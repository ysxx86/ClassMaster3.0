/**
 * 成绩分析模块
 * 提供考试成绩的导入、分析和展示功能
 */

// 全局变量
let currentClassId = null;
let currentExam = null;
let examScores = {};
let examStats = {};
let charts = {};

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化表单元素
    initElements();
    
    // 加载班级列表
    loadClasses();
    
    // 事件监听
    setupEventListeners();
});

/**
 * 初始化页面元素
 */
function initElements() {
    // 设置日期选择器默认值为今天
    document.getElementById('examDateInput').valueAsDate = new Date();
}

/**
 * 设置事件监听器
 */
function setupEventListeners() {
    // 新建考试按钮点击事件
    document.getElementById('createExamBtn').addEventListener('click', function() {
        // 重置表单
        document.getElementById('createExamForm').reset();
        document.getElementById('examDateInput').valueAsDate = new Date();
        document.getElementById('previewContainer').style.display = 'none';
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('createExamModal'));
        modal.show();
    });
    
    // 创建考试提交按钮
    document.getElementById('createExamSubmitBtn').addEventListener('click', createExam);
    
    // 返回列表按钮
    document.getElementById('backToListBtn').addEventListener('click', function() {
        document.getElementById('examDetailContainer').style.display = 'none';
        document.getElementById('examsContainer').parentElement.parentElement.style.display = 'block';
    });
    
    // 下载模板按钮
    document.getElementById('downloadTemplateBtn').addEventListener('click', function() {
        downloadTemplate();
    });
    
    // 上传模板下载按钮
    document.getElementById('uploadDownloadTemplateBtn').addEventListener('click', function() {
        const examId = document.getElementById('uploadExamId').value;
        if (examId) {
            downloadTemplate(examId);
        }
    });
    
    // 文件上传预览
    document.getElementById('scoresFileInput').addEventListener('change', function(e) {
        if (this.files && this.files[0]) {
            previewScoresFile(this.files[0]);
        }
    });
    
    // 上传考试成绩文件预览
    document.getElementById('uploadScoresFileInput').addEventListener('change', function(e) {
        if (this.files && this.files[0]) {
            previewUploadScoresFile(this.files[0]);
        }
    });
    
    // 上传成绩按钮
    document.getElementById('uploadScoresSubmitBtn').addEventListener('click', uploadScores);
}

/**
 * 加载班级列表
 */
function loadClasses() {
    // 获取当前登录的班主任信息
    fetch('/api/current-user')
        .then(response => response.json())
        .then(userData => {
            if (userData.status === 'ok') {
                if (userData.user.class_id) {
                    // 设置当前班级ID为班主任的班级
                    currentClassId = userData.user.class_id;
                    
                    // 获取班级名称
                    fetch(`/api/classes/${currentClassId}`)
                        .then(response => response.json())
                        .then(classData => {
                            if (classData.status === 'ok') {
                                const className = classData.class.class_name;
                                // 显示班级名称
                                document.getElementById('currentClassName').textContent = `当前班级：${className}`;
                            }
                        })
                        .catch(error => {
                            console.error('获取班级信息失败:', error);
                        });
                    
                    // 加载考试列表
                    loadExams();
                } else {
                    // 如果未分配班级的用户
                    document.getElementById('examsContainer').innerHTML = `
                        <div class="empty-state">
                            <i class='bx bx-analyse'></i>
                            <h3>您尚未被分配班级</h3>
                            <p>请联系管理员为您分配班级</p>
                        </div>
                    `;
                    // 禁用新建考试按钮
                    document.getElementById('createExamBtn').disabled = true;
                }
            } else {
                showNotification('error', userData.message || '获取用户信息失败');
            }
        })
        .catch(error => {
            console.error('获取当前用户信息失败:', error);
            showNotification('error', '获取用户信息失败');
        });
}

/**
 * 加载考试列表
 */
function loadExams() {
    if (!currentClassId) {
        // 如果没有班级ID，显示空状态 (这种情况应该很少见，因为已在loadClasses处理)
        document.getElementById('examsContainer').innerHTML = `
            <div class="empty-state">
                <i class='bx bx-analyse'></i>
                <h3>未能获取班级信息</h3>
                <p>请刷新页面重试或联系管理员</p>
            </div>
        `;
        return;
    }
    
    // 显示加载中
    document.getElementById('examsContainer').innerHTML = `
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2">加载考试数据中...</p>
        </div>
    `;
    
    // 发送API请求获取考试列表
    fetch(`/api/exams?class_id=${currentClassId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                if (data.exams && data.exams.length > 0) {
                    // 有考试数据，显示列表
                    renderExamsList(data.exams);
                } else {
                    // 无考试数据，显示空状态
                    document.getElementById('examsContainer').innerHTML = `
                        <div class="empty-state">
                            <i class='bx bx-analyse'></i>
                            <h3>暂无考试数据</h3>
                            <p>请点击"新建考试"按钮创建一次考试记录</p>
                        </div>
                    `;
                }
            } else {
                showNotification('error', data.message || '加载考试列表失败');
                document.getElementById('examsContainer').innerHTML = `
                    <div class="alert alert-danger">
                        加载考试列表失败: ${data.message || '未知错误'}
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('加载考试列表出错:', error);
            showNotification('error', '加载考试列表失败');
            document.getElementById('examsContainer').innerHTML = `
                <div class="alert alert-danger">
                    加载考试列表失败: ${error.message}
                </div>
            `;
        });
}

/**
 * 渲染考试列表
 * @param {Array} exams 考试数据数组
 */
function renderExamsList(exams) {
    const container = document.getElementById('examsContainer');
    
    // 生成考试卡片列表
    const examCards = exams.map(exam => {
        // 格式化日期
        const examDate = new Date(exam.exam_date).toLocaleDateString('zh-CN');
        
        // 格式化学科列表
        const subjectsText = exam.subjects.join('、');
        
        return `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-4">
                            <h5 class="card-title">${exam.exam_name}</h5>
                            <p class="card-text text-muted">考试日期：${examDate}</p>
                        </div>
                        <div class="col-md-5">
                            <p class="card-text">学科：${subjectsText}</p>
                        </div>
                        <div class="col-md-3 text-end">
                            <button class="btn btn-outline-primary view-exam-btn" data-exam-id="${exam.id}">
                                <i class='bx bx-bar-chart-alt-2'></i> 查看分析
                            </button>
                            <button class="btn btn-outline-success upload-scores-btn" data-exam-id="${exam.id}" data-exam-name="${exam.exam_name}">
                                <i class='bx bx-upload'></i> 上传成绩
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // 更新内容
    container.innerHTML = examCards;
    
    // 添加查看按钮事件
    document.querySelectorAll('.view-exam-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const examId = this.getAttribute('data-exam-id');
            loadExamDetail(examId);
        });
    });
    
    // 添加上传成绩按钮事件
    document.querySelectorAll('.upload-scores-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const examId = this.getAttribute('data-exam-id');
            const examName = this.getAttribute('data-exam-name');
            
            document.getElementById('uploadExamId').value = examId;
            document.getElementById('uploadExamName').value = examName;
            document.getElementById('uploadScoresForm').reset();
            document.getElementById('uploadPreviewContainer').style.display = 'none';
            
            const modal = new bootstrap.Modal(document.getElementById('uploadScoresModal'));
            modal.show();
        });
    });
}

/**
 * 加载考试详情
 * @param {number} examId 考试ID
 */
function loadExamDetail(examId) {
    // 显示加载中
    document.getElementById('examDetailContainer').style.display = 'block';
    document.getElementById('examsContainer').parentElement.parentElement.style.display = 'none';
    
    document.getElementById('examDetailContainer').innerHTML = `
        <div class="card">
            <div class="card-body text-center my-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-2">加载考试详情数据中...</p>
            </div>
        </div>
    `;
    
    // 发送API请求获取考试详情
    fetch(`/api/exams/${examId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                currentExam = data.exam;
                examScores = data.scores;
                examStats = data.stats;
                
                // 恢复原始的考试详情容器结构
                document.getElementById('examDetailContainer').innerHTML = `
                    <div class="card">
                        <div class="card-header">
                            <span id="examDetailTitle">考试详情</span>
                            <button id="backToListBtn" class="btn btn-sm btn-outline-secondary float-end">
                                <i class='bx bx-arrow-back'></i> 返回列表
                            </button>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>考试名称：</strong><span id="examName"></span></p>
                                    <p><strong>考试日期：</strong><span id="examDate"></span></p>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>班级：</strong><span id="examClass"></span></p>
                                    <p><strong>学科：</strong><span id="examSubjects"></span></p>
                                </div>
                            </div>
                            
                            <!-- 成绩统计 -->
                            <div class="row mt-4">
                                <div class="col-12">
                                    <h5>成绩统计</h5>
                                    <ul class="nav nav-tabs" id="subjectTabs" role="tablist">
                                        <!-- 学科标签页由JS加载 -->
                                    </ul>
                                    <div class="tab-content pt-3" id="subjectTabContent">
                                        <!-- 学科内容由JS加载 -->
                                    </div>
                                </div>
                            </div>
                            
                            <!-- 成绩详情表格 -->
                            <div class="row mt-4">
                                <div class="col-12">
                                    <h5>成绩详情</h5>
                                    <div class="table-responsive">
                                        <table class="table table-striped table-hover">
                                            <thead>
                                                <tr>
                                                    <th>学号</th>
                                                    <th>姓名</th>
                                                    <!-- 学科列由JS加载 -->
                                                </tr>
                                            </thead>
                                            <tbody id="scoresTableBody">
                                                <!-- 成绩行由JS加载 -->
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                // 重新添加返回按钮事件
                document.getElementById('backToListBtn').addEventListener('click', function() {
                    document.getElementById('examDetailContainer').style.display = 'none';
                    document.getElementById('examsContainer').parentElement.parentElement.style.display = 'block';
                });
                
                // 显示考试基本信息
                renderExamInfo(data.exam);
                
                // 渲染学科标签和数据
                renderSubjectTabs(data.exam.subjects, data.stats);
                
                // 渲染成绩表格
                renderScoresTable(data.exam.subjects, data.scores);
            } else {
                showNotification('error', data.message || '加载考试详情失败');
                document.getElementById('examDetailContainer').innerHTML = `
                    <div class="card">
                        <div class="card-header">
                            <span>考试详情</span>
                            <button id="backToListBtn" class="btn btn-sm btn-outline-secondary float-end">
                                <i class='bx bx-arrow-back'></i> 返回列表
                            </button>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-danger">
                                加载考试详情失败: ${data.message || '未知错误'}
                            </div>
                        </div>
                    </div>
                `;
                
                // 重新添加返回按钮事件
                document.getElementById('backToListBtn').addEventListener('click', function() {
                    document.getElementById('examDetailContainer').style.display = 'none';
                    document.getElementById('examsContainer').parentElement.parentElement.style.display = 'block';
                });
            }
        })
        .catch(error => {
            console.error('加载考试详情出错:', error);
            showNotification('error', '加载考试详情失败');
            document.getElementById('examDetailContainer').innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <span>考试详情</span>
                        <button id="backToListBtn" class="btn btn-sm btn-outline-secondary float-end">
                            <i class='bx bx-arrow-back'></i> 返回列表
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-danger">
                            加载考试详情失败: ${error.message}
                        </div>
                    </div>
                </div>
            `;
            
            // 重新添加返回按钮事件
            document.getElementById('backToListBtn').addEventListener('click', function() {
                document.getElementById('examDetailContainer').style.display = 'none';
                document.getElementById('examsContainer').parentElement.parentElement.style.display = 'block';
            });
        });
}

/**
 * 渲染考试基本信息
 * @param {Object} exam 考试数据
 */
function renderExamInfo(exam) {
    // 格式化日期
    const examDate = new Date(exam.exam_date).toLocaleDateString('zh-CN');
    
    // 更新考试标题
    document.getElementById('examDetailTitle').textContent = exam.exam_name;
    
    // 更新考试基本信息
    document.getElementById('examName').textContent = exam.exam_name;
    document.getElementById('examDate').textContent = examDate;
    
    // 获取班级名称
    fetch(`/api/classes/${exam.class_id}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                document.getElementById('examClass').textContent = data.class.class_name;
            } else {
                document.getElementById('examClass').textContent = `班级ID: ${exam.class_id}`;
            }
        })
        .catch(error => {
            console.error('获取班级名称出错:', error);
            document.getElementById('examClass').textContent = `班级ID: ${exam.class_id}`;
        });
    
    // 更新学科信息
    document.getElementById('examSubjects').textContent = exam.subjects.join('、');
}

/**
 * 渲染学科标签页和数据
 * @param {Array} subjects 学科列表
 * @param {Object} stats 统计数据
 */
function renderSubjectTabs(subjects, stats) {
    const tabsContainer = document.getElementById('subjectTabs');
    const contentContainer = document.getElementById('subjectTabContent');
    
    // 清空现有内容
    tabsContainer.innerHTML = '';
    contentContainer.innerHTML = '';
    
    // 销毁现有图表
    Object.keys(charts).forEach(id => {
        if (charts[id]) {
            charts[id].destroy();
            delete charts[id];
        }
    });
    
    // 生成标签和内容
    subjects.forEach((subject, index) => {
        // 检查是否有该学科的统计数据
        const hasStats = stats[subject] !== undefined;
        
        // 创建标签页
        const tabId = `subject-tab-${index}`;
        const contentId = `subject-content-${index}`;
        
        // 添加标签
        const tabItem = document.createElement('li');
        tabItem.className = 'nav-item';
        tabItem.role = 'presentation';
        tabItem.innerHTML = `
            <button class="nav-link ${index === 0 ? 'active' : ''}" 
                    id="${tabId}" 
                    data-bs-toggle="tab" 
                    data-bs-target="#${contentId}" 
                    type="button" 
                    role="tab" 
                    aria-controls="${contentId}" 
                    aria-selected="${index === 0}">
                ${subject}
            </button>
        `;
        tabsContainer.appendChild(tabItem);
        
        // 添加内容
        const contentItem = document.createElement('div');
        contentItem.className = `tab-pane fade ${index === 0 ? 'show active' : ''}`;
        contentItem.id = contentId;
        contentItem.role = 'tabpanel';
        contentItem.setAttribute('aria-labelledby', tabId);
        
        if (hasStats) {
            const subjectStats = stats[subject];
            
            contentItem.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <div class="row">
                            <div class="col-md-4">
                                <div class="stats-card">
                                    <div class="stats-label">平均分</div>
                                    <div class="stats-value">${subjectStats.average}</div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="stats-card">
                                    <div class="stats-label">最高分</div>
                                    <div class="stats-value">${subjectStats.max}</div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="stats-card">
                                    <div class="stats-label">最低分</div>
                                    <div class="stats-value">${subjectStats.min}</div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-3">
                            <div class="col-md-6">
                                <div class="stats-card">
                                    <div class="stats-label">优秀率 (${subjectStats.excellent_threshold}分及以上)</div>
                                    <div class="stats-value">${subjectStats.excellent_rate}%</div>
                                    <div class="progress-bar-container">
                                        <div class="progress-bar bg-success" style="width: ${subjectStats.excellent_rate}%"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="stats-card">
                                    <div class="stats-label">及格率 (60分及以上)</div>
                                    <div class="stats-value">${subjectStats.pass_rate}%</div>
                                    <div class="progress-bar-container">
                                        <div class="progress-bar bg-info" style="width: ${subjectStats.pass_rate}%"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="mt-4">
                            <h6>分数段分布</h6>
                            <div class="distribution-bar">
                                <div class="distribution-segment segment-fail" style="width: ${calculateWidth(subjectStats.score_distribution['0-59'], subjectStats)}%" title="不及格: ${subjectStats.score_distribution['0-59']}人"></div>
                                <div class="distribution-segment segment-pass" style="width: ${calculateWidth(subjectStats.score_distribution['60-69'], subjectStats)}%" title="及格: ${subjectStats.score_distribution['60-69']}人"></div>
                                <div class="distribution-segment segment-good" style="width: ${calculateWidth(subjectStats.score_distribution['70-79'] + subjectStats.score_distribution['80-89'], subjectStats)}%" title="良好: ${subjectStats.score_distribution['70-79'] + subjectStats.score_distribution['80-89']}人"></div>
                                <div class="distribution-segment segment-excellent" style="width: ${calculateWidth(subjectStats.score_distribution['90-100'], subjectStats)}%" title="优秀: ${subjectStats.score_distribution['90-100']}人"></div>
                            </div>
                            <div class="d-flex justify-content-between mt-1">
                                <small>0-59</small>
                                <small>60-69</small>
                                <small>70-89</small>
                                <small>90-100</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="chart-container">
                            <canvas id="chart-${subject}"></canvas>
                        </div>
                    </div>
                </div>
            `;
        } else {
            contentItem.innerHTML = `
                <div class="alert alert-warning">
                    <i class='bx bx-info-circle'></i> 
                    暂无 ${subject} 学科的成绩数据，请上传成绩。
                </div>
            `;
        }
        
        contentContainer.appendChild(contentItem);
        
        // 如果有统计数据，初始化图表
        if (hasStats) {
            // 等DOM渲染完成后初始化图表
            setTimeout(() => {
                const chartCanvas = document.getElementById(`chart-${subject}`);
                if (chartCanvas) {
                    initChart(chartCanvas, subject, stats[subject]);
                }
            }, 100);
        }
    });
}

/**
 * 计算分布条宽度
 * @param {number} count 人数
 * @param {Object} stats 统计数据
 * @returns {number} 宽度百分比
 */
function calculateWidth(count, stats) {
    // 计算当前学科的总学生数
    const distribution = stats.score_distribution;
    const totalStudents = Object.values(distribution).reduce((a, b) => a + b, 0);
    
    // 计算百分比
    return totalStudents > 0 ? (count / totalStudents) * 100 : 0;
}

/**
 * 获取分布百分比
 * @param {number} count 数量
 * @returns {number} 百分比
 */
function getDistributionPercentage(count) {
    // 获取当前正在显示的学科
    const activeTab = document.querySelector('.nav-link.active');
    if (!activeTab) return 0;
    
    const subject = activeTab.textContent.trim();
    
    // 获取当前学科的总学生数
    let totalStudents = 0;
    if (examStats[subject] && examStats[subject].score_distribution) {
        const distribution = examStats[subject].score_distribution;
        totalStudents = Object.values(distribution).reduce((a, b) => a + b, 0);
    }
    
    // 计算百分比
    return totalStudents > 0 ? (count / totalStudents) * 100 : 0;
}

/**
 * 初始化图表
 * @param {HTMLElement} canvas 画布元素
 * @param {string} subject 学科名称
 * @param {Object} stats 统计数据
 */
function initChart(canvas, subject, stats) {
    // 销毁可能存在的旧图表
    if (charts[subject]) {
        charts[subject].destroy();
    }
    
    // 创建图表
    const ctx = canvas.getContext('2d');
    
    // 准备数据
    const distribution = stats.score_distribution;
    
    // 确保数据有效
    const totalStudents = Object.values(distribution).reduce((a, b) => a + b, 0);
    console.log(`${subject} 学科总学生数: ${totalStudents}`);
    console.log(`${subject} 分数分布:`, distribution);
    
    // 获取最大值以设置图表刻度
    const maxValue = Math.max(...Object.values(distribution));
    
    const data = {
        labels: ['0-59', '60-69', '70-79', '80-89', '90-100'],
        datasets: [{
            label: '学生人数',
            data: [
                distribution['0-59'],
                distribution['60-69'],
                distribution['70-79'],
                distribution['80-89'],
                distribution['90-100']
            ],
            backgroundColor: [
                'rgba(231, 76, 60, 0.7)',  // 红色
                'rgba(243, 156, 18, 0.7)',  // 橙色
                'rgba(52, 152, 219, 0.7)',  // 蓝色
                'rgba(46, 204, 113, 0.7)',  // 绿色
                'rgba(155, 89, 182, 0.7)'   // 紫色
            ],
            borderColor: [
                'rgb(231, 76, 60)',
                'rgb(243, 156, 18)',
                'rgb(52, 152, 219)',
                'rgb(46, 204, 113)',
                'rgb(155, 89, 182)'
            ],
            borderWidth: 1
        }]
    };
    
    // 创建图表
    charts[subject] = new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `${subject} 成绩分布`
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            return `${tooltipItems[0].label} 分`;
                        },
                        label: function(context) {
                            let value = context.raw;
                            // 确保显示值是整数
                            if (typeof value === 'number') {
                                value = Math.round(value);
                            }
                            return `${context.dataset.label}: ${value} 人`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '学生人数'
                    },
                    ticks: {
                        stepSize: 1,
                        precision: 0 // 确保Y轴刻度是整数
                    },
                    // 设置Y轴最大值稍大于数据最大值
                    suggestedMax: maxValue + 2
                },
                x: {
                    title: {
                        display: true,
                        text: '分数段'
                    }
                }
            }
        },
        plugins: [{
            afterDraw: function(chart) {
                const ctx = chart.ctx;
                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';
                ctx.font = 'bold 12px Arial';
                
                chart.data.datasets.forEach(function(dataset, i) {
                    chart.getDatasetMeta(i).data.forEach(function(bar, index) {
                        const data = dataset.data[index];
                        if (data > 0) {
                            ctx.fillStyle = 'black';
                            ctx.fillText(data, bar.x, bar.y - 5);
                        }
                    });
                });
                ctx.restore();
            }
        }]
    });
}

/**
 * 渲染成绩详情表格
 * @param {Array} subjects 学科列表
 * @param {Array} scores 成绩数据
 */
function renderScoresTable(subjects, scores) {
    // 获取表格头和表格体
    const tableHead = document.querySelector('#examDetailContainer table thead tr');
    const tableBody = document.getElementById('scoresTableBody');
    
    // 清空现有内容，保留学号和姓名列
    tableHead.innerHTML = '<th>学号</th><th>姓名</th>';
    tableBody.innerHTML = '';
    
    // 添加学科列
    subjects.forEach(subject => {
        const th = document.createElement('th');
        th.textContent = subject;
        tableHead.appendChild(th);
    });
    
    // 按学生ID组织成绩数据
    const studentScores = {};
    scores.forEach(score => {
        if (!studentScores[score.student_id]) {
            studentScores[score.student_id] = {
                id: score.student_id,
                name: score.student_name,
                scores: {}
            };
        }
        studentScores[score.student_id].scores[score.subject] = score.score;
    });
    
    // 生成表格行
    Object.values(studentScores).forEach(student => {
        const row = document.createElement('tr');
        
        // 添加学号和姓名
        row.innerHTML = `
            <td>${student.id}</td>
            <td>${student.name}</td>
        `;
        
        // 添加各科成绩
        subjects.forEach(subject => {
            const td = document.createElement('td');
            const score = student.scores[subject];
            
            if (score !== undefined) {
                // 根据成绩设置样式
                td.textContent = score;
                
                // 应用颜色样式
                if (score >= 90) {
                    td.className = 'table-success';
                } else if (score >= 80) {
                    td.className = 'table-info';
                } else if (score >= 60) {
                    td.className = 'table-warning';
                } else {
                    td.className = 'table-danger';
                }
            } else {
                td.textContent = '-';
                td.className = 'table-secondary';
            }
            
            row.appendChild(td);
        });
        
        tableBody.appendChild(row);
    });
}

/**
 * 创建新考试
 */
function createExam() {
    // 获取表单数据
    const examName = document.getElementById('examNameInput').value.trim();
    const examDate = document.getElementById('examDateInput').value;
    
    // 获取选中的学科
    const subjects = [];
    document.querySelectorAll('.subject-checkbox:checked').forEach(cb => {
        subjects.push(cb.value);
    });
    
    // 验证表单
    if (!examName) {
        showNotification('error', '请输入考试名称');
        return;
    }
    
    if (!examDate) {
        showNotification('error', '请选择考试日期');
        return;
    }
    
    if (subjects.length === 0) {
        showNotification('error', '请至少选择一个学科');
        return;
    }
    
    // 准备请求数据
    const requestData = {
        exam_name: examName,
        exam_date: examDate,
        subjects: subjects
    };
    
    // 如果是管理员，需要提供班级ID
    if (currentClassId) {
        requestData.class_id = currentClassId;
    }
    
    // 发送请求
    fetch('/api/exams', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showNotification('success', '考试创建成功');
            
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('createExamModal')).hide();
            
            // 刷新考试列表
            loadExams();
            
            // 判断是否需要上传成绩文件
            const fileInput = document.getElementById('scoresFileInput');
            if (fileInput.files && fileInput.files[0]) {
                uploadScoresFile(data.exam_id, fileInput.files[0]);
            }
        } else {
            showNotification('error', data.message || '创建考试失败');
        }
    })
    .catch(error => {
        console.error('创建考试出错:', error);
        showNotification('error', '创建考试失败: ' + error.message);
    });
}

/**
 * 上传成绩文件
 * @param {number} examId 考试ID
 * @param {File} file 成绩文件
 */
function uploadScoresFile(examId, file) {
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);
    
    // 发送请求
    fetch(`/api/exams/${examId}/scores`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showNotification('success', `成绩上传成功，共导入 ${data.records_count} 条记录`);
            
            // 可以选择是否查看刚上传的考试详情
            if (confirm('成绩上传成功，是否查看详情？')) {
                loadExamDetail(examId);
            }
        } else {
            showNotification('error', data.message || '上传成绩失败');
        }
    })
    .catch(error => {
        console.error('上传成绩出错:', error);
        showNotification('error', '上传成绩失败: ' + error.message);
    });
}

/**
 * 预览成绩文件
 * @param {File} file 成绩文件
 */
function previewScoresFile(file) {
    // 显示加载中
    document.getElementById('previewContainer').innerHTML = `
        <div class="text-center my-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2">正在解析文件...</p>
        </div>
    `;
    document.getElementById('previewContainer').style.display = 'block';
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);
    
    // 发送请求
    fetch('/api/exams/preview', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            renderPreview(data.preview, data.subjects);
        } else {
            document.getElementById('previewContainer').innerHTML = `
                <div class="alert alert-danger">
                    ${data.message || '预览失败'}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('预览成绩文件出错:', error);
        document.getElementById('previewContainer').innerHTML = `
            <div class="alert alert-danger">
                预览失败: ${error.message}
            </div>
        `;
    });
}

/**
 * 渲染预览数据
 * @param {Array} preview 预览数据
 * @param {Array} subjects 学科列表
 */
function renderPreview(preview, subjects) {
    // 更新预览容器
    document.getElementById('previewContainer').innerHTML = `
        <h6>成绩预览</h6>
        <div class="preview-table">
            <table class="table table-sm table-striped">
                <thead id="previewTableHead">
                    <tr>
                        <th>学号</th>
                        <th>姓名</th>
                        ${subjects.map(subject => `<th>${subject}</th>`).join('')}
                    </tr>
                </thead>
                <tbody id="previewTableBody">
                    ${preview.map(student => `
                        <tr>
                            <td>${student.student_id}</td>
                            <td>${student.student_name}</td>
                            ${subjects.map(subject => `
                                <td>${student.scores[subject] !== null ? student.scores[subject] : '-'}</td>
                            `).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * 下载模板
 * @param {number} examId 考试ID (可选)
 */
function downloadTemplate(examId) {
    let url = '/api/exams/template?';
    
    // 添加班级ID
    if (currentClassId) {
        url += `class_id=${currentClassId}`;
    }
    
    // 如果有考试ID，从考试中获取学科列表
    if (examId) {
        // 获取考试详情
        fetch(`/api/exams/${examId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    const subjects = data.exam.subjects;
                    
                    // 下载包含指定学科的模板
                    window.location.href = `${url}&subjects=${subjects.join(',')}`;
                } else {
                    showNotification('error', data.message || '获取考试详情失败');
                }
            })
            .catch(error => {
                console.error('获取考试详情出错:', error);
                showNotification('error', '获取考试详情失败');
            });
    } else {
        // 获取选中的学科
        const subjects = [];
        document.querySelectorAll('.subject-checkbox:checked').forEach(cb => {
            subjects.push(cb.value);
        });
        
        if (subjects.length === 0) {
            showNotification('warning', '请至少选择一个学科');
            return;
        }
        
        // 下载包含选中学科的模板
        window.location.href = `${url}&subjects=${subjects.join(',')}`;
    }
}

/**
 * 预览上传成绩文件
 * @param {File} file 成绩文件
 */
function previewUploadScoresFile(file) {
    // 显示加载中
    document.getElementById('uploadPreviewContainer').innerHTML = `
        <div class="text-center my-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2">正在解析文件...</p>
        </div>
    `;
    document.getElementById('uploadPreviewContainer').style.display = 'block';
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);
    
    // 发送请求
    fetch('/api/exams/preview', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            renderUploadPreview(data.preview, data.subjects);
        } else {
            document.getElementById('uploadPreviewContainer').innerHTML = `
                <div class="alert alert-danger">
                    ${data.message || '预览失败'}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('预览上传成绩文件出错:', error);
        document.getElementById('uploadPreviewContainer').innerHTML = `
            <div class="alert alert-danger">
                预览失败: ${error.message}
            </div>
        `;
    });
}

/**
 * 渲染上传预览数据
 * @param {Array} preview 预览数据
 * @param {Array} subjects 学科列表
 */
function renderUploadPreview(preview, subjects) {
    // 更新预览容器
    document.getElementById('uploadPreviewContainer').innerHTML = `
        <h6>成绩预览</h6>
        <div class="preview-table">
            <table class="table table-sm table-striped">
                <thead id="uploadPreviewTableHead">
                    <tr>
                        <th>学号</th>
                        <th>姓名</th>
                        ${subjects.map(subject => `<th>${subject}</th>`).join('')}
                    </tr>
                </thead>
                <tbody id="uploadPreviewTableBody">
                    ${preview.map(student => `
                        <tr>
                            <td>${student.student_id}</td>
                            <td>${student.student_name}</td>
                            ${subjects.map(subject => `
                                <td>${student.scores[subject] !== null ? student.scores[subject] : '-'}</td>
                            `).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * 上传成绩
 */
function uploadScores() {
    const examId = document.getElementById('uploadExamId').value;
    const fileInput = document.getElementById('uploadScoresFileInput');
    
    if (!examId) {
        showNotification('error', '缺少考试ID');
        return;
    }
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showNotification('error', '请选择成绩文件');
        return;
    }
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    // 发送请求
    fetch(`/api/exams/${examId}/scores`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showNotification('success', `成绩上传成功，共导入 ${data.records_count} 条记录`);
            
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('uploadScoresModal')).hide();
            
            // 可以选择是否查看刚上传的考试详情
            if (confirm('成绩上传成功，是否查看详情？')) {
                loadExamDetail(examId);
            } else {
                // 刷新考试列表
                loadExams();
            }
        } else {
            showNotification('error', data.message || '上传成绩失败');
        }
    })
    .catch(error => {
        console.error('上传成绩出错:', error);
        showNotification('error', '上传成绩失败: ' + error.message);
    });
}

/**
 * 显示通知
 * @param {string} type 通知类型 (success/error/warning)
 * @param {string} message 通知消息
 */
function showNotification(type, message) {
    const notificationContainer = document.getElementById('notificationContainer');
    
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-icon">
            <i class='bx bx-${type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : 'info-circle'}'></i>
        </div>
        <div class="notification-content">
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close">
            <i class='bx bx-x'></i>
        </button>
    `;
    
    // 添加关闭按钮事件
    notification.querySelector('.notification-close').addEventListener('click', function() {
        notification.classList.add('notification-hiding');
        setTimeout(() => {
            notification.remove();
        }, 300);
    });
    
    // 添加到容器
    notificationContainer.appendChild(notification);
    
    // 自动关闭
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.add('notification-hiding');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 5000);
} 