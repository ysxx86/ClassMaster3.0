/**
 * 成绩分析模块
 * 提供考试成绩的导入、分析和展示功能
 */

// 添加样式到页面
(function addStyles() {
    const style = document.createElement('style');
    style.textContent = `
        th.sortable {
            cursor: pointer;
            position: relative;
            user-select: none;
        }
        
        th.sortable:hover {
            background-color: rgba(0,0,0,0.05);
        }
        
        th.sortable i {
            font-size: 0.9em;
            margin-left: 5px;
            opacity: 0.5;
        }
        
        th.sortable[data-sort-direction="asc"] i,
        th.sortable[data-sort-direction="desc"] i {
            opacity: 1;
            color: #3498db;
        }
    `;
    document.head.appendChild(style);
})();

// 全局变量
let currentClassId = null;
let currentExam = null;
let examScores = {};
let examStats = {};
let charts = {};
let selectedExams = [];
let compareData = null;

/**
 * 检查依赖库是否正确加载
 */
function checkDependencies() {
    // 检查jQuery是否加载
    if (typeof jQuery === 'undefined') {
        console.error('jQuery is not loaded.');
        return false;
    }
    
    // 检查Chart.js是否加载
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded.');
        return false;
    }
    
    return true;
}

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查依赖
    const dependenciesLoaded = checkDependencies();
    
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
        const examId = document.getElementById('uploadExamId').value;
        downloadTemplate(examId);
    });
    
    // 上传模板下载按钮
    document.getElementById('uploadDownloadTemplateBtn').addEventListener('click', function() {
        const examId = document.getElementById('uploadExamId').value;
        downloadTemplate(examId);
    });
    
    // 文件上传预览
    document.getElementById('scoresFileInput').addEventListener('change', function() {
        if (this.files.length > 0) {
            previewScoresFile(this.files[0]);
        }
    });
    
    // 上传成绩文件预览
    document.getElementById('uploadScoresFileInput').addEventListener('change', function() {
        if (this.files.length > 0) {
            previewUploadScoresFile(this.files[0]);
        }
    });
    
    // 上传成绩按钮
    document.getElementById('uploadScoresSubmitBtn').addEventListener('click', uploadScores);
    
    // 更新考试按钮
    document.getElementById('updateExamBtn').addEventListener('click', updateExam);
    
    // 对比分析按钮事件
    document.getElementById('compareExamsBtn').addEventListener('click', compareSelectedExams);
    
    // 全选按钮事件
    document.getElementById('selectAllExams').addEventListener('change', function() {
        const isChecked = this.checked;
        document.querySelectorAll('.exam-checkbox').forEach(checkbox => {
            checkbox.checked = isChecked;
        });
        
        updateCompareButton();
    });
    
    // 返回列表按钮（从对比分析页面）
    document.getElementById('backToListFromCompareBtn').addEventListener('click', function() {
        document.getElementById('compareResultContainer').style.display = 'none';
        document.getElementById('examsContainer').parentElement.parentElement.style.display = 'block';
    });
    
    // 学科下拉框变化事件
    document.getElementById('compareSubjectSelect').addEventListener('change', function() {
        if (compareData) {
            renderComparisonCharts(compareData);
        }
    });
    
    // 学生姓名点击事件（使用事件委托）
    document.body.addEventListener('click', function(e) {
        if (e.target.classList.contains('student-name-link') || e.target.closest('.student-name-link')) {
            const link = e.target.classList.contains('student-name-link') ? e.target : e.target.closest('.student-name-link');
            const studentId = link.dataset.studentId;
            const studentName = link.dataset.studentName;
            
            // 打开学生分析模态框
            openStudentAnalysisModal(studentId, studentName);
        }
    });
    
    // 添加上传试卷按钮的事件监听器
    document.getElementById('uploadPaperSubmitBtn')?.addEventListener('click', uploadPaperFile);
    
    // 添加下载分析报告按钮事件
    document.getElementById('downloadAnalysisReportBtn')?.addEventListener('click', function() {
        const examId = document.getElementById('paperExamId').value;
        if (examId) {
            downloadAnalysisReport(examId);
        }
    });
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
                            <div class="d-flex align-items-center">
                                <div class="form-check me-2">
                                    <input class="form-check-input exam-checkbox" type="checkbox" value="${exam.id}" 
                                        id="exam-${exam.id}" data-exam-name="${exam.exam_name}" data-subjects='${JSON.stringify(exam.subjects)}'>
                                </div>
                                <div>
                                    <h5 class="card-title mb-0">${exam.exam_name}</h5>
                                    <p class="card-text text-muted mb-0">考试日期：${examDate}</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <p class="card-text">学科：${subjectsText}</p>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="btn-group" role="group">
                                <button class="btn btn-outline-primary view-exam-btn" data-exam-id="${exam.id}">
                                    <i class='bx bx-bar-chart-alt-2'></i> 查看分析
                                </button>
                                <button class="btn btn-outline-success upload-scores-btn" data-exam-id="${exam.id}" data-exam-name="${exam.exam_name}">
                                    <i class='bx bx-upload'></i> 上传成绩
                                </button>
                                <button class="btn btn-outline-warning edit-exam-btn" data-exam-id="${exam.id}" data-exam-name="${exam.exam_name}" data-exam-date="${exam.exam_date}" data-subjects='${JSON.stringify(exam.subjects)}'>
                                    <i class='bx bx-edit'></i> 编辑
                                </button>
                                <button class="btn btn-outline-danger delete-exam-btn" data-exam-id="${exam.id}" data-exam-name="${exam.exam_name}">
                                    <i class='bx bx-trash'></i> 删除
                                </button>
                            </div>
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
    
    // 添加编辑按钮事件
    document.querySelectorAll('.edit-exam-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const examId = this.getAttribute('data-exam-id');
            const examName = this.getAttribute('data-exam-name');
            const examDate = this.getAttribute('data-exam-date');
            const subjects = JSON.parse(this.getAttribute('data-subjects'));
            
            // 设置表单值
            document.getElementById('editExamId').value = examId;
            document.getElementById('editExamNameInput').value = examName;
            document.getElementById('editExamDateInput').value = examDate;
            
            // 清除所有选择
            document.querySelectorAll('.edit-subject-checkbox').forEach(cb => {
                cb.checked = false;
            });
            
            // 设置学科选择
            subjects.forEach(subject => {
                const checkbox = document.getElementById(`editSubject${subject.replace(/[^a-zA-Z]/g, '')}`);
                if (checkbox) {
                    checkbox.checked = true;
                }
            });
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('editExamModal'));
            modal.show();
        });
    });
    
    // 添加删除按钮事件
    document.querySelectorAll('.delete-exam-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const examId = this.getAttribute('data-exam-id');
            const examName = this.getAttribute('data-exam-name');
            
            if (confirm(`确定要删除考试"${examName}"吗？此操作不可恢复，所有相关成绩数据都将被删除。`)) {
                deleteExam(examId);
            }
        });
    });
    
    // 添加考试复选框事件，用于对比分析
    document.querySelectorAll('.exam-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateCompareButton);
    });
    
    // 初始化全选按钮状态
    updateSelectAllCheckbox();
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
                                                    <th class="sortable" data-sort-by="id">学号 <i class="bx bx-sort"></i></th>
                                                    <th class="sortable" data-sort-by="name">姓名 <i class="bx bx-sort"></i></th>
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
    
    // 添加试卷分析按钮
    const actionButtonsContainer = document.createElement('div');
    actionButtonsContainer.className = 'mt-3 d-flex gap-2';
    actionButtonsContainer.innerHTML = `
        <button class="btn btn-primary" id="uploadPaperBtn">
            <i class='bx bx-upload'></i> 上传试卷PDF
        </button>
        <button class="btn btn-info" id="analyzePaperBtn" ${!exam.has_paper ? 'disabled' : ''}>
            <i class='bx bx-analyse'></i> 查看试卷分析
        </button>
    `;
    
    // 将按钮添加到考试信息区域
    const examInfoSection = document.querySelector('#examDetailContainer .card-body .row:first-child');
    if (examInfoSection && !document.getElementById('uploadPaperBtn')) {
        examInfoSection.appendChild(actionButtonsContainer);
        
        // 添加上传试卷按钮事件
        document.getElementById('uploadPaperBtn').addEventListener('click', function() {
            openUploadPaperModal(exam.id, exam.exam_name);
        });
        
        // 添加查看分析按钮事件
        document.getElementById('analyzePaperBtn').addEventListener('click', function() {
            if(exam.has_paper) {
                openPaperAnalysisModal(exam.id, exam.exam_name);
            } else {
                showNotification('info', '请先上传试卷PDF');
            }
        });
    }
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
            // 计算达优人数（使用与优秀率相同的标准）
            let excellentCount = 0;
            const excellentThreshold = subjectStats.excellent_threshold || 90;
            
            // 分析分数段统计，计算达到优秀阈值的学生数量
            Object.keys(subjectStats.score_distribution).forEach(range => {
                const [min, max] = range.split('-').map(Number);
                if (min >= excellentThreshold || max >= excellentThreshold) {
                    // 对于跨越优秀分数线的区间，需要根据比例估算
                    if (min < excellentThreshold && max >= excellentThreshold) {
                        // 假设学生分数均匀分布，估算达到阈值的人数
                        const ratio = (max - excellentThreshold + 1) / (max - min + 1);
                        excellentCount += Math.round(subjectStats.score_distribution[range] * ratio);
                    } else {
                        // 整个区间都达到阈值
                        excellentCount += subjectStats.score_distribution[range];
                    }
                }
            });
            
            contentItem.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <div class="row">
                            <div class="col-md-3">
                                <div class="stats-card">
                                    <div class="stats-label">平均分</div>
                                    <div class="stats-value">${subjectStats.average}</div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="stats-card">
                                    <div class="stats-label">最高分</div>
                                    <div class="stats-value">${subjectStats.max}</div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="stats-card">
                                    <div class="stats-label">最低分</div>
                                    <div class="stats-value">${subjectStats.min}</div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="stats-card">
                                    <div class="stats-label">达优人数</div>
                                    <div class="stats-value">${excellentCount}</div>
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
                        <div class="row mt-3">
                            <div class="col-md-4">
                                <div class="stats-card">
                                    <div class="stats-label">应考人数</div>
                                    <div class="stats-value">${subjectStats.on_exam_students || subjectStats.total_students}</div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="stats-card">
                                    <div class="stats-label">实考人数</div>
                                    <div class="stats-value">${subjectStats.actual_exam_students || subjectStats.total_students}</div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="stats-card">
                                    <div class="stats-label">请假人数</div>
                                    <div class="stats-value">${subjectStats.leave_students || 0}</div>
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
    tableHead.innerHTML = '<th class="sortable" data-sort-by="id">学号 <i class="bx bx-sort"></i></th><th class="sortable" data-sort-by="name">姓名 <i class="bx bx-sort"></i></th>';
    tableBody.innerHTML = '';
    
    // 添加学科列
    subjects.forEach(subject => {
        const th = document.createElement('th');
        th.className = 'sortable';
        th.setAttribute('data-sort-by', subject);
        th.innerHTML = `${subject} <i class="bx bx-sort"></i>`;
        tableHead.appendChild(th);
    });
    
    // 添加操作列
    const actionTh = document.createElement('th');
    actionTh.textContent = '操作';
    tableHead.appendChild(actionTh);
    
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
    
    // 转换为数组以便排序
    let studentsArray = Object.values(studentScores);
    
    // 默认按学号排序
    studentsArray.sort((a, b) => {
        // 尝试将学号转为数字进行比较
        const numA = parseInt(a.id);
        const numB = parseInt(b.id);
        if (!isNaN(numA) && !isNaN(numB)) {
            return numA - numB;
        }
        // 如果不能转为数字，按字符串比较
        return a.id.localeCompare(b.id);
    });
    
    // 渲染表格
    renderSortedTable(studentsArray, subjects);
    
    // 添加表头排序事件
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', function() {
            const sortBy = this.getAttribute('data-sort-by');
            const currentDirection = this.getAttribute('data-sort-direction') || 'asc';
            const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';
            
            // 清除所有排序状态
            document.querySelectorAll('th.sortable').forEach(el => {
                el.setAttribute('data-sort-direction', '');
                el.querySelector('i').className = 'bx bx-sort';
            });
            
            // 设置当前排序状态
            this.setAttribute('data-sort-direction', newDirection);
            this.querySelector('i').className = newDirection === 'asc' ? 'bx bx-sort-up' : 'bx bx-sort-down';
            
            // 执行排序
            if (sortBy === 'id') {
                studentsArray.sort((a, b) => {
                    const numA = parseInt(a.id);
                    const numB = parseInt(b.id);
                    if (!isNaN(numA) && !isNaN(numB)) {
                        return newDirection === 'asc' ? numA - numB : numB - numA;
                    }
                    return newDirection === 'asc' ? a.id.localeCompare(b.id) : b.id.localeCompare(a.id);
                });
            } else if (sortBy === 'name') {
                studentsArray.sort((a, b) => {
                    return newDirection === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
                });
            } else {
                // 按学科成绩排序
                studentsArray.sort((a, b) => {
                    const scoreA = a.scores[sortBy] !== undefined ? parseFloat(a.scores[sortBy]) : -1;
                    const scoreB = b.scores[sortBy] !== undefined ? parseFloat(b.scores[sortBy]) : -1;
                    return newDirection === 'asc' ? scoreA - scoreB : scoreB - scoreA;
                });
            }
            
            // 重新渲染表格
            renderSortedTable(studentsArray, subjects);
        });
    });
    
    // 初始状态设置为学号升序排序
    const idHeader = document.querySelector('th[data-sort-by="id"]');
    idHeader.setAttribute('data-sort-direction', 'asc');
    idHeader.querySelector('i').className = 'bx bx-sort-up';

    /**
     * 渲染排序后的表格
     * @param {Array} students 排序后的学生数组
     * @param {Array} subjects 学科列表
     */
    function renderSortedTable(students, subjects) {
        // 清空表格内容
        tableBody.innerHTML = '';
        
        // 生成表格行
        students.forEach(student => {
            const row = document.createElement('tr');
            row.setAttribute('data-student-id', student.id);
            
            // 添加学号和姓名
            row.innerHTML = `
                <td>${student.id}</td>
                <td>${student.name}</td>`;
            
            // 添加各科成绩
            subjects.forEach(subject => {
                const td = document.createElement('td');
                const score = student.scores[subject];
                
                if (score !== undefined) {
                    // 检查是否为请假状态
                    const isLeave = score === 0;
                    
                    if (isLeave) {
                        // 显示请假标识
                        td.innerHTML = `<span class="badge bg-secondary">请假</span>`;
                        td.className = 'table-secondary';
                    } else {
                    // 包装成可编辑的形式
                    td.innerHTML = `
                        <span class="score-value" 
                              data-student-id="${student.id}" 
                              data-subject="${subject}" 
                              data-original-score="${score}">
                            ${score}
                        </span>
                    `;
                    
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
                    }
                } else {
                    td.textContent = '-';
                    td.className = 'table-secondary';
                }
                
                row.appendChild(td);
            });
            
            // 添加操作按钮
            const actionTd = document.createElement('td');
            actionTd.innerHTML = `
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-primary edit-student-scores-btn" data-student-id="${student.id}" data-student-name="${student.name}">
                        <i class='bx bx-edit'></i>
                    </button>
                    <button class="btn btn-outline-danger delete-student-scores-btn" data-student-id="${student.id}" data-student-name="${student.name}">
                        <i class='bx bx-trash'></i>
                    </button>
                </div>
            `;
            row.appendChild(actionTd);
            
            tableBody.appendChild(row);
        });
        
        // 添加编辑按钮事件
        document.querySelectorAll('.edit-student-scores-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const studentId = this.getAttribute('data-student-id');
                const studentName = this.getAttribute('data-student-name');
                
                // 获取该学生的所有成绩
                const studentScoreData = studentScores[studentId];
                
                // 打开编辑成绩模态框
                openEditScoresModal(studentId, studentName, subjects, studentScoreData.scores);
            });
        });
        
        // 添加删除按钮事件
        document.querySelectorAll('.delete-student-scores-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const studentId = this.getAttribute('data-student-id');
                const studentName = this.getAttribute('data-student-name');
                
                if (confirm(`确定要删除学生 ${studentName}(${studentId}) 的所有成绩记录吗？此操作不可恢复。`)) {
                    deleteStudentScores(currentExam.id, studentId);
                }
            });
        });
        
        // 单击成绩值可以直接编辑
        document.querySelectorAll('.score-value').forEach(span => {
            span.addEventListener('click', function() {
                const studentId = this.getAttribute('data-student-id');
                const subject = this.getAttribute('data-subject');
                const originalScore = this.getAttribute('data-original-score');
                
                // 将文本替换为输入框
                const input = document.createElement('input');
                input.type = 'number';
                input.min = '0';
                input.max = '100';
                input.step = '0.5';
                input.value = originalScore;
                input.className = 'form-control form-control-sm';
                input.style.width = '60px';
                
                // 替换内容
                this.innerHTML = '';
                this.appendChild(input);
                input.focus();
                
                // 处理输入完成事件
                const handleComplete = () => {
                    const newScore = parseFloat(input.value);
                    
                    // 验证输入
                    if (isNaN(newScore) || newScore < 0 || newScore > 100) {
                        showNotification('error', '请输入0-100之间的有效分数');
                        this.innerHTML = originalScore;
                        return;
                    }
                    
                    // 如果分数没变，直接恢复显示
                    if (newScore === parseFloat(originalScore)) {
                        this.innerHTML = originalScore;
                        return;
                    }
                    
                    // 更新成绩
                    updateScore(currentExam.id, studentId, subject, newScore)
                        .then(success => {
                            if (success) {
                                // 更新内容和属性
                                this.innerHTML = newScore;
                                this.setAttribute('data-original-score', newScore);
                                
                                // 可能需要更新单元格的颜色类
                                const td = this.closest('td');
                                td.className = '';
                                if (newScore >= 90) {
                                    td.className = 'table-success';
                                } else if (newScore >= 80) {
                                    td.className = 'table-info';
                                } else if (newScore >= 60) {
                                    td.className = 'table-warning';
                                } else {
                                    td.className = 'table-danger';
                                }
                                
                                // 更新内存中的分数数据
                                if (studentScores[studentId]) {
                                    studentScores[studentId].scores[subject] = newScore;
                                }
                                
                                // 更新排序数组中的分数
                                const student = studentsArray.find(s => s.id === studentId);
                                if (student) {
                                    student.scores[subject] = newScore;
                                }
                                
                                // 如果当前正在按这个科目排序，则重新排序并刷新表格
                                const activeSort = document.querySelector('th.sortable[data-sort-direction]');
                                if (activeSort && activeSort.getAttribute('data-sort-by') === subject) {
                                    activeSort.click();
                                }
                            } else {
                                // 恢复原始显示
                                this.innerHTML = originalScore;
                            }
                        });
                };
                
                // 添加事件监听器
                input.addEventListener('blur', handleComplete);
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        handleComplete();
                        e.preventDefault();
                    }
                });
            });
        });
    }
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
                            ${subjects.map(subject => {
                                const scoreData = student.scores[subject];
                                if (!scoreData) return '<td>-</td>';
                                
                                const score = scoreData.score;
                                const isLeave = scoreData.leave_status;
                                
                                if (isLeave) {
                                    return '<td><span class="badge bg-secondary">请假</span></td>';
                                } else if (score !== null) {
                                    return `<td>${score}</td>`;
                                } else {
                                    return '<td>-</td>';
                                }
                            }).join('')}
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
                            ${subjects.map(subject => {
                                const scoreData = student.scores[subject];
                                if (!scoreData) return '<td>-</td>';
                                
                                const score = scoreData.score;
                                const isLeave = scoreData.leave_status;
                                
                                if (isLeave) {
                                    return '<td><span class="badge bg-secondary">请假</span></td>';
                                } else if (score !== null) {
                                    return `<td>${score}</td>`;
                                } else {
                                    return '<td>-</td>';
                                }
                            }).join('')}
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

/**
 * 删除考试
 * @param {number} examId 考试ID
 */
function deleteExam(examId) {
    // 显示加载中
    showNotification('info', '正在删除考试...');
    
    // 发送删除请求
    fetch(`/api/exams/${examId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showNotification('success', '考试删除成功');
            
            // 刷新考试列表
            loadExams();
        } else {
            showNotification('error', data.message || '删除考试失败');
        }
    })
    .catch(error => {
        console.error('删除考试出错:', error);
        showNotification('error', '删除考试失败: ' + error.message);
    });
}

/**
 * 更新考试信息
 */
function updateExam() {
    // 获取表单数据
    const examId = document.getElementById('editExamId').value;
    const examName = document.getElementById('editExamNameInput').value.trim();
    const examDate = document.getElementById('editExamDateInput').value;
    
    // 获取选中的学科
    const subjects = [];
    document.querySelectorAll('.edit-subject-checkbox:checked').forEach(cb => {
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
        subjects: subjects,
        _method: 'PUT' // 添加方法覆盖参数，以支持某些不接受PUT的环境
    };
    
    // 如果是管理员，可能需要提供班级ID
    if (currentClassId) {
        requestData.class_id = currentClassId;
    }
    
    // 发送请求 - 尝试使用POST方法，但在服务器端被解释为PUT
    fetch(`/api/exams/${examId}`, {
        method: 'POST', // 改为POST，但在数据中指定_method为PUT
        headers: {
            'Content-Type': 'application/json',
            'X-HTTP-Method-Override': 'PUT' // 添加HTTP方法覆盖头
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showNotification('success', '考试更新成功');
            
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('editExamModal')).hide();
            
            // 刷新考试列表
            loadExams();
        } else {
            showNotification('error', data.message || '更新考试失败');
        }
    })
    .catch(error => {
        console.error('更新考试出错:', error);
        showNotification('error', '更新考试失败: ' + error.message);
    });
}

/**
 * 更新学生单科成绩
 * @param {number} examId 考试ID
 * @param {string} studentId 学生ID
 * @param {string} subject 学科
 * @param {number} score 分数
 * @param {number} leaveStatus 请假状态，0表示正常，1表示请假
 * @returns {Promise<boolean>} 是否更新成功
 */
function updateScore(examId, studentId, subject, score, leaveStatus = 0) {
    // 显示加载中
    showNotification('info', '正在更新成绩...');
    
    // 准备请求数据
    const requestData = {
        exam_id: examId,
        student_id: studentId,
        subject: subject,
        score: score,
        leave_status: leaveStatus
    };
    
    // 发送请求
    return fetch(`/api/exams/${examId}/scores/update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showNotification('success', '成绩更新成功');
            return true;
        } else {
            showNotification('error', data.message || '成绩更新失败');
            return false;
        }
    })
    .catch(error => {
        console.error('更新成绩出错:', error);
        showNotification('error', '更新成绩失败: ' + error.message);
        return false;
    });
}

/**
 * 删除学生全部成绩
 * @param {number} examId 考试ID
 * @param {string} studentId 学生ID
 */
function deleteStudentScores(examId, studentId) {
    // 显示加载中
    showNotification('info', '正在删除成绩...');
    
    // 发送请求
    fetch(`/api/exams/${examId}/scores/delete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            exam_id: examId,
            student_id: studentId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showNotification('success', '成绩删除成功');
            
            // 重新加载考试详情以刷新视图
            loadExamDetail(examId);
        } else {
            showNotification('error', data.message || '成绩删除失败');
        }
    })
    .catch(error => {
        console.error('删除成绩出错:', error);
        showNotification('error', '删除成绩失败: ' + error.message);
    });
}

/**
 * 打开编辑成绩模态框
 * @param {string} studentId 学生ID
 * @param {string} studentName 学生姓名
 * @param {Array} subjects 学科列表
 * @param {Object} scores 成绩数据
 */
function openEditScoresModal(studentId, studentName, subjects, scores) {
    // 创建模态框HTML
    const modalId = 'editScoresModal';
    
    // 检查是否已存在模态框
    let modal = document.getElementById(modalId);
    if (!modal) {
        // 创建模态框
        modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal fade';
        modal.tabIndex = -1;
        modal.setAttribute('aria-labelledby', 'editScoresModalLabel');
        modal.setAttribute('aria-hidden', 'true');
        
        // 设置模态框内容
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="editScoresModalLabel">编辑学生成绩</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editScoresForm">
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label class="form-label">学生</label>
                                    <input type="text" class="form-control" id="editScoresStudentName" readonly>
                                    <input type="hidden" id="editScoresStudentId">
                                </div>
                            </div>
                            <div class="row" id="editScoresSubjectsContainer">
                                <!-- 学科输入字段将由JS动态生成 -->
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" id="saveScoresBtn">保存修改</button>
                    </div>
                </div>
            </div>
        `;
        
        // 添加到页面
        document.body.appendChild(modal);
    }
    
    // 显示学生基本信息
    document.getElementById('editScoresStudentName').value = `${studentName} (${studentId})`;
    document.getElementById('editScoresStudentId').value = studentId;
    
    // 清空并添加学科输入字段
    const container = document.getElementById('editScoresSubjectsContainer');
    container.innerHTML = '';
    
    subjects.forEach((subject, index) => {
        const score = scores[subject] !== undefined ? scores[subject] : '';
        const isLeave = score === 0;  // 判断是否为请假状态
        
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-3';
        col.innerHTML = `
            <label class="form-label">${subject}</label>
            <div class="input-group">
            <input type="number" class="form-control edit-score-input" 
                   data-subject="${subject}" 
                       value="${isLeave ? '' : score}" 
                       min="0" max="100" step="0.5"
                       ${isLeave ? 'disabled' : ''}>
                <div class="input-group-text">
                    <div class="form-check form-switch">
                        <input class="form-check-input leave-checkbox" type="checkbox" 
                               data-subject="${subject}" 
                               id="leaveCheckbox-${subject.replace(/[^a-zA-Z0-9]/g, '')}"
                               ${isLeave ? 'checked' : ''}>
                        <label class="form-check-label" for="leaveCheckbox-${subject.replace(/[^a-zA-Z0-9]/g, '')}">
                            请假
                        </label>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(col);
    });
    
    // 添加请假勾选的事件处理
    document.querySelectorAll('.leave-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const subject = this.getAttribute('data-subject');
            const scoreInput = container.querySelector(`.edit-score-input[data-subject="${subject}"]`);
            
            if (this.checked) {
                // 请假状态
                scoreInput.disabled = true;
                scoreInput.value = '';  // 清空分数
            } else {
                // 非请假状态
                scoreInput.disabled = false;
            }
        });
    });
    
    // 保存按钮事件
    document.getElementById('saveScoresBtn').onclick = function() {
        saveEditedScores(studentId);
    };
    
    // 显示模态框
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

/**
 * 保存编辑后的成绩
 * @param {string} studentId 学生ID
 */
function saveEditedScores(studentId) {
    // 收集所有成绩输入和请假状态
    const scoreInputs = document.querySelectorAll('.edit-score-input');
    const leaveCheckboxes = document.querySelectorAll('.leave-checkbox');
    const scoreUpdates = [];
    
    // 验证并收集成绩数据
    let hasErrors = false;
    
    // 遍历所有学科
    for (let i = 0; i < scoreInputs.length; i++) {
        const input = scoreInputs[i];
        const subject = input.getAttribute('data-subject');
        
        // 获取对应的请假复选框
        const leaveCheckbox = document.querySelector(`.leave-checkbox[data-subject="${subject}"]`);
        const isLeave = leaveCheckbox && leaveCheckbox.checked;
        
        if (isLeave) {
            // 请假状态，分数设为0
            scoreUpdates.push({
                subject: subject,
                score: 0,
                leave_status: 1
            });
        } else {
            // 非请假状态，检查分数是否有效
        const scoreValue = input.value.trim();
        
        if (scoreValue === '') {
            // 空值跳过
                continue;
        }
        
        const score = parseFloat(scoreValue);
        
        // 验证分数范围
        if (isNaN(score) || score < 0 || score > 100) {
            showNotification('error', `${subject} 的分数必须在0-100之间`);
            hasErrors = true;
                continue;
        }
        
        // 添加到更新列表
        scoreUpdates.push({
            subject: subject,
                score: score,
                leave_status: 0
        });
        }
    }
    
    // 如果有错误，不继续
    if (hasErrors) {
        return;
    }
    
    // 如果没有更改，直接关闭
    if (scoreUpdates.length === 0) {
        bootstrap.Modal.getInstance(document.getElementById('editScoresModal')).hide();
        return;
    }
    
    // 显示加载中
    showNotification('info', '正在更新成绩...');
    
    // 批量更新成绩
    const requests = scoreUpdates.map(update => {
        return updateScore(currentExam.id, studentId, update.subject, update.score, update.leave_status);
    });
    
    // 等待所有请求完成
    Promise.all(requests)
        .then(results => {
            // 检查是否全部成功
            const allSuccess = results.every(result => result === true);
            
            if (allSuccess) {
                showNotification('success', '所有成绩更新成功');
                
                // 关闭模态框
                bootstrap.Modal.getInstance(document.getElementById('editScoresModal')).hide();
                
                // 重新加载考试详情以刷新视图
                loadExamDetail(currentExam.id);
            } else {
                showNotification('warning', '部分成绩更新失败，请重试');
            }
        })
        .catch(error => {
            console.error('批量更新成绩出错:', error);
            showNotification('error', '更新成绩失败: ' + error.message);
        });
}

/**
 * 更新全选复选框状态
 */
function updateSelectAllCheckbox() {
    const totalCheckboxes = document.querySelectorAll('.exam-checkbox').length;
    const checkedCheckboxes = document.querySelectorAll('.exam-checkbox:checked').length;
    
    const selectAllCheckbox = document.getElementById('selectAllExams');
    
    if (totalCheckboxes === 0) {
        selectAllCheckbox.disabled = true;
        selectAllCheckbox.checked = false;
    } else {
        selectAllCheckbox.disabled = false;
        selectAllCheckbox.checked = totalCheckboxes === checkedCheckboxes;
    }
}

/**
 * 更新对比按钮状态
 */
function updateCompareButton() {
    // 获取所有选中的考试ID
    selectedExams = Array.from(document.querySelectorAll('.exam-checkbox:checked')).map(checkbox => checkbox.value);
    
    // 更新按钮状态
    const compareButton = document.getElementById('compareExamsBtn');
    
    if (selectedExams.length >= 2) {
        compareButton.disabled = false;
    } else {
        compareButton.disabled = true;
    }
    
    // 更新全选状态
    updateSelectAllCheckbox();
}

/**
 * 对比选中的考试
 */
function compareSelectedExams() {
    if (selectedExams.length < 2) {
        showNotification('warning', '请至少选择两次考试进行对比');
        return;
    }
    
    // 显示加载中
    showNotification('info', '正在加载对比数据...');
    
    // 发送请求获取对比数据
    fetch('/api/exams/compare', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            exam_ids: selectedExams
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 保存对比数据
            compareData = data.results;
            
            // 渲染对比分析页面
            renderComparisonPage(compareData);
            
            // 隐藏考试列表，显示对比结果
            document.getElementById('examsContainer').parentElement.parentElement.style.display = 'none';
            document.getElementById('compareResultContainer').style.display = 'block';
        } else {
            showNotification('error', data.message || '加载对比数据失败');
        }
    })
    .catch(error => {
        console.error('加载对比数据出错:', error);
        showNotification('error', '加载对比数据失败: ' + error.message);
    });
}

/**
 * 渲染对比分析页面
 * @param {Object} data 对比数据
 */
function renderComparisonPage(data) {
    // 渲染参与对比的考试列表
    renderComparedExamsList(data.exams);
    
    // 设置学科选择下拉框
    setupCompareSubjectSelect(data);
    
    // 渲染对比图表
    renderComparisonCharts(data);
    
    // 渲染学生成绩对比表格
    renderStudentComparisonTable(data);
}

/**
 * 渲染参与对比的考试列表
 * @param {Array} exams 考试数组
 */
function renderComparedExamsList(exams) {
    const container = document.getElementById('comparedExamsList');
    
    const examsList = exams.map(exam => {
        const examDate = new Date(exam.date).toLocaleDateString('zh-CN');
        return `
            <div class="badge bg-info p-2 me-2 mb-2">
                ${exam.name}（${examDate}）
            </div>
        `;
    }).join('');
    
    container.innerHTML = examsList;
}

/**
 * 设置对比学科选择下拉框
 * @param {Object} data 对比数据
 */
function setupCompareSubjectSelect(data) {
    const select = document.getElementById('compareSubjectSelect');
    select.innerHTML = '';
    
    // 添加公共学科选项
    if (data.common_subjects && data.common_subjects.length > 0) {
        // 优先使用所有考试共有的学科
        data.common_subjects.forEach(subject => {
            const option = document.createElement('option');
            option.value = subject;
            option.textContent = subject;
            select.appendChild(option);
        });
    } else if (data.all_subjects && data.all_subjects.length > 0) {
        // 如果没有共有学科，列出所有学科
        data.all_subjects.forEach(subject => {
            const option = document.createElement('option');
            option.value = subject;
            option.textContent = subject;
            select.appendChild(option);
        });
    } else {
        // 如果没有任何学科数据，显示空选项
        const option = document.createElement('option');
        option.value = '';
        option.textContent = '没有可用的学科';
        select.appendChild(option);
    }
    
    // 触发change事件，更新图表和表格
    if (select.options.length > 0) {
        select.dispatchEvent(new Event('change'));
    }
}

/**
 * 渲染对比图表
 * @param {Object} data 对比数据
 */
function renderComparisonCharts(data) {
    // 销毁现有图表
    ['averageScoreComparisonChart', 'passRateComparisonChart', 'excellentRateComparisonChart', 
     'scoreDistributionComparisonChart', 'radarComparisonChart', 'scoreChangesDistributionChart'].forEach(chartId => {
        if (charts[chartId]) {
            charts[chartId].destroy();
            delete charts[chartId];
        }
    });
    
    // 获取当前选择的学科
    const selectedSubject = document.getElementById('compareSubjectSelect').value;
    
    if (!selectedSubject) {
        return;
    }
    
    // 准备图表数据
    const labels = data.exams.map(exam => exam.name);
    
    // 1. 平均分对比图表
    const averageScores = data.exams.map(exam => {
        return exam.stats[selectedSubject] ? exam.stats[selectedSubject].average : 0;
    });
    
    const averageScoreCtx = document.getElementById('averageScoreComparisonChart').getContext('2d');
    charts['averageScoreComparisonChart'] = new Chart(averageScoreCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `${selectedSubject}平均分`,
                data: averageScores,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
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
            },
            plugins: {
                title: {
                    display: true,
                    text: `${selectedSubject}学科平均分对比`
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `平均分: ${context.raw}`;
                        }
                    }
                }
            }
        }
    });
    
    // 2. 及格率对比图表
    const passRates = data.exams.map(exam => {
        return exam.stats[selectedSubject] ? exam.stats[selectedSubject].pass_rate : 0;
    });
    
    const passRateCtx = document.getElementById('passRateComparisonChart').getContext('2d');
    charts['passRateComparisonChart'] = new Chart(passRateCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `${selectedSubject}及格率`,
                data: passRates,
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: `${selectedSubject}学科及格率对比`
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `及格率: ${context.raw}%`;
                        }
                    }
                }
            }
        }
    });
    
    // 3. 优秀率对比图表
    const excellentRates = data.exams.map(exam => {
        return exam.stats[selectedSubject] ? exam.stats[selectedSubject].excellent_rate : 0;
    });
    
    const excellentRateCtx = document.getElementById('excellentRateComparisonChart').getContext('2d');
    charts['excellentRateComparisonChart'] = new Chart(excellentRateCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `${selectedSubject}优秀率`,
                data: excellentRates,
                backgroundColor: 'rgba(255, 159, 64, 0.6)',
                borderColor: 'rgba(255, 159, 64, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: `${selectedSubject}学科优秀率对比`
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `优秀率: ${context.raw}%`;
                        }
                    }
                }
            }
        }
    });
    
    // 4. 分数段分布对比图表
    const distributionDatasets = [];
    const distributionLabels = ['0-59', '60-69', '70-79', '80-89', '90-100'];
    
    data.exams.forEach((exam, index) => {
        if (exam.stats[selectedSubject]) {
            const distribution = exam.stats[selectedSubject].score_distribution;
            const distributionData = [
                distribution['0-59'] || 0,
                distribution['60-69'] || 0,
                distribution['70-79'] || 0,
                distribution['80-89'] || 0,
                distribution['90-100'] || 0
            ];
            
            distributionDatasets.push({
                label: exam.name,
                data: distributionData,
                backgroundColor: getChartColor(index, 0.6),
                borderColor: getChartColor(index, 1),
                borderWidth: 1
            });
        }
    });
    
    const distributionCtx = document.getElementById('scoreDistributionComparisonChart').getContext('2d');
    charts['scoreDistributionComparisonChart'] = new Chart(distributionCtx, {
        type: 'bar',
        data: {
            labels: distributionLabels,
            datasets: distributionDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '人数'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '分数段'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: `${selectedSubject}学科分数段分布对比`
                }
            }
        }
    });
    
    // 5. 渲染雷达图
    renderRadarComparisonChart(data, selectedSubject);
    
    // 6. 渲染成绩变化分布图
    renderScoreChangesDistributionChart(data, selectedSubject);
}

/**
 * 渲染雷达图对比
 * @param {Object} data 对比数据
 * @param {string} subject 学科
 */
function renderRadarComparisonChart(data, subject) {
    // 准备雷达图数据
    const radarDatasets = [];
    
    // 定义雷达图指标（平均分、及格率、优秀率、最高分、最低分）
    const indicators = ['平均分', '及格率', '优秀率', '最高分', '最低分'];
    
    // 为指标准备数据
    data.exams.forEach((exam, index) => {
        if (exam.stats[subject]) {
            // 标准化数据，使其在雷达图上显示合理
            const stats = exam.stats[subject];
            const radarData = [
                // 平均分值域为 0-100，将平均分除以100，使得取值范围为0-1
                stats.average / 100,
                // 及格率值域为 0-100%，将及格率除以100，使得取值范围为0-1
                stats.pass_rate / 100,
                // 优秀率值域为 0-100%，将优秀率除以100，使得取值范围为0-1
                stats.excellent_rate / 100,
                // 最高分值域为 0-100，将最高分除以100，使得取值范围为0-1
                stats.max / 100,
                // 最低分可能较低，将最低分除以100，使得取值范围为0-1
                stats.min / 100
            ];
            
            radarDatasets.push({
                label: exam.name,
                data: radarData,
                fill: true,
                backgroundColor: getChartColor(index, 0.2),
                borderColor: getChartColor(index, 1),
                pointBackgroundColor: getChartColor(index, 1),
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: getChartColor(index, 1)
            });
        }
    });
    
    // 创建雷达图
    const radarCtx = document.getElementById('radarComparisonChart').getContext('2d');
    charts['radarComparisonChart'] = new Chart(radarCtx, {
        type: 'radar',
        data: {
            labels: indicators,
            datasets: radarDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                line: {
                    borderWidth: 2
                }
            },
            scales: {
                r: {
                    angleLines: {
                        display: true
                    },
                    suggestedMin: 0,
                    suggestedMax: 1,
                    ticks: {
                        // 将0-1的比例值转换为百分比显示
                        callback: function(value) {
                            return (value * 100) + '%';
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: `${subject}学科各项指标对比`
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const dataIndex = context.dataIndex;
                            const value = context.raw;
                            const indicator = indicators[dataIndex];
                            
                            // 根据不同指标使用不同的显示格式
                            if (dataIndex === 0) { // 平均分
                                return `${indicator}: ${(value * 100).toFixed(1)}分`;
                            } else if (dataIndex === 1 || dataIndex === 2) { // 及格率/优秀率
                                return `${indicator}: ${(value * 100).toFixed(1)}%`;
                            } else { // 最高分/最低分
                                return `${indicator}: ${(value * 100).toFixed(1)}分`;
                            }
                        }
                    }
                }
            }
        }
    });
}

/**
 * 渲染学生成绩变化分布图
 * @param {Object} data 对比数据
 * @param {string} subject 学科
 */
function renderScoreChangesDistributionChart(data, subject) {
    // 如果只有一次考试，无法分析变化
    if (data.exams.length < 2) {
        const ctx = document.getElementById('scoreChangesDistributionChart').getContext('2d');
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#666';
        ctx.textAlign = 'center';
        ctx.fillText('需要至少两次考试才能分析成绩变化', ctx.canvas.width / 2, ctx.canvas.height / 2);
        return;
    }
    
    // 计算学生成绩变化
    const studentChanges = [];
    
    // 获取第一次和最后一次考试的ID
    const firstExamId = data.exams[0].id;
    const lastExamId = data.exams[data.exams.length - 1].id;
    
    // 遍历学生数据，计算变化
    data.students.forEach(student => {
        // 检查是否有该学科的成绩
        if (student.scores[firstExamId] && 
            student.scores[firstExamId][subject] !== undefined &&
            student.scores[lastExamId] && 
            student.scores[lastExamId][subject] !== undefined) {
            
            const firstScore = student.scores[firstExamId][subject];
            const lastScore = student.scores[lastExamId][subject];
            const change = lastScore - firstScore;
            
            studentChanges.push(change);
        }
    });
    
    // 如果没有变化数据，显示提示
    if (studentChanges.length === 0) {
        const ctx = document.getElementById('scoreChangesDistributionChart').getContext('2d');
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#666';
        ctx.textAlign = 'center';
        ctx.fillText('没有足够的学生数据来分析成绩变化', ctx.canvas.width / 2, ctx.canvas.height / 2);
        return;
    }
    
    // 定义变化区间
    const intervals = [
        '下降10分以上',
        '下降5-10分',
        '下降0-5分',
        '提高0-5分',
        '提高5-10分',
        '提高10分以上'
    ];
    
    // 统计各区间的学生数量
    const counts = [0, 0, 0, 0, 0, 0];
    
    studentChanges.forEach(change => {
        if (change <= -10) {
            counts[0]++;
        } else if (change <= -5) {
            counts[1]++;
        } else if (change < 0) {
            counts[2]++;
        } else if (change <= 5) {
            counts[3]++;
        } else if (change <= 10) {
            counts[4]++;
        } else {
            counts[5]++;
        }
    });
    
    // 准备堆叠柱状图数据
    const datasets = [
        {
            label: '下降',
            data: [counts[0], counts[1], counts[2], 0, 0, 0],
            backgroundColor: 'rgba(231, 76, 60, 0.7)'
        },
        {
            label: '提高',
            data: [0, 0, 0, counts[3], counts[4], counts[5]],
            backgroundColor: 'rgba(46, 204, 113, 0.7)'
        }
    ];
    
    // 创建图表
    const ctx = document.getElementById('scoreChangesDistributionChart').getContext('2d');
    charts['scoreChangesDistributionChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: intervals,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: '变化区间'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '学生人数'
                    },
                    ticks: {
                        precision: 0
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: `${subject}学科学生成绩变化分布`
                },
                subtitle: {
                    display: true,
                    text: `从"${data.exams[0].name}"到"${data.exams[data.exams.length-1].name}"的变化`,
                    padding: {
                        bottom: 10
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            return tooltipItems[0].label;
                        },
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw}人`;
                        },
                        footer: function(tooltipItems) {
                            const dataIndex = tooltipItems[0].dataIndex;
                            const value = tooltipItems[0].raw;
                            const total = studentChanges.length;
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `占比: ${percentage}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * 获取图表颜色
 * @param {number} index 索引
 * @param {number} alpha 透明度
 * @returns {string} 颜色字符串
 */
function getChartColor(index, alpha) {
    const colors = [
        `rgba(54, 162, 235, ${alpha})`,   // 蓝色
        `rgba(255, 99, 132, ${alpha})`,   // 红色
        `rgba(75, 192, 192, ${alpha})`,   // 绿色
        `rgba(255, 159, 64, ${alpha})`,   // 橙色
        `rgba(153, 102, 255, ${alpha})`,  // 紫色
        `rgba(255, 205, 86, ${alpha})`,   // 黄色
        `rgba(201, 203, 207, ${alpha})`,  // 灰色
        `rgba(0, 204, 150, ${alpha})`,    // 青绿色
        `rgba(255, 100, 255, ${alpha})`,  // 粉色
        `rgba(102, 102, 255, ${alpha})`   // 淡紫色
    ];
    
    return colors[index % colors.length];
}

/**
 * 计算学生排名
 * @param {Array} students 学生数组
 * @param {string} subject 学科
 * @param {number} examId 考试ID
 * @returns {Object} 排名映射对象 {学生ID: 排名}
 */
function calculateRanking(students, subject, examId) {
    // 筛选出有该科目成绩的学生
    const studentsWithScores = students.filter(student => 
        student.scores[examId] && 
        student.scores[examId][subject] !== undefined &&
        student.scores[examId][subject] !== null
    );
    
    // 按分数从高到低排序
    studentsWithScores.sort((a, b) => 
        b.scores[examId][subject] - a.scores[examId][subject]
    );
    
    // 创建排名映射
    const rankings = {};
    let currentRank = 1;
    let previousScore = null;
    let sameRankCount = 0;
    
    studentsWithScores.forEach((student, index) => {
        const score = student.scores[examId][subject];
        
        // 如果分数与前一个相同，使用相同排名
        if (previousScore !== null && score === previousScore) {
            sameRankCount++;
        } else {
            // 新的分数，排名更新为当前位置
            currentRank = index + 1;
            sameRankCount = 0;
        }
        
        // 保存当前学生排名
        rankings[student.student_id] = currentRank;
        previousScore = score;
    });
    
    return rankings;
}

/**
 * 计算学生的排名变化和分数变化率
 * @param {Array} students 学生数组
 * @param {Array} exams 考试数组
 * @param {string} subject 学科
 * @returns {Object} 增强的学生数据
 */
function calculateStudentChanges(students, exams, subject) {
    // 计算每次考试的排名
    const examRankings = {};
    exams.forEach(exam => {
        examRankings[exam.id] = calculateRanking(students, subject, exam.id);
    });
    
    // 增强学生数据
    return students.map(student => {
        // 复制基本信息
        const enhancedStudent = {
            ...student,
            scores: [], // 将重新填充
            rankings: [], // 添加排名信息
            rankChange: null, // 排名变化
            scoreChange: null, // 分数变化
            changeRate: null // 变化率
        };
        
        // 获取每次考试的成绩和排名
        exams.forEach(exam => {
            const examId = exam.id;
            let score = null;
            let ranking = null;
            
            // 获取成绩
            if (student.scores[examId] && student.scores[examId][subject] !== undefined) {
                score = student.scores[examId][subject];
            }
            
            // 获取排名
            if (score !== null && examRankings[examId] && examRankings[examId][student.student_id]) {
                ranking = examRankings[examId][student.student_id];
            }
            
            enhancedStudent.scores.push(score);
            enhancedStudent.rankings.push(ranking);
        });
        
        // 计算分数变化和排名变化
        const validScores = enhancedStudent.scores.filter(s => s !== null);
        const validRankings = enhancedStudent.rankings.filter(r => r !== null);
        
        if (validScores.length >= 2) {
            // 分数变化
            const firstScore = validScores[0];
            const lastScore = validScores[validScores.length - 1];
            enhancedStudent.scoreChange = firstScore - lastScore;
            
            // 变化率
            if (lastScore > 0) { // 使用最后一个分数作为基准
                enhancedStudent.changeRate = (enhancedStudent.scoreChange / lastScore * 100).toFixed(1);
            }
            
            // 最大分差
            enhancedStudent.maxDiff = Math.max(...validScores) - Math.min(...validScores);
        }
        
        // 计算排名变化
        if (validRankings.length >= 2) {
            const firstRank = validRankings[0];
            const lastRank = validRankings[validRankings.length - 1];
            // 注意：排名下降是正向变化，所以用第一次减去最后一次
            enhancedStudent.rankChange = firstRank - lastRank;
        }
        
        return enhancedStudent;
    });
}

/**
 * 渲染学生成绩对比表格
 * @param {Object} data 对比数据
 */
function renderStudentComparisonTable(data) {
    // 获取表头和表体元素
    const tableHead = document.getElementById('compareStudentsTableHead');
    const tableBody = document.getElementById('compareStudentsTableBody');
    
    // 获取当前选择的学科
    const selectedSubject = document.getElementById('compareSubjectSelect').value;
    
    if (!selectedSubject) {
        tableHead.innerHTML = '<tr><th>请选择一个学科进行对比</th></tr>';
        tableBody.innerHTML = '';
        return;
    }
    
    // 更新页面标题，显示比较关系
    if (data.exams.length >= 2) {
        const newestExamName = data.exams[0].name;
        const previousExamName = data.exams[1].name;
        const newestExamDate = new Date(data.exams[0].date).toLocaleDateString('zh-CN');
        const previousExamDate = new Date(data.exams[1].date).toLocaleDateString('zh-CN');
        const titleText = `学生个人成绩对比 (${newestExamName}[${newestExamDate}] 相对于 ${previousExamName}[${previousExamDate}])`;
        
        // 更新页面标题
        const titleElement = document.getElementById('compareTitle');
        if (titleElement) {
            titleElement.textContent = titleText;
        }
    }
    
    // 生成表头
    let headerRow = '<tr><th>学号</th><th>姓名</th>';
    
    // 添加考试名称列（已按时间降序排序，最新的在前）
    data.exams.forEach((exam, index) => {
        // 格式化日期为 YYYY-MM-DD
        const examDate = new Date(exam.date).toLocaleDateString('zh-CN');
        // 显示考试名称和日期，为最新考试添加标记
        let headerClass = '';
        if (index === 0) {
            headerClass = 'text-primary fw-bold';  // 最新考试加粗显示
        }
        headerRow += `<th class="${headerClass}">${exam.name}<br><small>(${examDate})${index === 0 ? ' 最新' : ''}</small></th>`;
    });
    
    // 添加分差列，如果有两次以上考试
    if (data.exams.length >= 2) {
        headerRow += '<th>最大分差</th><th>排名变化</th><th>分数变化</th><th>变化率</th>';
    }
    
    headerRow += '</tr>';
    tableHead.innerHTML = headerRow;
    
    // 过滤出包含所选学科成绩的学生
    const validStudents = data.students.filter(student => {
        let hasScore = false;
        for (const examId in student.scores) {
            if (student.scores[examId][selectedSubject] !== undefined) {
                hasScore = true;
                break;
            }
        }
        return hasScore;
    });
    
    // 计算学生的排名变化和分数变化率
    const enhancedStudents = calculateStudentChanges(validStudents, data.exams, selectedSubject);
    
    // 过滤出有效分数（至少参加了2次考试）的学生
    const validStudentsWithChange = enhancedStudents.filter(student => 
        student.scores.filter(score => score !== null).length >= 2
    );
    
    // 按照变化程度排序，先展示进步最大的学生，再展示退步最明显的学生
    validStudentsWithChange.sort((a, b) => b.scoreChange - a.scoreChange);
    
    // 找出进步和退步比较大的学生
    // 使用四分位数来确定"比较大"的标准
    const changes = validStudentsWithChange.map(student => student.scoreChange);
    
    // 计算Q3（进步学生第三四分位数）
    const positiveChanges = changes.filter(change => change > 0);
    let significantImprovement = 5; // 默认值
    if (positiveChanges.length > 0) {
        positiveChanges.sort((a, b) => a - b);
        const q3Index = Math.floor(positiveChanges.length * 0.75);
        significantImprovement = positiveChanges[q3Index] || 5;
    }
    
    // 计算Q1（退步学生第一四分位数）
    const negativeChanges = changes.filter(change => change < 0);
    let significantDecline = -5; // 默认值
    if (negativeChanges.length > 0) {
        negativeChanges.sort((a, b) => a - b);
        const q1Index = Math.floor(negativeChanges.length * 0.25);
        significantDecline = negativeChanges[q1Index] || -5;
    }
    
    // 生成表格内容
    let rows = '';
    
    // 生成分组标题 - 进步明显的学生
    if (validStudentsWithChange.some(s => s.scoreChange > 0)) {
        rows += `
            <tr class="table-success">
                <td colspan="${data.exams.length + 6}" class="text-center fw-bold">
                    进步明显的学生 (提升 ${significantImprovement.toFixed(1)} 分以上)
                </td>
            </tr>
        `;
        
        // 过滤出进步明显的学生
        const improvedStudents = validStudentsWithChange.filter(student => student.scoreChange >= significantImprovement);
        
        // 添加进步明显的学生行
        improvedStudents.forEach(student => {
            rows += generateEnhancedStudentRow(student, data.exams, selectedSubject, 'success');
        });
        
        // 如果没有进步明显的学生，显示提示
        if (improvedStudents.length === 0) {
            rows += `
                <tr>
                    <td colspan="${data.exams.length + 6}" class="text-center">
                        无进步明显的学生
                    </td>
                </tr>
            `;
        }
    }
    
    // 生成分组标题 - 成绩稳定的学生
    rows += `
        <tr class="table-light">
            <td colspan="${data.exams.length + 6}" class="text-center fw-bold">
                成绩稳定的学生
            </td>
        </tr>
    `;
    
    // 过滤出成绩稳定的学生
    const stableStudents = validStudentsWithChange.filter(student => 
        student.scoreChange < significantImprovement && student.scoreChange > significantDecline
    );
    
    // 添加稳定学生行
    stableStudents.forEach(student => {
        rows += generateEnhancedStudentRow(student, data.exams, selectedSubject, 'light');
    });
    
    // 如果没有稳定的学生，显示提示
    if (stableStudents.length === 0) {
        rows += `
            <tr>
                <td colspan="${data.exams.length + 6}" class="text-center">
                    无成绩稳定的学生
                </td>
            </tr>
        `;
    }
    
    // 生成分组标题 - 退步明显的学生
    if (validStudentsWithChange.some(s => s.scoreChange < 0)) {
        rows += `
            <tr class="table-danger">
                <td colspan="${data.exams.length + 6}" class="text-center fw-bold">
                    退步明显的学生 (下降 ${Math.abs(significantDecline).toFixed(1)} 分以上)
                </td>
            </tr>
        `;
        
        // 过滤出退步明显的学生
        const declinedStudents = validStudentsWithChange.filter(student => student.scoreChange <= significantDecline);
        
        // 添加退步明显的学生行
        declinedStudents.forEach(student => {
            rows += generateEnhancedStudentRow(student, data.exams, selectedSubject, 'danger');
        });
        
        // 如果没有退步明显的学生，显示提示
        if (declinedStudents.length === 0) {
            rows += `
                <tr>
                    <td colspan="${data.exams.length + 6}" class="text-center">
                        无退步明显的学生
                    </td>
                </tr>
            `;
        }
    }
    
    // 未参加足够次数考试的学生
    const notEnoughExams = enhancedStudents.filter(student => 
        student.scores.filter(score => score !== null).length < 2
    );
    
    if (notEnoughExams.length > 0) {
        rows += `
            <tr class="table-secondary">
                <td colspan="${data.exams.length + 6}" class="text-center fw-bold">
                    未参加足够次数考试的学生
                </td>
            </tr>
        `;
        
        // 添加未参加足够次数考试的学生行
        notEnoughExams.forEach(student => {
            rows += generateEnhancedStudentRow(student, data.exams, selectedSubject, 'secondary');
        });
    }
    
    tableBody.innerHTML = rows || '<tr><td colspan="' + (data.exams.length + 6) + '" class="text-center">暂无成绩数据</td></tr>';
}

/**
 * 生成增强的学生成绩行
 * @param {Object} student 增强后的学生数据
 * @param {Array} exams 考试数组（已按时间降序排序，最新的在前）
 * @param {string} subject 学科
 * @param {string} rowClass 行样式类
 * @returns {string} 表格行HTML
 */
function generateEnhancedStudentRow(student, exams, subject, rowClass = '') {
    let row = `<tr${rowClass ? ` class="table-${rowClass}"` : ''}>`;
    
    // 学号
    row += `<td>${student.student_id}</td>`;
    
    // 添加可点击的学生姓名
    row += `<td>
        <a href="javascript:void(0);" class="student-name-link" 
           data-student-id="${student.student_id}" 
           data-student-name="${student.student_name}">
            ${student.student_name}
        </a>
    </td>`;
    
    // 添加每次考试的成绩和排名（已按时间降序排序，首个为最新考试）
    student.scores.forEach((score, index) => {
        // 为基于索引获取的成绩应用颜色样式
        let cellClass = '';
        let rankDisplay = '';
        
        if (score !== null) {
            if (score >= 90) cellClass = 'table-success';
            else if (score >= 80) cellClass = 'table-info';
            else if (score >= 60) cellClass = 'table-warning';
            else cellClass = 'table-danger';
            
            // 显示排名（如果有）
            if (student.rankings && student.rankings[index] !== null) {
                rankDisplay = ` <small class="text-muted">(第${student.rankings[index]}名)</small>`;
            }
        }
        
        // 为最新考试（第一个）添加加粗样式
        let cellStyle = '';
        if (index === 0) {
            cellStyle = ' style="font-weight: bold;"';
        }
        
        row += `<td${cellClass ? ` class="${cellClass}"` : ''}${cellStyle}>${score !== null ? score + rankDisplay : '-'}</td>`;
    });
    
    // 添加最大分差和变化指标（基于最新和前一次考试的比较）
    if (exams.length >= 2) {
        // 获取有效分数
        const validScores = student.scores.filter(score => score !== null);
        
        if (validScores.length >= 2) {
            // 最大分差
            row += `<td>${student.maxDiff.toFixed(1)}</td>`;
            
            // 排名变化
            let rankChangeHtml = '';
            if (student.rankChange !== null) {
                if (student.rankChange > 0) {
                    rankChangeHtml = `<span class="text-success">↑ ${student.rankChange} 名</span>`;
                } else if (student.rankChange < 0) {
                    rankChangeHtml = `<span class="text-danger">↓ ${Math.abs(student.rankChange)} 名</span>`;
                } else {
                    rankChangeHtml = `<span class="text-muted">→ 0</span>`;
                }
            } else {
                rankChangeHtml = '-';
            }
            row += `<td>${rankChangeHtml}</td>`;
            
            // 分数变化
            let scoreChangeHtml = '';
            if (student.scoreChange !== null) {
                if (student.scoreChange > 0) {
                    scoreChangeHtml = `<span class="text-success">↑ ${student.scoreChange.toFixed(1)}</span>`;
                } else if (student.scoreChange < 0) {
                    scoreChangeHtml = `<span class="text-danger">↓ ${Math.abs(student.scoreChange).toFixed(1)}</span>`;
                } else {
                    scoreChangeHtml = `<span class="text-muted">→ 0</span>`;
                }
            } else {
                scoreChangeHtml = '-';
            }
            row += `<td>${scoreChangeHtml}</td>`;
            
            // 变化率
            let changeRateHtml = '';
            if (student.changeRate !== null) {
                if (parseFloat(student.changeRate) > 0) {
                    changeRateHtml = `<span class="text-success">↑ ${student.changeRate}%</span>`;
                } else if (parseFloat(student.changeRate) < 0) {
                    changeRateHtml = `<span class="text-danger">↓ ${Math.abs(parseFloat(student.changeRate))}%</span>`;
                } else {
                    changeRateHtml = `<span class="text-muted">→ 0%</span>`;
                }
            } else {
                changeRateHtml = '-';
            }
            row += `<td>${changeRateHtml}</td>`;
        } else {
            // 对于未参加足够考试的学生，显示破折号
            row += `<td>-</td><td>-</td><td>-</td><td>-</td>`;
        }
    }
    
    row += '</tr>';
    return row;
}

/**
 * 学生个人成绩分析
 */
document.addEventListener('DOMContentLoaded', function() {
    // 监听学生姓名点击事件（使用事件委托）
    document.body.addEventListener('click', function(e) {
        if (e.target.classList.contains('student-name-link') || e.target.closest('.student-name-link')) {
            const link = e.target.classList.contains('student-name-link') ? e.target : e.target.closest('.student-name-link');
            const studentId = link.dataset.studentId;
            const studentName = link.dataset.studentName;
            
            // 打开学生分析模态框
            openStudentAnalysisModal(studentId, studentName);
        }
    });
});

/**
 * 检查元素是否存在，如果不存在则返回备用ID对应的元素
 * @param {string} primaryId 主要元素ID
 * @param {string} fallbackId 备用元素ID
 * @returns {HTMLElement|null} 找到的HTML元素或null
 */
function getElement(primaryId, fallbackId) {
    const primaryElement = document.getElementById(primaryId);
    if (primaryElement) {
        return primaryElement;
    }
    
    if (fallbackId) {
        return document.getElementById(fallbackId);
    }
    
    return null;
}

/**
 * 打开学生成绩分析模态框
 * @param {string|number} studentId 学生ID
 * @param {string} studentName 学生姓名
 */
function openStudentAnalysisModal(studentId, studentName) {
    // 尝试获取不同页面的元素
    const nameElement = getElement('studentName', 'studentAnalysisName');
    const idElement = getElement('studentId', 'studentAnalysisId');
    const classElement = getElement('studentAnalysisClass', null);
    const examCountElement = getElement('studentExamCount', null);
    const averageScoreElement = getElement('studentAverageScore', null);
    const scoreTrendElement = getElement('studentScoreTrend', null);
    
    // 设置学生基本信息
    if (nameElement) nameElement.textContent = studentName;
    if (idElement) idElement.textContent = studentId;
    
    // 清空加载中状态
    if (classElement) classElement.textContent = '加载中...';
    if (examCountElement) examCountElement.textContent = '加载中...';
    if (averageScoreElement) averageScoreElement.textContent = '加载中...';
    if (scoreTrendElement) scoreTrendElement.textContent = '加载中...';
    
    // 确定使用哪个表格头和表格体
    const tableHeadElement = getElement('studentScoresTableHead', 'studentDetailTableHead');
    const tableBodyElement = getElement('studentScoresTableBody', 'studentDetailTableBody');
    
    // 清空表格
    if (tableHeadElement) {
        tableHeadElement.innerHTML = '<tr><th>考试名称</th><th>考试日期</th><th>成绩</th><th>班级平均分</th><th>排名</th><th>与平均分差距</th></tr>';
    }
    if (tableBodyElement) {
        const colSpan = document.getElementById('studentScoresTableHead') ? 6 : 2;
        tableBodyElement.innerHTML = `<tr><td colspan="${colSpan}" class="text-center">加载中...</td></tr>`;
    }
    
    // 销毁现有图表
    if (charts['studentScoreTrendChart']) {
        charts['studentScoreTrendChart'].destroy();
        delete charts['studentScoreTrendChart'];
    }
    
    // 根据当前页面决定使用哪个对比图表ID
    const comparisonChartId = document.getElementById('studentSubjectsComparisonChart') ? 
        'studentSubjectsComparisonChart' : 'studentSubjectComparisonChart';
    
    if (charts[comparisonChartId]) {
        charts[comparisonChartId].destroy();
        delete charts[comparisonChartId];
    }
    
    // 获取模态框元素
    const modalElement = document.getElementById('studentAnalysisModal');
    
    // 确保移除之前的事件监听器
    modalElement.removeEventListener('hidden.bs.modal', handleModalHidden);
    
    // 添加模态框隐藏后的事件处理
    modalElement.addEventListener('hidden.bs.modal', handleModalHidden);
    
    // 显示模态框
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    // 获取学生所有考试数据
    fetchStudentExamData(studentId);
}

/**
 * 处理模态框隐藏后的事件
 */
function handleModalHidden() {
    // 移除模态框背景
    const modalBackdrops = document.querySelectorAll('.modal-backdrop');
    modalBackdrops.forEach(backdrop => {
        backdrop.remove();
    });
    
    // 移除body上的modal-open类
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
}

/**
 * 获取学生所有考试数据
 * @param {string|number} studentId 学生ID
 */
function fetchStudentExamData(studentId) {
    // 获取当前班级的所有考试
    fetch(`/api/exams?class_id=${currentClassId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok' && data.exams && data.exams.length > 0) {
                const examIds = data.exams.map(exam => exam.id);
                
                // 获取考试对比数据（包含所有学生的所有考试成绩）
                fetch('/api/exams/compare', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        exam_ids: examIds
                    })
                })
                .then(response => response.json())
                .then(compareData => {
                    if (compareData.status === 'ok') {
                        // 分析学生成绩数据
                        analyzeStudentData(studentId, compareData.results);
                    } else {
                        showNotification('error', compareData.message || '获取学生成绩数据失败');
                    }
                })
                .catch(error => {
                    console.error('获取考试对比数据失败:', error);
                    showNotification('error', '获取学生成绩数据失败: ' + error.message);
                });
            } else {
                document.getElementById('studentScoresTableBody').innerHTML = '<tr><td colspan="6" class="text-center">没有找到考试数据</td></tr>';
            }
        })
        .catch(error => {
            console.error('获取考试列表失败:', error);
            showNotification('error', '获取考试列表失败: ' + error.message);
        });
}

/**
 * 分析学生成绩数据
 * @param {string|number} studentId 学生ID
 * @param {Object} data 考试对比数据
 */
function analyzeStudentData(studentId, data) {
    // 找到指定学生的数据
    const student = data.students.find(s => s.student_id == studentId);
    
    // 获取元素引用
    const classElement = getElement('studentAnalysisClass', null);
    const examCountElement = getElement('studentExamCount', null);
    const averageScoreElement = getElement('studentAverageScore', null);
    const scoreTrendElement = getElement('studentScoreTrend', null);
    const tableBodyElement = getElement('studentScoresTableBody', 'studentDetailTableBody');
    
    if (!student) {
        if (tableBodyElement) {
            const colSpan = document.getElementById('studentScoresTableHead') ? 6 : 2;
            tableBodyElement.innerHTML = `<tr><td colspan="${colSpan}" class="text-center">未找到该学生的成绩数据</td></tr>`;
        }
        return;
    }
    
    // 设置学生基本信息
    if (classElement) classElement.textContent = student.class_name || '未知';
    
    // 提取学生的考试记录
    const examScores = {}; // 按考试ID存储学生的成绩
    const examDates = {}; // 存储考试日期
    const examNames = {}; // 存储考试名称
    const subjects = new Set(); // 存储所有学科
    
    // 处理考试信息
    data.exams.forEach(exam => {
        examDates[exam.id] = exam.date;
        examNames[exam.id] = exam.name;
        
        // 如果学生参加了这次考试，提取成绩
        if (student.scores[exam.id]) {
            examScores[exam.id] = student.scores[exam.id];
            
            // 收集学科
            Object.keys(student.scores[exam.id]).forEach(subject => {
                subjects.add(subject);
            });
        }
    });
    
    // 设置考试次数
    const examCount = Object.keys(examScores).length;
    if (examCountElement) examCountElement.textContent = examCount;
    
    // 如果没有考试记录
    if (examCount === 0) {
        if (tableBodyElement) {
            const colSpan = document.getElementById('studentScoresTableHead') ? 6 : 2;
            tableBodyElement.innerHTML = `<tr><td colspan="${colSpan}" class="text-center">未找到该学生的考试记录</td></tr>`;
        }
        if (averageScoreElement) averageScoreElement.textContent = '无数据';
        if (scoreTrendElement) scoreTrendElement.textContent = '无数据';
        return;
    }
    
    // 计算所有科目的平均分
    let totalScore = 0;
    let scoreCount = 0;
    
    Object.values(examScores).forEach(subjectScores => {
        Object.values(subjectScores).forEach(score => {
            if (typeof score === 'number' && !isNaN(score)) {
                totalScore += score;
                scoreCount++;
            }
        });
    });
    
    // 设置平均分
    const averageScore = scoreCount > 0 ? (totalScore / scoreCount).toFixed(1) : '无数据';
    if (averageScoreElement) averageScoreElement.textContent = averageScore;
    
    // 计算成绩趋势
    const scoreTrend = calculateScoreTrend(examScores, data.exams);
    if (scoreTrendElement) scoreTrendElement.textContent = scoreTrend.text;
    
    // 渲染成绩趋势图
    renderStudentScoreTrendChart(student, data.exams, subjects);
    
    // 渲染学科对比图 - 根据当前页面确定使用哪个函数
    if (document.getElementById('studentSubjectsComparisonChart')) {
        renderStudentSubjectsComparisonChart(student, data.exams, subjects);
    } else if (document.getElementById('studentSubjectComparisonChart')) {
        renderStudentSubjectComparisonChart(student, data.exams, subjects);
    }
    
    // 渲染成绩明细表格
    renderStudentDetailTable(student, data.exams, subjects);
}

/**
 * 计算学生成绩趋势
 * @param {Object} examScores 考试成绩
 * @param {Array} exams 考试数组
 * @returns {Object} 趋势信息
 */
function calculateScoreTrend(examScores, exams) {
    // 按照考试日期排序的考试ID
    const sortedExamIds = exams
        .map(exam => exam.id)
        .filter(examId => examScores[examId]); // 只保留学生参加了的考试
    
    if (sortedExamIds.length < 2) {
        return { trend: 'stable', text: '考试次数不足，无法分析趋势' };
    }
    
    // 计算每次考试的所有科目平均分
    const examAverages = sortedExamIds.map(examId => {
        const scores = Object.values(examScores[examId]).filter(score => typeof score === 'number' && !isNaN(score));
        return scores.length > 0 ? scores.reduce((sum, score) => sum + score, 0) / scores.length : 0;
    });
    
    // 计算最后一次和第一次的差值
    const firstAverage = examAverages[examAverages.length - 1]; // 修改：使用最新一次考试（数组末尾）
    const lastAverage = examAverages[0]; // 修改：使用最早一次考试（数组开头）
    const difference = firstAverage - lastAverage; // 修改：最新考试减去最早考试
    
    let trend, text;
    if (difference > 5) {
        trend = 'improving';
        text = `显著进步（↑ ${difference.toFixed(1)}分）`;
    } else if (difference > 0) {
        trend = 'slightly_improving';
        text = `略有进步（↑ ${difference.toFixed(1)}分）`;
    } else if (difference < -5) {
        trend = 'declining';
        text = `明显下降（↓ ${Math.abs(difference).toFixed(1)}分）`;
    } else if (difference < 0) {
        trend = 'slightly_declining';
        text = `略有下降（↓ ${Math.abs(difference).toFixed(1)}分）`;
    } else {
        trend = 'stable';
        text = '成绩稳定';
    }
    
    return { trend, text, difference };
}

/**
 * 渲染学生成绩趋势图
 * @param {Object} student 学生数据
 * @param {Array} exams 考试数组
 * @param {Set} subjects 学科集合
 */
function renderStudentScoreTrendChart(student, exams, subjects) {
    const canvasElement = document.getElementById('studentScoreTrendChart');
    
    // 如果找不到画布元素，返回
    if (!canvasElement) {
        console.error('找不到studentScoreTrendChart画布元素');
        return;
    }
    
    // 确保先销毁已有图表
    if (charts['studentScoreTrendChart']) {
        charts['studentScoreTrendChart'].destroy();
        delete charts['studentScoreTrendChart'];
    }
    
    const ctx = canvasElement.getContext('2d');
    
    // 按日期排序的考试
    const sortedExams = [...exams].sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // 获取科目列表
    const subjectArray = [...subjects];
    
    // 为每个科目创建一个数据集
    const datasets = [];
    subjectArray.forEach((subject, index) => {
        const data = [];
        sortedExams.forEach(exam => {
            if (student.scores[exam.id] && typeof student.scores[exam.id][subject] === 'number') {
                data.push(student.scores[exam.id][subject]);
            } else {
                data.push(null); // 无数据用null表示，Chart.js会处理为断点
            }
        });
        
        datasets.push({
            label: subject,
            data: data,
            borderColor: getChartColor(index, 1),
            backgroundColor: getChartColor(index, 0.1),
            borderWidth: 2,
            fill: false,
            tension: 0.1
        });
    });
    
    try {
        // 创建图表
        charts['studentScoreTrendChart'] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedExams.map(exam => exam.name),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        min: 0,
                        max: 100,
                        title: {
                            display: true,
                            text: '分数'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: '考试'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: '学生成绩趋势'
                    }
                }
            }
        });
    } catch (error) {
        console.error('创建成绩趋势图表失败:', error);
    }
}

/**
 * 渲染学生学科对比图
 * @param {Object} student 学生数据
 * @param {Array} exams 考试数组
 * @param {Set} subjects 学科集合
 */
function renderStudentSubjectsComparisonChart(student, exams, subjects) {
    const canvasElement = document.getElementById('studentSubjectsComparisonChart');
    
    // 如果找不到画布元素，退出
    if (!canvasElement) {
        console.error('找不到studentSubjectsComparisonChart画布元素');
        return;
    }
    
    // 确保先销毁已有图表
    if (charts['studentSubjectsComparisonChart']) {
        charts['studentSubjectsComparisonChart'].destroy();
        delete charts['studentSubjectsComparisonChart'];
    }
    
    const ctx = canvasElement.getContext('2d');
    
    // 准备最近两次考试的数据
    const sortedExams = [...exams].sort((a, b) => new Date(a.date) - new Date(b.date));
    const recentExams = sortedExams.slice(-2); // 获取最近的两次考试
    
    if (recentExams.length < 1) {
        return; // 考试数据不足，无法渲染
    }
    
    // 准备图表数据
    const subjectArray = [...subjects];
    const datasets = [];
    
    recentExams.forEach((exam, index) => {
        const scores = [];
        subjectArray.forEach(subject => {
            if (student.scores[exam.id] && typeof student.scores[exam.id][subject] === 'number') {
                scores.push(student.scores[exam.id][subject]);
            } else {
                scores.push(null); // 无数据
            }
        });
        
        datasets.push({
            label: exam.name,
            data: scores,
            backgroundColor: getChartColor(index, 0.2),
            borderColor: getChartColor(index, 1),
            borderWidth: 1
        });
    });
    
    try {
        // 创建图表
        charts['studentSubjectsComparisonChart'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: subjectArray,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: '各学科成绩对比'
                    }
                }
            }
        });
    } catch (error) {
        console.error('创建学科对比图表失败:', error);
    }
}

/**
 * 渲染学生详细成绩表格
 * @param {Object} student 学生数据
 * @param {Array} exams 考试数组
 * @param {Set} subjects 学科集合
 */
function renderStudentDetailTable(student, exams, subjects) {
    // 按日期排序的考试
    const sortedExams = [...exams].sort((a, b) => new Date(a.date) - new Date(b.date));
    const subjectArray = [...subjects];
    
    // 获取表格元素
    const tableHeadElement = getElement('studentScoresTableHead', 'studentDetailTableHead');
    const tableBodyElement = getElement('studentScoresTableBody', 'studentDetailTableBody');
    
    if (!tableHeadElement || !tableBodyElement) {
        console.error('未找到表格元素');
        return;
    }
    
    // 设置表头
    let headerRow = '<tr><th>考试名称</th><th>考试日期</th>';
    subjectArray.forEach(subject => {
        headerRow += `<th>${subject}</th>`;
    });
    headerRow += '<th>平均分</th></tr>';
    
    tableHeadElement.innerHTML = headerRow;
    
    // 生成表格行
    let tableRows = '';
    
    // 处理每次考试
    sortedExams.forEach(exam => {
        if (student.scores[exam.id]) {
            const examScores = student.scores[exam.id];
            let row = `<tr>
                <td>${exam.name}</td>
                <td>${exam.date || '未知'}</td>`;
            
            // 遍历每个科目的成绩
            let totalExamScore = 0;
            let validScoreCount = 0;
            
            subjectArray.forEach(subject => {
                const score = examScores[subject];
                if (typeof score === 'number' && !isNaN(score)) {
                    totalExamScore += score;
                    validScoreCount++;
                    
                    // 根据分数决定单元格样式
                    let cellClass = '';
                    if (score >= 90) cellClass = 'table-success';
                    else if (score >= 80) cellClass = 'table-info';
                    else if (score >= 60) cellClass = 'table-warning';
                    else cellClass = 'table-danger';
                    
                    row += `<td class="${cellClass}">${score}</td>`;
                } else {
                    row += '<td>-</td>';
                }
            });
            
            // 添加总分/平均分
            if (validScoreCount > 0) {
                const average = (totalExamScore / validScoreCount).toFixed(1);
                row += `<td>${average}</td>`;
            } else {
                row += '<td>-</td>';
            }
            
            row += '</tr>';
            tableRows += row;
        }
    });
    
    // 显示表格内容
    if (tableRows) {
        tableBodyElement.innerHTML = tableRows;
    } else {
        const colSpan = 2 + subjectArray.length + 1;
        tableBodyElement.innerHTML = `<tr><td colspan="${colSpan}" class="text-center">暂无考试记录</td></tr>`;
    }
}

/**
 * 渲染学生学科对比图(主页面版)
 * @param {Object} student 学生数据
 * @param {Array} exams 考试数组
 * @param {Set} subjects 学科集合
 */
function renderStudentSubjectComparisonChart(student, exams, subjects) {
    const canvasElement = document.getElementById('studentSubjectComparisonChart');
    
    // 如果找不到画布元素，退出
    if (!canvasElement) {
        console.error('无法找到studentSubjectComparisonChart画布元素');
        return;
    }
    
    // 确保先销毁已有图表
    if (charts['studentSubjectComparisonChart']) {
        charts['studentSubjectComparisonChart'].destroy();
        delete charts['studentSubjectComparisonChart'];
    }
    
    const ctx = canvasElement.getContext('2d');
    
    const subjectArray = Array.from(subjects);
    
    // 计算每个学科的平均分
    const subjectAverages = {};
    subjectArray.forEach(subject => {
        let sum = 0;
        let count = 0;
        
        exams.forEach(exam => {
            if (student.scores[exam.id] && typeof student.scores[exam.id][subject] === 'number') {
                sum += student.scores[exam.id][subject];
                count++;
            }
        });
        
        if (count > 0) {
            subjectAverages[subject] = sum / count;
        }
    });
    
    // 按平均分排序的学科列表
    const sortedSubjects = Object.keys(subjectAverages).sort((a, b) => subjectAverages[b] - subjectAverages[a]);
    
    // 准备图表数据
    const labels = sortedSubjects;
    const data = sortedSubjects.map(subject => subjectAverages[subject]);
    const backgroundColors = sortedSubjects.map((_, index) => getChartColor(index, 0.6));
    
    try {
        // 创建图表
        charts['studentSubjectComparisonChart'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '学科平均分',
                    data: data,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(color => color.replace('0.6', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        min: 0,
                        max: 100
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.raw.toFixed(1)}分`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('创建学科对比图表失败:', error);
    }
}

/**
 * 打开上传试卷模态框
 * @param {number} examId 考试ID
 * @param {string} examName 考试名称
 */
function openUploadPaperModal(examId, examName) {
    // 设置模态框数据
    document.getElementById('paperExamId').value = examId;
    document.getElementById('paperExamName').value = examName;
    
    // 清空文件输入
    document.getElementById('paperFileInput').value = '';
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('uploadPaperModal'));
    modal.show();
    
    // 添加提交按钮事件
    document.getElementById('uploadPaperSubmitBtn').onclick = uploadPaperFile;
}

/**
 * 上传试卷文件
 */
function uploadPaperFile() {
    const examId = document.getElementById('paperExamId').value;
    const fileInput = document.getElementById('paperFileInput');
    
    if (!examId) {
        showNotification('error', '缺少考试ID');
        return;
    }
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showNotification('error', '请选择PDF文件');
        return;
    }
    
    // 验证文件类型
    const file = fileInput.files[0];
    if (file.type !== 'application/pdf') {
        showNotification('error', '请上传PDF格式的文件');
        return;
    }
    
    // 显示上传中状态
    const submitBtn = document.getElementById('uploadPaperSubmitBtn');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 上传中...`;
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);
    
    // 发送请求
    fetch(`/api/exams/${examId}/paper`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // 恢复按钮状态
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
        
        if (data.status === 'ok') {
            showNotification('success', '试卷上传成功，正在进行分析');
            
            // 关闭上传模态框
            bootstrap.Modal.getInstance(document.getElementById('uploadPaperModal')).hide();
            
            // 打开分析结果模态框
            setTimeout(() => {
                openPaperAnalysisModal(examId, document.getElementById('paperExamName').value);
            }, 1000);
        } else {
            showNotification('error', data.message || '上传试卷失败');
        }
    })
    .catch(error => {
        console.error('上传试卷出错:', error);
        showNotification('error', '上传试卷失败: ' + error.message);
        
        // 恢复按钮状态
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    });
}

/**
 * 打开试卷分析模态框
 * @param {number} examId 考试ID
 * @param {string} examName 考试名称
 */
function openPaperAnalysisModal(examId, examName) {
    // 显示加载中状态
    document.getElementById('paperAnalysisLoading').style.display = 'block';
    document.getElementById('paperAnalysisContent').style.display = 'none';
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('paperAnalysisModal'));
    modal.show();
    
    // 设置考试名称
    document.getElementById('paperExamNameDisplay').textContent = examName;
    
    // 获取试卷分析数据
    fetchPaperAnalysisData(examId);
    
    // 添加下载报告按钮事件
    document.getElementById('downloadAnalysisReportBtn').onclick = function() {
        downloadAnalysisReport(examId);
    };
}

/**
 * 获取试卷分析数据
 * @param {number} examId 考试ID
 */
function fetchPaperAnalysisData(examId) {
    fetch(`/api/exams/${examId}/paper-analysis`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                // 渲染分析结果
                renderPaperAnalysis(data.analysis);
                
                // 隐藏加载中状态，显示内容
                document.getElementById('paperAnalysisLoading').style.display = 'none';
                document.getElementById('paperAnalysisContent').style.display = 'block';
            } else if (data.status === 'processing') {
                // 如果分析仍在处理中，显示提示并等待
                showNotification('info', '试卷分析正在进行中，请稍候...');
                
                // 5秒后再次查询
                setTimeout(() => {
                    fetchPaperAnalysisData(examId);
                }, 5000);
            } else {
                showNotification('error', data.message || '获取试卷分析数据失败');
                
                // 关闭模态框
                bootstrap.Modal.getInstance(document.getElementById('paperAnalysisModal')).hide();
            }
        })
        .catch(error => {
            console.error('获取试卷分析数据出错:', error);
            showNotification('error', '获取试卷分析数据失败: ' + error.message);
            
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('paperAnalysisModal')).hide();
        });
}

/**
 * 渲染试卷分析结果
 * @param {Object} analysis 分析数据
 */
function renderPaperAnalysis(analysis) {
    // 设置基本信息
    document.getElementById('paperSubjectDisplay').textContent = analysis.subject || '';
    document.getElementById('paperTotalScore').textContent = analysis.total_score || '100';
    
    // 渲染题目分析表格
    renderQuestionAnalysisTable(analysis.questions || []);
    
    // 渲染错题分布图表
    renderErrorDistributionChart(analysis.questions || []);
    
    // 渲染AI分析结果
    document.getElementById('aiOverallAnalysis').innerHTML = `<p>${analysis.ai_analysis?.overall || '暂无分析'}</p>`;
    
    // 渲染薄弱知识点
    if (analysis.ai_analysis?.weak_points && analysis.ai_analysis.weak_points.length > 0) {
        const weakPointsHtml = analysis.ai_analysis.weak_points.map(point => 
            `<div class="alert alert-warning">
                <strong>${point.title || '知识点'}</strong>: ${point.description || ''}
            </div>`
        ).join('');
        document.getElementById('aiWeakPointsAnalysis').innerHTML = weakPointsHtml;
    } else {
        document.getElementById('aiWeakPointsAnalysis').innerHTML = '<p>暂无薄弱知识点分析</p>';
    }
    
    // 渲染教学建议
    if (analysis.ai_analysis?.suggestions && analysis.ai_analysis.suggestions.length > 0) {
        const suggestionsHtml = analysis.ai_analysis.suggestions.map(suggestion => 
            `<div class="card mb-3">
                <div class="card-header">${suggestion.title || '建议'}</div>
                <div class="card-body">
                    <p>${suggestion.description || ''}</p>
                </div>
            </div>`
        ).join('');
        document.getElementById('aiTeachingSuggestions').innerHTML = suggestionsHtml;
    } else {
        document.getElementById('aiTeachingSuggestions').innerHTML = '<p>暂无教学建议</p>';
    }
}

/**
 * 渲染题目分析表格
 * @param {Array} questions 题目数据
 */
function renderQuestionAnalysisTable(questions) {
    const tableBody = document.getElementById('questionAnalysisTable');
    tableBody.innerHTML = '';
    
    if (questions.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center">暂无题目分析数据</td></tr>';
        return;
    }
    
    questions.forEach((question, index) => {
        const row = document.createElement('tr');
        
        // 根据错误率设置行样式
        if (question.error_rate > 0.7) {
            row.className = 'table-danger';
        } else if (question.error_rate > 0.4) {
            row.className = 'table-warning';
        }
        
        // 计算错误人数
        const errorCount = Math.round(question.error_rate * question.student_count) || 0;
        
        // 根据错误率确定难度等级
        let difficultyLevel;
        if (question.error_rate > 0.7) {
            difficultyLevel = '<span class="badge bg-danger">困难</span>';
        } else if (question.error_rate > 0.4) {
            difficultyLevel = '<span class="badge bg-warning text-dark">中等</span>';
        } else {
            difficultyLevel = '<span class="badge bg-success">简单</span>';
        }
        
        row.innerHTML = `
            <td>${question.number || (index + 1)}</td>
            <td>${question.type || '未知'}</td>
            <td>${question.score || '-'}</td>
            <td>${((1 - question.error_rate) * 100).toFixed(1)}%</td>
            <td>${errorCount} / ${question.student_count || '-'}</td>
            <td>${difficultyLevel}</td>
        `;
        
        tableBody.appendChild(row);
    });
}

/**
 * 渲染错题分布图表
 * @param {Array} questions 题目数据
 */
function renderErrorDistributionChart(questions) {
    // 销毁现有图表
    if (charts['errorDistributionChart']) {
        charts['errorDistributionChart'].destroy();
        delete charts['errorDistributionChart'];
    }
    
    // 如果没有数据，不渲染图表
    if (!questions || questions.length === 0) {
        return;
    }
    
    // 准备图表数据
    const labels = questions.map(q => q.number || `题${questions.indexOf(q) + 1}`);
    const errorRates = questions.map(q => (q.error_rate * 100).toFixed(1));
    const scores = questions.map(q => q.score || 0);
    
    // 创建图表
    const ctx = document.getElementById('errorDistributionChart').getContext('2d');
    charts['errorDistributionChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '错误率 (%)',
                    data: errorRates,
                    backgroundColor: 'rgba(255, 99, 132, 0.7)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1,
                    yAxisID: 'y'
                },
                {
                    label: '分值',
                    data: scores,
                    type: 'line',
                    fill: false,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '题号'
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: '错误率 (%)'
                    },
                    grid: {
                        drawOnChartArea: true
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '分值'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const datasetLabel = context.dataset.label;
                            const value = context.raw;
                            if (datasetLabel === '错误率 (%)') {
                                return `错误率: ${value}%`;
                            } else {
                                return `分值: ${value}`;
                            }
                        }
                    }
                }
            }
        }
    });
}

/**
 * 下载分析报告
 * @param {number} examId 考试ID
 */
function downloadAnalysisReport(examId) {
    window.location.href = `/api/exams/${examId}/paper-analysis-report`;
}

// 在DOM加载完成后添加事件监听
document.addEventListener('DOMContentLoaded', function() {
    // 原有的初始化代码...
    
    // 添加上传试卷按钮的事件监听器
    document.getElementById('uploadPaperSubmitBtn')?.addEventListener('click', uploadPaperFile);
    
    // 添加下载分析报告按钮事件
    document.getElementById('downloadAnalysisReportBtn')?.addEventListener('click', function() {
        const examId = document.getElementById('paperExamId').value;
        if (examId) {
            downloadAnalysisReport(examId);
        }
    });
}); 
