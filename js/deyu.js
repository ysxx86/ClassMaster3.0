// 德育维度模块

let currentSemester = ''; // 当前选择的学期
// 德育维度定义
const deyuDimensions = {
    'pinzhi': '品质',     // 30分
    'xuexi': '学习',      // 20分
    'jiankang': '健康',   // 20分
    'shenmei': '审美',    // 10分
    'shijian': '实践',    // 10分
    'shenghuo': '生活'    // 10分
};

// 各维度的最高分值
const dimensionMaxScores = {
    'pinzhi': 30,
    'xuexi': 20,
    'jiankang': 20,
    'shenmei': 10,
    'shijian': 10,
    'shenghuo': 10
};

document.addEventListener('DOMContentLoaded', function() {
    // 初始化学期选择和数据
    setupSemesterSelect();
    
    // 绑定搜索事件
    const searchInput = document.getElementById('searchStudent');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterGrades(this.value);
        });
    }
    
    // 绑定评分标准按钮事件
    const showRatingStandardsBtn = document.getElementById('showRatingStandardsBtn');
    if (showRatingStandardsBtn) {
        showRatingStandardsBtn.addEventListener('click', function() {
            const ratingStandardsModal = new bootstrap.Modal(document.getElementById('ratingStandardsModal'));
            ratingStandardsModal.show();
        });
    }
    
    // 绑定导出成绩按钮事件
    const exportGradesBtn = document.getElementById('exportGradesBtn');
    if (exportGradesBtn) {
        exportGradesBtn.addEventListener('click', function() {
            exportGrades();
        });
    }
    
    // 绑定"一键优"按钮事件
    const setAllExcellentBtn = document.getElementById('setAllExcellentBtn');
    if (setAllExcellentBtn) {
        setAllExcellentBtn.addEventListener('click', function() {
            setAllGradesExcellent();
        });
    }
    
    // 绑定清空所有成绩按钮事件
    const clearAllGradesBtn = document.getElementById('clearAllGradesBtn');
    if (clearAllGradesBtn) {
        clearAllGradesBtn.addEventListener('click', function() {
            clearAllGrades();
        });
    }
    
    // 初始化成绩导入功能
    initGradesImport();
    
    // 绑定成绩输入框变化事件 - 使用事件委托
    document.addEventListener('change', function(e) {
        if (e.target && e.target.classList.contains('grade-input')) {
            updateGrade(e.target);
            // 更新总分
            updateTotalScore(e.target);
        }
    });
});

// 设置学期选择器
function setupSemesterSelect() {
    const semesterSelect = document.getElementById('semesterSelect');
    const importSemesterSelect = document.getElementById('importSemester');
    
    // 自动计算当前学期
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1; // 月份从0开始，需要+1
    
    let academicYear, semester;
    
    // 3-8月为下学期（春季），9-2月为上学期（秋季）
    if (currentMonth >= 3 && currentMonth <= 8) {
        // 春季 - 下学期
        academicYear = `${currentYear-1}-${currentYear}`;
        semester = `下学期`;
    } else {
        // 秋季 - 上学期（包括9-12月和1-2月）
        if (currentMonth >= 9) {
            // 当年秋季
            academicYear = `${currentYear}-${currentYear+1}`;
        } else {
            // 次年初（1-2月）
            academicYear = `${currentYear-1}-${currentYear}`;
        }
        semester = `上学期`;
    }
    
    // 设置当前学期
    currentSemester = `${academicYear}学年${semester}`;
    
    if (semesterSelect) {
        // 设置学期显示文本
        semesterSelect.textContent = currentSemester;
    }
    
    if (importSemesterSelect) {
        // 设置导入模态框中的学期文本
        importSemesterSelect.value = currentSemester;
    }

    // 加载初始数据
    loadGrades();
}

// 加载成绩数据
function loadGrades() {
    const gradesTable = document.querySelector('.grades-table table tbody');
    if (!gradesTable) return;
    
    // 显示加载状态
    gradesTable.innerHTML = `
        <tr>
            <td colspan="9" class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-2">正在加载学生德育维度数据...</p>
            </td>
        </tr>
    `;
    
    // 首先获取当前用户信息以获取class_id
    console.log('获取当前用户信息...');
    fetch('/api/current-user')
        .then(response => response.json())
        .then(userData => {
            console.log('当前用户信息:', userData);
            
            // 确保用户数据有效
            if (!userData || userData.status !== 'ok' || !userData.user) {
                console.error('无法获取有效的用户信息');
                throw new Error('无法获取用户信息');
            }
            
            // 从用户数据中获取class_id
            const currentUser = userData.user;
            const classId = currentUser.class_id;
            
            console.log('当前用户班级ID:', classId);
            
            // 如果用户是班主任但没有class_id，显示提示信息
            if (!currentUser.is_admin && !classId) {
                console.warn('当前用户没有班级ID');
                gradesTable.innerHTML = `
                    <tr>
                        <td colspan="9" class="text-center py-5">
                            <div class="empty-state">
                                <i class='bx bx-error-circle'></i>
                                <h3>无法加载德育数据</h3>
                                <p>您尚未被分配班级，请联系管理员分配班级</p>
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }
            
            // 构建API URL，确保包含class_id参数
            const apiUrl = `/api/deyu?semester=${encodeURIComponent(currentSemester)}${classId ? `&class_id=${encodeURIComponent(classId)}` : ''}`;
            console.log('正在加载德育数据, URL:', apiUrl);
            
            // 从API获取德育数据
            return fetch(apiUrl);
        })
        .then(response => response.json())
        .then(data => {
            console.log('德育API返回数据:', data);
            if (data.status === 'ok' && data.deyu && data.deyu.length > 0) {
                console.log('成功获取德育数据, 学生数量:', data.deyu.length);
                renderGradesTable(data.deyu);
            } else {
                // 如果没有德育数据，尝试获取学生列表
                console.log('未找到德育数据，尝试获取学生列表');
                fetch('/api/current-user')
                    .then(response => response.json())
                    .then(userData => {
                        const currentUser = userData.user;
                        const classId = currentUser.class_id;
                        
                        // 构建学生API URL，确保包含class_id参数
                        const studentsApiUrl = `/api/students${classId ? `?class_id=${encodeURIComponent(classId)}` : ''}`;
                        console.log('请求学生列表:', studentsApiUrl);
                        
                        return fetch(studentsApiUrl);
                    })
                    .then(response => response.json())
                    .then(studentsData => {
                        if (studentsData.status === 'ok' && studentsData.students && studentsData.students.length > 0) {
                            console.log('成功获取学生列表，学生数量:', studentsData.students.length);
                            // 转换学生数据格式，创建空的德育维度数据
                            const emptyDeyuData = studentsData.students.map(student => ({
                                student_id: student.id,
                                name: student.name,
                                class: student.class,
                                pinzhi: 0,
                                xuexi: 0,
                                jiankang: 0,
                                shenmei: 0,
                                shijian: 0,
                                shenghuo: 0
                            }));
                            renderGradesTable(emptyDeyuData);
                        } else {
                            // 如果学生列表也为空
                            console.warn('未获取到学生列表数据');
                            gradesTable.innerHTML = `
                                <tr>
                                    <td colspan="9" class="text-center py-5">
                                        <div class="empty-state">
                                            <i class='bx bx-file-blank'></i>
                                            <h3>暂无学生数据</h3>
                                            <p>请先在学生管理中添加学生</p>
                                        </div>
                                    </td>
                                </tr>
                            `;
                        }
                    })
                    .catch(error => {
                        console.error('获取学生列表时出错:', error);
                        showNotification('获取学生列表失败', 'error');
                        gradesTable.innerHTML = `
                            <tr>
                                <td colspan="9" class="text-center py-5">
                                    <div class="empty-state">
                                        <i class='bx bx-error-circle'></i>
                                        <h3>加载失败</h3>
                                        <p>无法获取学生列表: ${error.message}</p>
                                    </div>
                                </td>
                            </tr>
                        `;
                    });
            }
        })
        .catch(error => {
            console.error('获取德育数据时出错:', error);
            gradesTable.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center py-5">
                        <div class="empty-state">
                            <i class='bx bx-error-circle'></i>
                            <h3>加载失败</h3>
                            <p>获取德育数据时发生错误: ${error.message}</p>
                        </div>
                    </td>
                </tr>
            `;
        });
}

// 渲染成绩表格
function renderGradesTable(grades) {
    console.log('渲染德育表格, 数据:', grades);
    const gradesTable = document.querySelector('.grades-table table tbody');
    if (!gradesTable) {
        console.error('找不到德育表格元素');
        return;
    }
    
    // 检查是否有数据
    if (!grades || grades.length === 0) {
        console.log('没有学生数据可显示');
        gradesTable.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-5">
                    <div class="empty-state">
                        <i class='bx bx-file-blank'></i>
                        <h3>暂无学生数据</h3>
                        <p>请先在学生管理中添加学生</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    console.log(`开始渲染德育表格，共有 ${grades.length} 名学生数据`);
    
    // 按班级和学号排序
    grades.sort((a, b) => {
        if (a.class !== b.class) {
            return a.class.localeCompare(b.class);
        }
        return parseInt(a.student_id) - parseInt(b.student_id);
    });
    
    // 清空表格
    gradesTable.innerHTML = '';
    
    // 分班级渲染学生成绩表
    let currentClass = null;
    const dimensionsToRender = ['pinzhi', 'xuexi', 'jiankang', 'shenmei', 'shijian', 'shenghuo'];
    
    // 添加调试信息 - 随机选择三个学生进行详细检查
    let debugSampleStudents = [];
    for (let i = 0; i < Math.min(3, grades.length); i++) {
        const randomIndex = Math.floor(Math.random() * grades.length);
        debugSampleStudents.push(grades[randomIndex]);
    }
    
    console.log('调试 - 样本学生德育维度数据:');
    debugSampleStudents.forEach(student => {
        console.log(`学生: ${student.student_id} - ${student.name}`);
        dimensionsToRender.forEach(dim => {
            console.log(`${dim}: ${student[dim]} (类型: ${typeof student[dim]}, 有效值: ${student[dim] !== null && student[dim] !== undefined})`);
        });
    });
    
    // 创建每个学生的行
    let studentsRendered = 0;
    let totalScoreSum = 0;
    let dimensionStats = {};
    
    // 初始化维度统计对象
    dimensionsToRender.forEach(dim => {
        dimensionStats[dim] = {
            sum: 0,
            count: 0,
            min: Number.MAX_VALUE,
            max: 0
        };
    });
    
    // 渲染每个学生成绩行
    grades.forEach(studentData => {
        studentsRendered++;
        
        // 创建班级标题行（如果需要）
        if (currentClass !== studentData.class) {
            currentClass = studentData.class;
            
            // 创建班级标题行
            const classRow = document.createElement('tr');
            classRow.className = 'table-light';
            classRow.innerHTML = `<td colspan="9"><strong>${currentClass || '未分配班级'}</strong></td>`;
            gradesTable.appendChild(classRow);
        }
        
        // 创建学生行
        const row = document.createElement('tr');
        row.setAttribute('data-student-id', studentData.student_id);
        
        // 添加学号和姓名单元格
        row.innerHTML = `
            <td>${studentData.student_id}</td>
            <td>${studentData.name}</td>
        `;
        
        // 维度总分
        let totalScore = 0;
        
        // 添加各维度分数单元格
        dimensionsToRender.forEach(dimension => {
            const cell = document.createElement('td');
            // 确保scoreValue是数字，处理null、undefined、NaN等情况
            let scoreValue = 0;
            if (studentData[dimension] !== undefined && studentData[dimension] !== null) {
                scoreValue = Number(studentData[dimension]);
                if (isNaN(scoreValue)) {
                    console.warn(`学生 ${studentData.student_id} 的 ${dimension} 值不是有效数字:`, studentData[dimension]);
                    scoreValue = 0;
                }
            }
            
            // 更新维度统计
            dimensionStats[dimension].sum += scoreValue;
            dimensionStats[dimension].count++;
            dimensionStats[dimension].min = Math.min(dimensionStats[dimension].min, scoreValue);
            dimensionStats[dimension].max = Math.max(dimensionStats[dimension].max, scoreValue);
            
            // 计算总分
            totalScore += scoreValue;
            
            // 创建分数输入框
            const input = document.createElement('input');
            input.type = 'number';
            input.className = 'form-control form-control-sm grade-input';
            input.setAttribute('data-student-id', studentData.student_id);
            input.setAttribute('data-dimension', dimension);
            input.value = scoreValue;
            
            // 设置输入框最小值和最大值
            input.min = 0;
            input.max = dimensionMaxScores[dimension];
            
            // 添加提示
            input.title = `${deyuDimensions[dimension]}(最高${dimensionMaxScores[dimension]}分)`;
            
            // 根据分数设置颜色
            const maxScore = dimensionMaxScores[dimension];
            const scorePercentage = scoreValue / maxScore;
            
            // 设置颜色
            if (scorePercentage >= 0.9) {
                input.style.backgroundColor = '#d4edda'; // 优秀 - 浅绿色
                input.style.color = '#155724';
                input.style.borderColor = '#c3e6cb';
            } else if (scorePercentage >= 0.75) {
                input.style.backgroundColor = '#d1ecf1'; // 良好 - 浅蓝色
                input.style.color = '#0c5460';
                input.style.borderColor = '#bee5eb';
            } else if (scorePercentage >= 0.6) {
                input.style.backgroundColor = '#fff3cd'; // 一般 - 浅黄色
                input.style.color = '#856404';
                input.style.borderColor = '#ffeeba';
            } else if (scoreValue > 0) {
                input.style.backgroundColor = '#f8d7da'; // 较差 - 浅红色
                input.style.color = '#721c24';
                input.style.borderColor = '#f5c6cb';
            }
            
            cell.appendChild(input);
            row.appendChild(cell);
        });
        
        // 添加总分单元格
        const totalCell = document.createElement('td');
        
        // 设置总分的颜色
        let totalScoreClass = '';
        let totalScoreStyle = '';
        if (totalScore >= 90) {
            totalScoreClass = 'bg-success text-white';
            totalScoreStyle = 'border-radius: 4px; padding: 2px 8px;';
        } else if (totalScore >= 75) {
            totalScoreClass = 'bg-info text-white';
            totalScoreStyle = 'border-radius: 4px; padding: 2px 8px;';
        } else if (totalScore >= 60) {
            totalScoreClass = 'bg-warning text-dark';
            totalScoreStyle = 'border-radius: 4px; padding: 2px 8px;';
        } else {
            totalScoreClass = 'bg-danger text-white';
            totalScoreStyle = 'border-radius: 4px; padding: 2px 8px;';
        }
        
        totalCell.innerHTML = `<span class="total-score ${totalScoreClass}" style="${totalScoreStyle}">${totalScore}</span> <span class="text-muted">/ 100</span>`;
        totalCell.className = 'fw-bold'; // 使总分加粗
        row.appendChild(totalCell);
        
        totalScoreSum += totalScore;
        
        gradesTable.appendChild(row);
    });
    
    // 输出渲染统计信息
    console.log(`渲染完成，总共渲染了 ${studentsRendered} 名学生的德育数据`);
    if (studentsRendered > 0) {
        console.log(`平均总分: ${(totalScoreSum / studentsRendered).toFixed(2)}`);
        
        console.log('各维度统计:');
        dimensionsToRender.forEach(dim => {
            const stat = dimensionStats[dim];
            if (stat.count > 0) {
                console.log(`${deyuDimensions[dim]}: 平均${(stat.sum / stat.count).toFixed(2)}分, 最低${stat.min}分, 最高${stat.max}分`);
            }
        });
    }
}

// 更新总分并添加颜色
function updateTotalScoreWithColor(inputElement) {
    const row = inputElement.closest('tr');
    const totalScoreSpan = row.querySelector('.total-score');
    
    let total = 0;
    row.querySelectorAll('.grade-input').forEach(input => {
        total += parseInt(input.value) || 0;
    });
    
    totalScoreSpan.textContent = total;
    
    // 设置总分的颜色
    totalScoreSpan.className = 'total-score'; // 重置类名
    
    // 添加颜色类和样式
    let totalScoreClass = '';
    if (total >= 90) {
        totalScoreClass = 'bg-success text-white';
    } else if (total >= 75) {
        totalScoreClass = 'bg-info text-white';
    } else if (total >= 60) {
        totalScoreClass = 'bg-warning text-dark';
    } else {
        totalScoreClass = 'bg-danger text-white';
    }
    
    totalScoreSpan.className = `total-score ${totalScoreClass}`;
    totalScoreSpan.style.borderRadius = '4px';
    totalScoreSpan.style.padding = '2px 8px';
}

// 更新总分
function updateTotalScore(inputElement) {
    updateTotalScoreWithColor(inputElement);
}

// 过滤成绩表格
function filterGrades(keyword) {
    if (!keyword) {
        // 如果没有关键字，显示所有行
        document.querySelectorAll('.grades-table table tbody tr').forEach(row => {
            row.style.display = '';
        });
        return;
    }
    
    keyword = keyword.toLowerCase();
    
    // 过滤学生行和班级行
    let lastVisibleClass = null;
    const classRows = {};
    const studentRows = [];
    
    // 收集所有班级行和学生行
    document.querySelectorAll('.grades-table table tbody tr').forEach(row => {
        if (row.classList.contains('table-light')) {
            // 班级行
            const className = row.textContent.trim();
            classRows[className] = row;
            row.style.display = 'none'; // 默认隐藏所有班级行
        } else if (row.hasAttribute('data-student-id')) {
            // 学生行
            studentRows.push(row);
            
            const studentId = row.getAttribute('data-student-id');
            const studentName = row.querySelector('td:nth-child(2)').textContent;
            
            // 检查是否匹配搜索关键字
            if (studentId.toLowerCase().includes(keyword) || 
                studentName.toLowerCase().includes(keyword)) {
                row.style.display = '';
                
                // 找到这个学生所属的班级行
                const className = row.previousElementSibling.textContent.trim();
                if (classRows[className]) {
                    classRows[className].style.display = '';
                }
            } else {
                row.style.display = 'none';
            }
        } else {
            // 其他行（如空状态行）
            row.style.display = keyword ? 'none' : '';
        }
    });
}

// 更新学生德育数据
function updateGrade(inputElement) {
    const studentId = inputElement.getAttribute('data-student-id');
    const dimension = inputElement.getAttribute('data-dimension');
    const value = inputElement.value;
    
    // 验证输入值在允许的范围内
    const maxScore = dimensionMaxScores[dimension];
    if (value < 0 || value > maxScore) {
        showNotification(`${deyuDimensions[dimension]}分数必须在0-${maxScore}之间`, 'warning');
        inputElement.value = Math.min(Math.max(0, value), maxScore);
        return;
    }
    
    // 显示保存中状态
    const originalBg = inputElement.style.backgroundColor;
    const originalColor = inputElement.style.color;
    const originalBorder = inputElement.style.borderColor;
    inputElement.style.backgroundColor = '#e6f7ff'; // 浅蓝色表示正在保存
    inputElement.style.color = '#0c5460';
    
    // 首先获取当前用户的class_id
    fetch('/api/current-user')
        .then(response => response.json())
        .then(userData => {
            // 确保用户数据有效
            if (!userData || userData.status !== 'ok' || !userData.user) {
                console.error('无法获取有效的用户信息');
                throw new Error('无法获取用户信息');
            }
            
            // 从用户数据中获取class_id
            const currentUser = userData.user;
            const classId = currentUser.class_id;
            
            console.log(`保存学生 ${studentId} 的德育维度数据，班级ID: ${classId}`);
            
            // 获取当前学生行中所有维度的值
            const row = inputElement.closest('tr');
            const gradeData = {
                semester: currentSemester,
                class_id: classId // 添加班级ID参数
            };
            
            // 获取所有维度的当前值
            const dimensionsToSave = ['pinzhi', 'xuexi', 'jiankang', 'shenmei', 'shijian', 'shenghuo'];
            dimensionsToSave.forEach(dim => {
                const input = row.querySelector(`input[data-dimension="${dim}"]`);
                if (input) {
                    gradeData[dim] = parseInt(input.value) || 0;
                }
            });
            
            // 更新当前正在修改的维度值
            gradeData[dimension] = parseInt(value) || 0;
            
            console.log(`保存学生 ${studentId} 的 ${dimension} 德育维度分数: ${value}`);
            console.log('发送数据:', gradeData);
            
            // 发送到服务器
            return fetch(`/api/deyu/${studentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(gradeData)
            });
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP错误! 状态: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'ok') {
                showNotification(`成功保存 ${studentId} 的 ${deyuDimensions[dimension]} 分数`, 'success');
                
                // 根据分数设置新的背景色
                const scoreValue = parseInt(value) || 0;
                const scorePercentage = scoreValue / maxScore;
                
                if (scorePercentage >= 0.9) {
                    inputElement.style.backgroundColor = '#d4edda'; // 优秀 - 浅绿色
                    inputElement.style.color = '#155724';
                    inputElement.style.borderColor = '#c3e6cb';
                } else if (scorePercentage >= 0.75) {
                    inputElement.style.backgroundColor = '#d1ecf1'; // 良好 - 浅蓝色
                    inputElement.style.color = '#0c5460';
                    inputElement.style.borderColor = '#bee5eb';
                } else if (scorePercentage >= 0.6) {
                    inputElement.style.backgroundColor = '#fff3cd'; // 一般 - 浅黄色
                    inputElement.style.color = '#856404';
                    inputElement.style.borderColor = '#ffeeba';
                } else if (scoreValue > 0) {
                    inputElement.style.backgroundColor = '#f8d7da'; // 较差 - 浅红色
                    inputElement.style.color = '#721c24';
                    inputElement.style.borderColor = '#f5c6cb';
                } else {
                    // 恢复默认样式
                    inputElement.style.backgroundColor = '';
                    inputElement.style.color = '';
                    inputElement.style.borderColor = '';
                }
                
                // 更新总分显示及其颜色
                updateTotalScoreWithColor(inputElement);
            } else {
                inputElement.style.backgroundColor = '#f8d7da'; // 红色表示保存失败
                inputElement.style.color = '#721c24';
                showNotification(data.message || '保存德育维度分数失败', 'error');
                setTimeout(() => {
                    inputElement.style.backgroundColor = originalBg;
                    inputElement.style.color = originalColor;
                    inputElement.style.borderColor = originalBorder;
                }, 1000);
            }
        })
        .catch(error => {
            console.error('保存德育维度分数时出错:', error);
            inputElement.style.backgroundColor = '#f8d7da'; // 红色表示保存失败
            inputElement.style.color = '#721c24';
            showNotification('保存德育维度分数时发生错误: ' + error.message, 'error');
            setTimeout(() => {
                inputElement.style.backgroundColor = originalBg;
                inputElement.style.color = originalColor;
                inputElement.style.borderColor = originalBorder;
            }, 1000);
        });
}

// 初始化德育数据导入功能
function initGradesImport() {
    const fileInput = document.getElementById('gradeFile');
    const importArea = document.querySelector('.import-area');
    const selectedFileNameDiv = document.getElementById('selectedFileName');
    const downloadTemplateBtn = document.getElementById('downloadTemplateBtn');
    const confirmImportBtn = document.getElementById('confirmImportGrades');
    
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                selectedFileNameDiv.textContent = `已选择: ${file.name}`;
                
                // 创建FormData对象并添加文件
                const formData = new FormData();
                formData.append('file', file);
                formData.append('semester', currentSemester);
                
                // 预览导入数据
                previewGradesImport(formData);
            }
        });
    }
    
    // 拖放功能
    if (importArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            importArea.addEventListener(eventName, function(e) {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            importArea.addEventListener(eventName, function() {
                importArea.classList.add('drag-over');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            importArea.addEventListener(eventName, function() {
                importArea.classList.remove('drag-over');
            }, false);
        });
        
        importArea.addEventListener('drop', function(e) {
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                const file = e.dataTransfer.files[0];
                selectedFileNameDiv.textContent = `已选择: ${file.name}`;
                
                // 创建FormData对象并添加文件
                const formData = new FormData();
                formData.append('file', file);
                formData.append('semester', currentSemester);
                
                // 预览导入数据
                previewGradesImport(formData);
            }
        }, false);
    }
    
    // 下载模板按钮
    if (downloadTemplateBtn) {
        downloadTemplateBtn.addEventListener('click', function() {
            window.location.href = `/api/deyu/template`;
        });
    }
    
    // 确认导入按钮
    if (confirmImportBtn) {
        confirmImportBtn.addEventListener('click', function() {
            const importFilePath = document.getElementById('importFilePath').value;
            if (importFilePath) {
                // 发送确认导入请求
                fetch('/api/deyu/confirm-import', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        file_path: importFilePath,
                        semester: currentSemester
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok') {
                        showNotification('德育数据导入成功!', 'success');
                        // 关闭模态框并刷新数据
                        const modal = bootstrap.Modal.getInstance(document.getElementById('importGradesModal'));
                        modal.hide();
                        resetImportModal();
                        loadGrades(); // 重新加载成绩数据
                    } else {
                        showNotification(data.message || '导入失败', 'error');
                    }
                })
                .catch(error => {
                    console.error('确认导入时出错:', error);
                    showNotification('导入过程中发生错误', 'error');
                });
            } else {
                showNotification('没有可导入的文件', 'warning');
            }
        });
    }
}

// 预览德育数据导入
function previewGradesImport(formData) {
    const previewContent = document.getElementById('previewContent');
    const confirmImportBtn = document.getElementById('confirmImportGrades');
    
    if (previewContent) {
        // 显示加载中状态
        previewContent.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-2">正在解析导入文件...</p>
            </div>
        `;
        
        // 发送预览请求
        fetch('/api/deyu/preview-import', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                // 保存导入文件路径
                document.getElementById('importFilePath').value = data.file_path;
                
                // 生成预览表格
                let previewHTML = '<h5>预览数据</h5>';
                if (data.preview && data.preview.length > 0) {
                    previewHTML += `
                        <div class="table-responsive">
                            <table class="table table-sm table-bordered">
                                <thead>
                                    <tr>
                                        <th>学号</th>
                                        <th>姓名</th>
                                        <th>班级</th>
                                        <th>维度</th>
                                        <th>分数</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    data.preview.forEach(row => {
                        previewHTML += `
                            <tr>
                                <td>${row.student_id || ''}</td>
                                <td>${row.student_name || ''}</td>
                                <td>${row.class || ''}</td>
                                <td>${row.dimension ? (deyuDimensions[row.dimension] || row.dimension) : ''}</td>
                                <td>${row.score || ''}</td>
                            </tr>
                        `;
                    });
                    
                    previewHTML += `
                                </tbody>
                            </table>
                        </div>
                        <p>预览显示前 ${data.preview.length} 条记录，总共有 ${data.total_rows || 'unknown'} 条记录将被导入。</p>
                    `;
                    
                    // 启用确认导入按钮
                    if (confirmImportBtn) {
                        confirmImportBtn.disabled = false;
                    }
                } else {
                    previewHTML += '<div class="alert alert-warning">没有找到可导入的数据</div>';
                    // 禁用确认导入按钮
                    if (confirmImportBtn) {
                        confirmImportBtn.disabled = true;
                    }
                }
                
                previewContent.innerHTML = previewHTML;
            } else {
                previewContent.innerHTML = `<div class="alert alert-danger">${data.message || '无法预览导入数据'}</div>`;
                // 禁用确认导入按钮
                if (confirmImportBtn) {
                    confirmImportBtn.disabled = true;
                }
            }
        })
        .catch(error => {
            console.error('预览导入时出错:', error);
            previewContent.innerHTML = `<div class="alert alert-danger">预览过程中发生错误</div>`;
            // 禁用确认导入按钮
            if (confirmImportBtn) {
                confirmImportBtn.disabled = true;
            }
        });
    }
}

// 重置导入模态框
function resetImportModal() {
    const fileInput = document.getElementById('gradeFile');
    const selectedFileNameDiv = document.getElementById('selectedFileName');
    const previewContent = document.getElementById('previewContent');
    const importFilePath = document.getElementById('importFilePath');
    const confirmImportBtn = document.getElementById('confirmImportGrades');
    
    if (fileInput) fileInput.value = '';
    if (selectedFileNameDiv) selectedFileNameDiv.textContent = '';
    if (previewContent) previewContent.innerHTML = '';
    if (importFilePath) importFilePath.value = '';
    if (confirmImportBtn) confirmImportBtn.disabled = true;
}

// 导出德育数据
function exportGrades() {
    window.location.href = `/api/deyu/export?semester=${encodeURIComponent(currentSemester)}`;
}

// 一键设置所有成绩为优
function setAllGradesExcellent() {
    if (!confirm('确定要将当前学期所有学生的所有维度分数都设置为最高分吗？此操作不可撤销。')) {
        return;
    }
    
    // 添加遮罩层和加载提示
    const tableBody = document.querySelector('.grades-table table tbody');
    if (!tableBody) return;
    
    const loadingRow = document.createElement('div');
    loadingRow.id = 'loadingOverlay';
    loadingRow.innerHTML = `
        <td colspan="9" class="text-center py-5" style="background: rgba(255,255,255,0.8); position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 100;">
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">处理中...</span>
                </div>
                <p class="mt-2">正在处理所有学生的德育维度分数...</p>
            </div>
        </td>
    `;
    document.querySelector('.grades-table').appendChild(loadingRow);
    
    // 创建要发送的更新数据
    const dimensionsToUpdate = ['pinzhi', 'xuexi', 'jiankang', 'shenmei', 'shijian', 'shenghuo'];
    
    // 获取所有学生ID
    const studentIds = [];
    document.querySelectorAll('.grades-table tr[data-student-id]').forEach(row => {
        const studentId = row.getAttribute('data-student-id');
        if (studentId && !studentIds.includes(studentId)) {
            studentIds.push(studentId);
        }
    });
    
    // 如果没有学生，不执行操作
    if (studentIds.length === 0) {
        document.getElementById('loadingOverlay').remove();
        showNotification('没有找到学生数据', 'warning');
        return;
    }
    
    // 为每个学生逐个设置维度最高分，不一次性批量操作以确保更新成功
    let successCount = 0;
    let errorCount = 0;
    let processedCount = 0;
    
    const promises = studentIds.map(studentId => {
        // 创建包含所有维度最高分的数据对象
        const gradeData = {
            semester: currentSemester
        };
        
        // 为每个维度设置最高分
        dimensionsToUpdate.forEach(dimension => {
            gradeData[dimension] = dimensionMaxScores[dimension];
        });
        
        // 发送更新请求
        return fetch(`/api/deyu/${studentId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(gradeData)
        })
        .then(response => response.json())
        .then(data => {
            processedCount++;
            if (data.status === 'ok') {
                successCount++;
            } else {
                errorCount++;
                console.error(`更新学生 ${studentId} 的德育维度分数失败:`, data.message);
            }
        })
        .catch(error => {
            processedCount++;
            errorCount++;
            console.error(`更新学生 ${studentId} 的德育维度分数时出错:`, error);
        });
    });
    
    // 等待所有请求完成
    Promise.all(promises)
        .then(() => {
            // 移除加载遮罩
            document.getElementById('loadingOverlay').remove();
            
            if (errorCount === 0) {
                showNotification(`已成功将所有 ${successCount} 名学生的德育维度分数设置为最高分`, 'success');
                
                // 更新页面上的所有成绩输入框
                document.querySelectorAll('.grades-table input.grade-input').forEach(input => {
                    const dimension = input.getAttribute('data-dimension');
                    if (dimension && dimensionMaxScores[dimension]) {
                        input.value = dimensionMaxScores[dimension];
                    }
                });
                
                // 更新所有总分
                document.querySelectorAll('.grades-table tr[data-student-id]').forEach(row => {
                    const totalScoreSpan = row.querySelector('.total-score');
                    if (totalScoreSpan) {
                        totalScoreSpan.textContent = '100';
                    }
                });
            } else {
                showNotification(`操作完成。成功: ${successCount}, 失败: ${errorCount}`, 
                    errorCount > successCount ? 'error' : 'warning');
                // 重新加载数据，确保显示最新状态
                loadGrades();
            }
        })
        .catch(error => {
            console.error('设置德育维度分数时出错:', error);
            document.getElementById('loadingOverlay').remove();
            showNotification('设置德育维度分数时发生错误', 'error');
        });
}

// 清空所有德育数据
function clearAllGrades() {
    if (!confirm('确定要清空当前学期所有学生的所有维度分数吗？此操作不可撤销。')) {
        return;
    }
    
    const gradesTable = document.querySelector('.grades-table table tbody');
    if (!gradesTable) return;
    
    // 显示加载状态
    const loadingRow = document.createElement('tr');
    loadingRow.id = 'loadingOverlay';
    loadingRow.innerHTML = `
        <td colspan="9" class="text-center py-5" style="background: rgba(255,255,255,0.8); position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 100;">
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">处理中...</span>
                </div>
                <p class="mt-2">正在清空所有评级，请稍候...</p>
            </div>
        </td>
    `;
    gradesTable.appendChild(loadingRow);
    
    // 批量清空请求
    fetch('/api/deyu/clear-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            semester: currentSemester
        })
    })
    .then(response => response.json())
    .then(data => {
        // 移除加载状态
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
        
        if (data.status === 'ok') {
            showNotification(`已成功清空所有学生的所有维度分数`, 'success');
            
            // 更新页面上的所有成绩输入框
            document.querySelectorAll('.grades-table input.grade-input').forEach(input => {
                input.value = '';
                input.className = 'form-control form-control-sm grade-input';
            });
        } else {
            showNotification(data.message || '清空评级失败', 'error');
        }
    })
    .catch(error => {
        console.error('清空评级时出错:', error);
        
        // 移除加载状态
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
        
        showNotification('清空评级时发生错误', 'error');
    });
}

// 显示通知
function showNotification(message, type = 'info') {
    // 图标映射
    const icons = {
        'success': 'bx-check-circle',
        'error': 'bx-error',
        'warning': 'bx-error-circle',
        'info': 'bx-info-circle'
    };
    
    // 创建通知容器（如果不存在）
    let notificationContainer = document.querySelector('.notification-container');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.className = 'notification-container';
        document.body.appendChild(notificationContainer);
    }
    
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class='bx ${icons[type] || icons.info} notification-icon'></i>
        <div class="notification-content">
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close">&times;</button>
    `;
    
    // 将通知添加到容器
    notificationContainer.appendChild(notification);
    
    // 绑定关闭按钮事件
    const closeButton = notification.querySelector('.notification-close');
    if (closeButton) {
        closeButton.addEventListener('click', function() {
            notification.classList.add('notification-hiding');
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
    }
    
    // 自动关闭通知
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.add('notification-hiding');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, 5000);
} 