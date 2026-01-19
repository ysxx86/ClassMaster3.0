// 成绩管理模块

let currentSemester = ''; // 当前选择的学期
// 使用data.js中已定义的subjects变量 - 确保data.js已在页面中引入
const subjectNames = {
    'daof': '道法',
    'yuwen': '语文',
    'shuxue': '数学',
    'yingyu': '英语',
    'laodong': '劳动',
    'tiyu': '体育',
    'yinyue': '音乐',
    'meishu': '美术',
    'kexue': '科学',
    'zonghe': '综合',
    'xinxi': '信息',
    'shufa': '书法',
    'xinli': '心理'
};

// 记录数据检查的最后时间戳
let lastDataCheckTimestamp = Date.now();

// 为其他页面提供的刷新方法
window.refreshGradesList = function() {
    console.log('手动触发成绩列表刷新...');
    loadGrades();
};

// 定期检查学生数据是否有变更（例如：学生被删除）
function startDataChangeChecking() {
    // 每5秒检查一次
    setInterval(checkStudentDataChanged, 5000);
}

// 检查学生数据是否发生变化
function checkStudentDataChanged() {
    // 尝试从localStorage获取数据变更时间戳
    const storedTimestamp = localStorage.getItem('studentDataChangeTimestamp');
    
    if (storedTimestamp && parseInt(storedTimestamp) > lastDataCheckTimestamp) {
        console.log('检测到学生数据变更，刷新成绩列表...');
        lastDataCheckTimestamp = parseInt(storedTimestamp);
        loadGrades();  // 重新加载成绩列表
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // 获取用户权限信息
    fetchUserPermissions().then(() => {
        // 初始化学期选择和数据
        setupSemesterSelect();
        
        // 绑定搜索事件
        const searchInput = document.getElementById('searchStudent');
        if (searchInput) {
            searchInput.addEventListener('input', function() {
                filterGrades(this.value);
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
        
        // 绑定成绩选择框变化事件 - 使用事件委托
        document.addEventListener('change', function(e) {
            if (e.target && e.target.classList.contains('grade-select')) {
                updateGrade(e.target);
            }
        });
        
        // 初始化表格布局
        adjustTableLayout();
        
        // 启动数据变更检查
        startDataChangeChecking();
        
        // ⭐ 监听教师信息更新事件（实时更新）
        window.addEventListener('teacherInfoUpdated', function(e) {
            console.log('✅ 检测到教师信息更新，立即重新加载数据...', e.detail);
            
            // 显示提示
            showNotification('任教信息已更新，正在刷新数据...', 'info');
            
            // 1. 重新获取用户权限（从服务器）
            fetchUserPermissions().then(() => {
                console.log('✅ 权限已更新');
                
                // 2. 重新加载成绩数据（从数据库）
                console.log('✅ 开始重新加载成绩列表...');
                loadGrades();
                
                // 3. 显示成功提示
                setTimeout(() => {
                    showNotification('数据已更新！', 'success');
                }, 500);
            }).catch(error => {
                console.error('❌ 更新权限失败:', error);
                showNotification('更新失败，请刷新页面', 'error');
            });
        });
        
        // ⭐ 监听localStorage变化（跨标签页/iframe通信）
        window.addEventListener('storage', function(e) {
            if (e.key === 'teacherInfoUpdateTimestamp') {
                console.log('✅ 检测到其他页面更新了教师信息（storage事件）');
                
                // 重新获取权限并加载数据
                fetchUserPermissions().then(() => {
                    loadGrades();
                    showNotification('数据已同步更新！', 'success');
                });
            }
        });
        
        // ⭐ 定期检查localStorage（用于同一标签页内的iframe通信）
        let lastTeacherInfoUpdate = localStorage.getItem('teacherInfoUpdateTimestamp') || '0';
        
        setInterval(() => {
            const currentUpdate = localStorage.getItem('teacherInfoUpdateTimestamp') || '0';
            
            if (currentUpdate !== lastTeacherInfoUpdate && currentUpdate !== '0') {
                console.log('✅ 检测到教师信息更新（轮询检查）');
                lastTeacherInfoUpdate = currentUpdate;
                
                // 重新获取权限并加载数据
                fetchUserPermissions().then(() => {
                    console.log('✅ 重新加载成绩数据...');
                    loadGrades();
                    showNotification('数据已自动更新！', 'success');
                });
            }
        }, 2000); // 每2秒检查一次
        
        // 设置数据变更事件监听
        window.addEventListener('storage', function(e) {
            if (e.key === 'studentDataChangeTimestamp') {
                console.log('从localStorage事件检测到学生数据变更');
                loadGrades();  // 重新加载成绩列表
            }
        });
    });
});

// 存储用户权限信息
let userPermissions = null;
let allowedSubjects = null;  // 用户可以查看的学科列表

// 获取用户权限信息
async function fetchUserPermissions() {
    try {
        const response = await fetch('/api/current-user');
        const data = await response.json();
        if (data.status === 'ok' && data.permissions) {
            userPermissions = data.permissions;
            console.log('用户权限信息:', userPermissions);
        }
    } catch (error) {
        console.error('获取用户权限失败:', error);
    }
}

// 检查是否可以编辑某个学科（需要传入班级ID）
function canEditSubject(subjectFieldName, classId) {
    if (!userPermissions) {
        return false;
    }
    
    // 超级管理员可以编辑所有学科
    if (userPermissions.is_admin) {
        return true;
    }
    
    // 获取学科显示名称
    const subjectDisplayName = subjectNames[subjectFieldName];
    if (!subjectDisplayName) {
        return false;
    }
    
    // 正班主任可以编辑自己班级的所有学科
    if (userPermissions.role === '正班主任' && userPermissions.class_id == classId) {
        return true;
    }
    
    // 其他角色：检查 teaching_map 中是否有该班级的该学科
    const teachingMap = userPermissions.teaching_map || {};
    const classSubjects = teachingMap[String(classId)] || [];
    return classSubjects.includes(subjectDisplayName);
}

// 设置学期选择器
async function setupSemesterSelect() {
    const semesterSelect = document.getElementById('semesterSelect');
    const importSemesterSelect = document.getElementById('importSemester');
    
    try {
        // ⭐ 从数据库获取学年和学期设置
        const response = await fetch('/api/system-settings');
        const data = await response.json();
        
        let academicYear, semester, semesterText;
        
        if (data.status === 'ok' && data.settings) {
            // 从数据库获取
            academicYear = data.settings.school_year || '2025-2026';
            const semesterNum = data.settings.semester || '1';
            
            // 转换为文字
            semesterText = semesterNum === '1' ? '第一学期' : '第二学期';
            semester = semesterText;
            
            console.log('从数据库获取学期设置:', { academicYear, semester });
        } else {
            // 如果API失败，使用默认值
            console.warn('无法从数据库获取学期设置，使用默认值');
            academicYear = '2025-2026';
            semester = '第一学期';
        }
        
        // 设置当前学期
        currentSemester = `${academicYear}学年${semester}`;
        
        // 更新显示
        if (semesterSelect) {
            semesterSelect.textContent = currentSemester;
        }
        
        if (importSemesterSelect) {
            importSemesterSelect.value = currentSemester;
        }
        
        console.log('当前学期:', currentSemester);
        
        // 加载成绩数据
        loadGrades();
    } catch (error) {
        console.error('获取学期设置失败:', error);
        
        // 使用默认值
        currentSemester = '2025-2026学年第一学期';
        
        if (semesterSelect) {
            semesterSelect.textContent = currentSemester;
        }
        
        if (importSemesterSelect) {
            importSemesterSelect.value = currentSemester;
        }
        
        // 仍然尝试加载成绩
        loadGrades();
    }
}

// 加载成绩数据
function loadGrades() {
    const gradesTable = document.querySelector('.grades-table table tbody');
    if (!gradesTable) return;
    
    // 显示加载状态
    gradesTable.innerHTML = `
        <tr>
            <td colspan="15" class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-2">正在加载学生成绩数据...</p>
            </td>
        </tr>
    `;
    
    // 从API获取数据
    console.log('正在加载学期成绩:', currentSemester);
    fetch(`/api/grades?semester=${encodeURIComponent(currentSemester)}`)
        .then(response => response.json())
        .then(data => {
            console.log('成绩API返回数据:', data);
            if (data.status === 'ok') {
                console.log('成功获取成绩数据, 学生数量:', data.grades ? data.grades.length : 0);
                
                // ⭐ 保存用户权限信息和允许查看的学科列表
                if (data.user_permissions) {
                    userPermissions = data.user_permissions;
                    console.log('用户权限信息:', userPermissions);
                }
                
                // ⭐ 保存允许查看的学科列表
                if (data.allowed_subjects) {
                    allowedSubjects = data.allowed_subjects;
                    console.log('允许查看的学科:', allowedSubjects);
                }
                
                // 检查是否有空班级
                if (data.empty_classes && data.empty_classes.length > 0) {
                    console.log('空班级:', data.empty_classes);
                    // 显示空班级提示
                    const emptyClassNames = data.empty_classes.map(c => c.class_name).join('、');
                    showNotification(`提示：${emptyClassNames} 暂无学生数据`, 'info');
                }
                
                renderGradesTable(data.grades || []);
            } else {
                showNotification(data.message || '加载成绩失败', 'error');
                gradesTable.innerHTML = `
                    <tr>
                        <td colspan="15" class="text-center py-5">
                            <div class="empty-state">
                                <i class='bx bx-error-circle'></i>
                                <h3>加载失败</h3>
                                <p>${data.message || '无法加载成绩数据'}</p>
                            </div>
                        </td>
                    </tr>
                `;
            }
        })
        .catch(error => {
            console.error('获取成绩数据时出错:', error);
            gradesTable.innerHTML = `
                <tr>
                    <td colspan="15" class="text-center py-5">
                        <div class="empty-state">
                            <i class='bx bx-error-circle'></i>
                            <h3>加载失败</h3>
                            <p>获取成绩数据时发生错误</p>
                        </div>
                    </td>
                </tr>
            `;
        });
}

// 渲染成绩表格
function renderGradesTable(grades) {
    console.log('渲染成绩表格, 数据:', grades);
    const gradesTable = document.querySelector('.grades-table table tbody');
    if (!gradesTable) {
        console.error('找不到成绩表格元素');
        return;
    }
    
    // 检查是否有数据
    if (!grades || grades.length === 0) {
        console.log('没有成绩数据可显示');
        gradesTable.innerHTML = `
            <tr>
                <td colspan="15" class="text-center py-5">
                    <div class="empty-state">
                        <i class='bx bx-file-blank'></i>
                        <h3>暂无成绩数据</h3>
                        <p>当前学期尚未录入任何学生成绩</p>
                        <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#importGradesModal">
                            <i class='bx bx-import'></i> 导入成绩
                        </button>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // 按班级和学号排序
    console.log('开始排序学生数据');
    grades.sort((a, b) => {
        if (a.class !== b.class) {
            return a.class.localeCompare(b.class);
        }
        return parseInt(a.student_id) - parseInt(b.student_id);
    });
    
    // ⭐ 确定要渲染的学科列表
    // 所有学科的完整列表
    const allSubjects = [
        'daof', 'yuwen', 'shuxue', 'yingyu', 'laodong', 
        'tiyu', 'yinyue', 'meishu', 'kexue', 'zonghe', 'xinxi', 'shufa', 'xinli'
    ];
    
    let subjectsToRender = allSubjects;
    
    // 如果用户不是超级管理员且不是正班主任，只显示任教的学科
    if (userPermissions && !userPermissions.is_admin && userPermissions.role !== '正班主任') {
        // 从 allowedSubjects 或 teaching_map 获取任教学科
        let teachingSubjects = [];
        
        if (allowedSubjects && allowedSubjects.length > 0) {
            // 使用 allowedSubjects（学科中文名）
            teachingSubjects = allowedSubjects;
            console.log('使用 allowedSubjects:', teachingSubjects);
        } else if (userPermissions.teaching_map) {
            // 从 teaching_map 提取所有学科（去重）
            const subjectSet = new Set();
            for (const classId in userPermissions.teaching_map) {
                const subjects = userPermissions.teaching_map[classId];
                subjects.forEach(s => subjectSet.add(s));
            }
            teachingSubjects = Array.from(subjectSet);
            console.log('从 teaching_map 提取学科:', teachingSubjects);
        }
        
        // 将中文学科名转换为字段名
        if (teachingSubjects.length > 0) {
            subjectsToRender = [];
            teachingSubjects.forEach(chineseName => {
                // 查找对应的字段名
                for (const [fieldName, displayName] of Object.entries(subjectNames)) {
                    if (displayName === chineseName) {
                        subjectsToRender.push(fieldName);
                        break;
                    }
                }
            });
            
            console.log('科任老师只显示任教学科:', subjectsToRender);
            
            // 如果没有找到任何学科，显示提示
            if (subjectsToRender.length === 0) {
                gradesTable.innerHTML = `
                    <tr>
                        <td colspan="15" class="text-center py-5">
                            <div class="empty-state">
                                <i class='bx bx-info-circle'></i>
                                <h3>暂无任教学科</h3>
                                <p>您尚未被分配任教学科，请联系管理员</p>
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }
        }
    } else {
        console.log('超级管理员或正班主任，显示所有学科');
    }
    
    // ⭐ 更新表头，只显示要渲染的学科
    const tableHeader = document.querySelector('.grades-table table thead tr');
    if (tableHeader) {
        // 清空表头
        tableHeader.innerHTML = '<th>学号</th><th>姓名</th>';
        
        // 添加学科列
        subjectsToRender.forEach(subject => {
            const th = document.createElement('th');
            th.textContent = subjectNames[subject] || subject;
            tableHeader.appendChild(th);
        });
        
        console.log('表头已更新，显示学科:', subjectsToRender.map(s => subjectNames[s]));
    }
    
    // 清空表格
    gradesTable.innerHTML = '';
    
    // 分班级渲染学生成绩表
    console.log('开始渲染成绩表格');
    let currentClass = null;
    
    grades.forEach(studentGrade => {
        // 如果是新班级，添加班级标题行
        if (currentClass !== studentGrade.class) {
            currentClass = studentGrade.class;
            
            const classRow = document.createElement('tr');
            classRow.className = 'table-light';
            // colspan 需要根据实际列数调整
            classRow.innerHTML = `<td colspan="${subjectsToRender.length + 2}"><strong>${currentClass}</strong></td>`;
            gradesTable.appendChild(classRow);
        }
        
        // 创建学生行
        const row = document.createElement('tr');
        row.setAttribute('data-student-id', studentGrade.student_id);
        row.setAttribute('data-class-id', studentGrade.class_id);  // 添加班级ID属性
        
        // 添加学号和姓名单元格
        row.innerHTML = `
            <td>${studentGrade.student_id}</td>
            <td>${studentGrade.student_name}</td>
        `;
        
        // ⭐ 只添加要渲染的学科成绩单元格
        subjectsToRender.forEach(subject => {
            const cell = document.createElement('td');
            const gradeValue = studentGrade[subject] !== undefined ? studentGrade[subject] : '';
            
            // 检查是否可以编辑该学科（传入班级ID）
            const canEdit = canEditSubject(subject, studentGrade.class_id);
            
            // 创建成绩选择框
            const select = document.createElement('select');
            select.className = 'form-select form-select-sm grade-select';
            select.setAttribute('data-student-id', studentGrade.student_id);
            select.setAttribute('data-subject', subject);
            
            // 如果没有编辑权限，禁用选择框并添加提示
            if (!canEdit) {
                select.disabled = true;
                select.classList.add('disabled-subject');
                select.title = '您没有权限编辑此学科';
            }
            
            // 添加选项（支持优、良、及格、待及格、/五个等级）
            ['', '优', '良', '及格', '待及格', '/'].forEach(option => {
                const optionEl = document.createElement('option');
                optionEl.value = option;
                optionEl.textContent = option || '未填';
                if (option === gradeValue) {
                    optionEl.selected = true;
                }
                select.appendChild(optionEl);
            });
            
            // 设置样式 - 为不同等级设置不同的颜色
            if (gradeValue === '优') {
                select.classList.add('grade-a');
            } else if (gradeValue === '良') {
                select.classList.add('grade-b');
            } else if (gradeValue === '及格') {
                select.classList.add('grade-c');
            } else if (gradeValue === '待及格') {
                select.classList.add('grade-d');
            } else if (gradeValue === '/') {
                select.classList.add('grade-none');
            }
            
            cell.appendChild(select);
            row.appendChild(cell);
        });
        
        gradesTable.appendChild(row);
    });
    
    // 渲染完成后调整表格布局
    adjustTableLayout();
}

/**
 * 调整表格布局，优化显示效果
 */
function adjustTableLayout() {
    console.log('调整表格布局');
    
    // 获取表格和表头
    const table = document.querySelector('.grades-table table');
    if (!table) return;
    
    // 科目单元格默认宽度
    const defaultColWidth = 80;
    
    // 获取表头所有列
    const headers = table.querySelectorAll('thead th');
    
    // 设置科目列宽度
    headers.forEach((header, index) => {
        if (index >= 2) { // 跳过学号和姓名列
            // 根据内容长度设置宽度，但不低于最小宽度
            const text = header.textContent.trim();
            // 汉字平均宽度约为16px
            const contentWidth = Math.max(text.length * 16, defaultColWidth);
            header.style.width = `${contentWidth}px`;
            header.style.minWidth = `${defaultColWidth}px`;
        }
    });
    
    // 确保固定列背景色正确
    const fixColumns = () => {
        // 获取所有第一列和第二列的单元格
        const firstCols = table.querySelectorAll('tr td:first-child, tr th:first-child');
        const secondCols = table.querySelectorAll('tr td:nth-child(2), tr th:nth-child(2)');
        
        // 设置正确的背景色
        firstCols.forEach(cell => {
            if (cell.tagName === 'TH') {
                cell.style.backgroundColor = '#f8f9fa';
            } else {
                cell.style.backgroundColor = '#fff';
            }
            cell.style.boxShadow = '2px 0 5px -2px rgba(0,0,0,0.1)';
        });
        
        secondCols.forEach(cell => {
            if (cell.tagName === 'TH') {
                cell.style.backgroundColor = '#f8f9fa';
            } else {
                cell.style.backgroundColor = '#fff';
            }
            cell.style.boxShadow = '2px 0 5px -2px rgba(0,0,0,0.1)';
        });
    };
    
    // 执行固定列样式
    fixColumns();
    
    // 检查水平滚动条是否应该显示
    const tableContainer = document.querySelector('.table-responsive.grades-table');
    if (tableContainer) {
        // 计算表格实际宽度和容器宽度
        const tableWidth = table.offsetWidth;
        const containerWidth = tableContainer.offsetWidth;
        
        console.log(`表格宽度: ${tableWidth}px, 容器宽度: ${containerWidth}px`);
        
        // 如果表格宽度大于容器宽度，应该显示水平滚动条
        if (tableWidth > containerWidth) {
            console.log('表格宽度大于容器宽度，应该显示水平滚动条');
            // 确保overflow-x是auto
            tableContainer.style.overflowX = 'auto';
        } else {
            console.log('表格宽度小于等于容器宽度，不需要水平滚动条');
        }
    }
    
    // 监听窗口大小变化，重新调整固定列样式
    window.addEventListener('resize', function() {
        fixColumns();
        
        // 重新检查滚动条
        const tableContainer = document.querySelector('.table-responsive.grades-table');
        if (tableContainer) {
            const tableWidth = table.offsetWidth;
            const containerWidth = tableContainer.offsetWidth;
            
            console.log(`[resize] 表格宽度: ${tableWidth}px, 容器宽度: ${containerWidth}px`);
            
            if (tableWidth > containerWidth) {
                tableContainer.style.overflowX = 'auto';
            }
        }
    });
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

// 更新学生成绩
function updateGrade(selectElement) {
    const studentId = selectElement.getAttribute('data-student-id');
    const subject = selectElement.getAttribute('data-subject');
    const value = selectElement.value;
    
    // 获取学生所在的班级ID（从行数据中获取）
    const row = selectElement.closest('tr');
    const classId = row ? row.getAttribute('data-class-id') : null;
    
    // 显示保存中状态
    const originalBg = selectElement.style.backgroundColor;
    selectElement.style.backgroundColor = '#e6f7ff'; // 浅蓝色表示正在保存
    
    // 更新样式
    selectElement.className = 'form-select form-select-sm grade-select';
    if (value === '优') {
        selectElement.classList.add('grade-a');
    } else if (value === '良') {
        selectElement.classList.add('grade-b');
    } else if (value === '及格') {
        selectElement.classList.add('grade-c');
    } else if (value === '待及格') {
        selectElement.classList.add('grade-d');
    } else if (value === '/') {
        selectElement.classList.add('grade-none');
    }
    
    // 准备要发送的数据
    const gradeData = {
        semester: currentSemester,
        class_id: classId  // 添加班级ID
    };
    gradeData[subject] = value;
    
    console.log(`保存学生 ${studentId} (班级ID: ${classId}) 的 ${subject} 成绩: ${value}`);
    
    // 发送到服务器
    fetch(`/api/grades/${studentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(gradeData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP错误! 状态: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'ok') {
            showNotification(`成功保存 ${studentId} 的 ${subjectNames[subject] || subject} 成绩`, 'success');
            selectElement.style.backgroundColor = '#d4edda'; // 绿色表示保存成功
            setTimeout(() => {
                selectElement.style.backgroundColor = originalBg;
            }, 1000);
        } else {
            selectElement.style.backgroundColor = '#f8d7da'; // 红色表示保存失败
            showNotification(data.message || '保存成绩失败', 'error');
            setTimeout(() => {
                selectElement.style.backgroundColor = originalBg;
            }, 1000);
        }
    })
    .catch(error => {
        console.error('保存成绩时出错:', error);
        selectElement.style.backgroundColor = '#f8d7da'; // 红色表示保存失败
        showNotification('保存成绩时发生错误', 'error');
        setTimeout(() => {
            selectElement.style.backgroundColor = originalBg;
        }, 1000);
    });
}

// 导入成绩
function importGrades() {
    // 获取文件路径
    const filePath = document.getElementById('importFilePath').value;
    if (!filePath) {
        showNotification('无效的文件路径，请重新上传文件', 'error');
        return;
    }
    
    const semesterInput = document.getElementById('importSemester');
    if (!semesterInput || !semesterInput.value) {
        showNotification('请选择学期', 'warning');
        return;
    }
    
    const semester = semesterInput.value;
    
    // 显示确认导入按钮加载状态
    const importBtn = document.getElementById('confirmImportGrades');
    importBtn.disabled = true;
    const originalBtnText = importBtn.innerHTML;
    importBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 导入中...`;
    
    // 显示加载状态
    document.getElementById('previewContent').innerHTML += `
        <div class="alert alert-info mt-3">
            <i class='bx bx-loader-alt bx-spin'></i> 正在导入数据，请稍候...
        </div>
    `;
    
    // 发送确认导入请求
    fetch('/api/grades/confirm-import', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            file_path: filePath,
            semester: semester
        })
    })
    .then(response => response.json())
    .then(data => {
        // 恢复按钮状态
        importBtn.disabled = false;
        importBtn.innerHTML = originalBtnText;
        
        if (data.status === 'ok') {
            showNotification(data.message || '成功导入成绩', 'success');
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('importGradesModal'));
            if (modal) modal.hide();
            
            // 重置模态框
            resetImportModal();
            
            // 如果导入的学期与当前选择的学期相同，刷新数据
            if (semester === currentSemester) {
                loadGrades();
            }
        } else {
            showNotification(data.message || '导入成绩失败', 'error');
            
            // 在预览区域显示错误
            document.getElementById('previewContent').innerHTML += `
                <div class="alert alert-danger mt-3">
                    <i class='bx bx-error-circle'></i> 导入失败: ${data.message || '未知错误'}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('导入成绩时出错:', error);
        importBtn.disabled = false;
        importBtn.innerHTML = originalBtnText;
        
        showNotification('导入成绩时发生错误', 'error');
        
        // 在预览区域显示错误
        document.getElementById('previewContent').innerHTML += `
            <div class="alert alert-danger mt-3">
                <i class='bx bx-error-circle'></i> 导入失败: ${error.message}
            </div>
        `;
    });
}

// 预览成绩导入
function previewGradesImport() {
    const fileInput = document.getElementById('gradeFile');
    const semesterInput = document.getElementById('importSemester');
    const previewArea = document.getElementById('previewArea');
    const previewContent = document.getElementById('previewContent');
    const confirmImportBtn = document.getElementById('confirmImportGrades');
    
    if (!fileInput || !fileInput.files.length) {
        showNotification('请选择要导入的Excel文件', 'warning');
        return;
    }
    
    if (!semesterInput || !semesterInput.value) {
        showNotification('请选择学期', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    const semester = semesterInput.value;
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);
    formData.append('semester', semester);
    
    // 显示加载中状态
    previewContent.innerHTML = `
        <div class="text-center p-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">上传中...</span>
            </div>
            <p class="mt-3">正在上传并解析文件，请稍候...</p>
        </div>
    `;
    
    // 禁用确认导入按钮
    confirmImportBtn.disabled = true;
    
    // 发送预览请求
    fetch('/api/grades/preview-import', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 显示预览内容
            previewContent.innerHTML = data.html_preview;
            
            // 保存文件路径
            document.getElementById('importFilePath').value = data.file_path;
            
            // 启用确认导入按钮
            confirmImportBtn.disabled = false;
        } else {
            // 显示错误
            previewContent.innerHTML = `
                <div class="alert alert-danger">
                    <i class='bx bx-error-circle'></i> ${data.message || '预览成绩导入失败'}
                </div>
            `;
            confirmImportBtn.disabled = true;
        }
    })
    .catch(error => {
        console.error('预览成绩导入时出错:', error);
        previewContent.innerHTML = `
            <div class="alert alert-danger">
                <i class='bx bx-error-circle'></i> 预览成绩导入时发生错误: ${error.message}
            </div>
        `;
        confirmImportBtn.disabled = true;
    });
}

// 重置导入模态框
function resetImportModal() {
    console.log('重置导入模态框');
    
    // 完全重置文件输入
    const fileInput = document.getElementById('gradeFile');
    if (fileInput) {
        // 清空文件输入的值
        fileInput.value = '';
        
        // 创建一个新的输入元素来替换旧的，彻底清除文件选择状态
        const newFileInput = document.createElement('input');
        newFileInput.type = 'file';
        newFileInput.id = 'gradeFile';
        newFileInput.className = 'd-none';
        newFileInput.accept = '.xlsx, .xls';
        
        // 复制事件监听器
        newFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const fileNameDisplay = document.getElementById('selectedFileName');
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = file.name;
                }
                
                if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
                    showNotification('只支持Excel文件格式 (.xlsx, .xls)', 'error');
                    return;
                }
                
                // 添加延迟处理
                setTimeout(() => {
                    previewGradesImport();
                }, 100); // 添加短暂延迟，避免双击时的重复处理
            }
        });
        
        // 替换旧的元素
        if (fileInput.parentNode) {
            fileInput.parentNode.replaceChild(newFileInput, fileInput);
        }
    }
    
    // 清空文件名显示
    const fileNameDisplay = document.getElementById('selectedFileName');
    if (fileNameDisplay) {
        fileNameDisplay.textContent = '';
    }
    
    // 清空预览内容
    const previewContent = document.getElementById('previewContent');
    if (previewContent) {
        previewContent.innerHTML = '';
    }
    
    // 清空隐藏字段
    const importFilePath = document.getElementById('importFilePath');
    if (importFilePath) {
        importFilePath.value = '';
    }
    
    // 禁用确认导入按钮
    const confirmImportBtn = document.getElementById('confirmImportGrades');
    if (confirmImportBtn) {
        confirmImportBtn.disabled = true;
    }
}

// 初始化成绩导入相关事件
function initGradesImport() {
    // 文件选择事件
    const fileInput = document.getElementById('gradeFile');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            // 选择文件后自动触发预览
            const file = e.target.files[0];
            if (file) {
                // 显示文件名
                const fileNameDisplay = document.getElementById('selectedFileName');
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = file.name;
                }
                
                // 检查文件类型
                if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
                    showNotification('只支持Excel文件格式 (.xlsx, .xls)', 'error');
                    return;
                }
                
                // 自动触发预览
                setTimeout(() => {
                    previewGradesImport();
                }, 100); // 添加短暂延迟，避免双击时的重复处理
            }
        });
    }
    
    // 下载模板按钮事件
    document.getElementById('downloadTemplateBtn').addEventListener('click', function() {
        window.open('/api/grades/template', '_blank');
    });
    
    // 确认导入按钮事件
    document.getElementById('confirmImportGrades').addEventListener('click', importGrades);
    
    // 模态框关闭时重置
    document.getElementById('importGradesModal').addEventListener('hidden.bs.modal', resetImportModal);
    
    // 绑定拖放区域事件
    const importArea = document.querySelector('.import-area');
    if (importArea) {
        importArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.add('drag-over');
        });
        
        importArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('drag-over');
        });
        
        importArea.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const fileInput = document.getElementById('gradeFile');
                fileInput.files = files;
                
                // 显示文件名
                const fileNameDisplay = document.getElementById('selectedFileName');
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = files[0].name;
                }
                
                // 检查文件类型
                if (!files[0].name.endsWith('.xlsx') && !files[0].name.endsWith('.xls')) {
                    showNotification('只支持Excel文件格式 (.xlsx, .xls)', 'error');
                    return;
                }
                
                // 自动触发预览
                setTimeout(() => {
                    previewGradesImport();
                }, 100); // 添加短暂延迟，避免双击时的重复处理
            }
        });
        
        // 点击导入区域也可以触发文件选择
        importArea.addEventListener('click', function(e) {
            // 不处理按钮的点击
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                return;
            }
            
            // 检查是否已经选择了文件
            const fileInput = document.getElementById('gradeFile');
            const fileNameDisplay = document.getElementById('selectedFileName');
            
            // 如果已经选择了文件且显示了文件名，不再触发文件选择
            if (fileInput.files && fileInput.files.length > 0 && fileNameDisplay && fileNameDisplay.textContent) {
                console.log('已选择文件，不再触发文件选择对话框');
                return;
            }
            
            // 否则触发文件选择
            fileInput.click();
        });
    }
}

// 导出成绩
function exportGrades() {
    // 未实现，可以通过前端Excel库如SheetJS实现，
    // 或者可以添加后端API返回Excel文件
    showNotification('导出功能尚未实现', 'info');
}

// 一键将所有学生的所有科目成绩设为"优"
function setAllGradesExcellent() {
    // 显示确认对话框
    if (confirm('确定要将当前学期所有学生的所有科目成绩设为"优"吗？')) {
        // 显示加载中的提示
        showNotification('正在设置所有成绩...', 'info');
        
        // 首先获取所有成绩选择框
        const gradeSelects = document.querySelectorAll('.grade-select');
        
        // 如果没有成绩选择框，提示用户
        if (gradeSelects.length === 0) {
            showNotification('当前没有学生成绩数据可设置', 'warning');
            return;
        }
        
        // 记录所有要更新的数据
        const updatedGrades = {};
        
        // 将所有成绩选择框设置为"优"
        gradeSelects.forEach(select => {
            // 获取学生ID和科目
            const studentId = select.getAttribute('data-student-id');
            const subject = select.getAttribute('data-subject');
            
            // 获取班级ID
            const row = select.closest('tr');
            const classId = row ? row.getAttribute('data-class-id') : null;
            
            // 如果已经是"优"，则不需要更新
            if (select.value !== '优') {
                // 更新选择框的值
                select.value = '优';
                
                // 更新选择框的样式类
                select.className = 'form-select form-select-sm grade-select grade-a';
                
                // 将数据添加到更新列表中
                if (!updatedGrades[studentId]) {
                    updatedGrades[studentId] = { class_id: classId };
                }
                updatedGrades[studentId][subject] = '优';
            }
        });
        
        // 如果没有需要更新的内容，提示用户
        if (Object.keys(updatedGrades).length === 0) {
            showNotification('所有成绩已经是"优"了', 'info');
            return;
        }
        
        // 发送数据到服务器保存
        const promises = [];
        
        // 对每个学生发送更新请求
        for (const studentId in updatedGrades) {
            const gradeData = {
                semester: currentSemester,
                ...updatedGrades[studentId]
            };
            
            // 发送请求保存单个学生的成绩
            const promise = fetch(`/api/grades/${studentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(gradeData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'ok') {
                    throw new Error(`无法更新学生 ${studentId} 的成绩: ${data.message}`);
                }
                return data;
            });
            
            promises.push(promise);
        }
        
        // 等待所有请求完成
        Promise.all(promises)
            .then(() => {
                showNotification(`成功更新 ${Object.keys(updatedGrades).length} 名学生的所有科目成绩为"优"`, 'success');
            })
            .catch(error => {
                console.error('设置所有成绩时出错:', error);
                showNotification(`设置成绩时出错: ${error.message}`, 'error');
            });
    }
}

// 根据中文名称查找科目代码
function findSubjectCodeByName(subjectName) {
    // 遍历subjectNames对象，找到匹配的科目代码
    for (const code in subjectNames) {
        if (subjectNames[code] === subjectName) {
            console.log(`找到科目代码: ${subjectName} -> ${code}`);
            return code;
        }
    }
    console.log(`未找到科目代码: ${subjectName}`);
    return null;
}

// 清空所有成绩
function clearAllGrades() {
    // 显示确认对话框
    if (confirm('确定要清空当前学期所有学生的所有科目成绩吗？此操作无法撤销！')) {
        // 显示加载中的提示
        showNotification('正在清空所有成绩...', 'info');
        
        // 首先获取所有成绩选择框
        const gradeSelects = document.querySelectorAll('.grade-select');
        
        // 如果没有成绩选择框，提示用户
        if (gradeSelects.length === 0) {
            showNotification('当前没有学生成绩数据可清空', 'warning');
            return;
        }
        
        // 记录所有要更新的数据
        const updatedGrades = {};
        
        // 将所有成绩选择框清空
        gradeSelects.forEach(select => {
            // 获取学生ID和科目
            const studentId = select.getAttribute('data-student-id');
            const subject = select.getAttribute('data-subject');
            
            // 获取班级ID
            const row = select.closest('tr');
            const classId = row ? row.getAttribute('data-class-id') : null;
            
            // 如果已经是空的，则不需要更新
            if (select.value !== '') {
                // 更新选择框的值
                select.value = '';
                
                // 更新选择框的样式类 - 移除所有颜色类
                select.className = 'form-select form-select-sm grade-select';
                
                // 将数据添加到更新列表中
                if (!updatedGrades[studentId]) {
                    updatedGrades[studentId] = { class_id: classId };
                }
                updatedGrades[studentId][subject] = '';
            }
        });
        
        // 如果没有需要更新的内容，提示用户
        if (Object.keys(updatedGrades).length === 0) {
            showNotification('所有成绩已经是空的了', 'info');
            return;
        }
        
        // 发送数据到服务器保存
        const promises = [];
        
        // 对每个学生发送更新请求
        for (const studentId in updatedGrades) {
            const gradeData = {
                semester: currentSemester,
                ...updatedGrades[studentId]
            };
            
            // 发送请求保存单个学生的成绩
            const promise = fetch(`/api/grades/${studentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(gradeData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'ok') {
                    throw new Error(`无法更新学生 ${studentId} 的成绩: ${data.message}`);
                }
                return data;
            });
            
            promises.push(promise);
        }
        
        // 等待所有请求完成
        Promise.all(promises)
            .then(() => {
                showNotification(`成功清空 ${Object.keys(updatedGrades).length} 名学生的所有科目成绩`, 'success');
            })
            .catch(error => {
                console.error('清空所有成绩时出错:', error);
                showNotification(`清空成绩时出错: ${error.message}`, 'error');
            });
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    // 检查是否有通知容器
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
        <div class="notification-icon">
            <i class='bx bx-${type === 'success' ? 'check-circle' : type === 'error' ? 'error-circle' : type === 'warning' ? 'error' : 'info-circle'}'></i>
        </div>
        <div class="notification-content">
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close">&times;</button>
    `;
    
    // 添加到容器
    notificationContainer.appendChild(notification);
    
    // 添加关闭按钮事件
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', function() {
        notification.classList.add('notification-hiding');
        setTimeout(() => {
            notificationContainer.removeChild(notification);
        }, 300);
    });
    
    // 自动关闭
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.add('notification-hiding');
            setTimeout(() => {
                if (notification.parentNode) {
                    notificationContainer.removeChild(notification);
                }
            }, 300);
        }
    }, 5000);
}

// 列选择和粘贴功能
// 记录当前选择的列
let selectedColumn = null;
let selectedSubject = null;

document.addEventListener('DOMContentLoaded', function() {
    // 列选择和粘贴功能初始化
    initColumnSelectAndPaste();
});

// 初始化列选择和粘贴功能
function initColumnSelectAndPaste() {
    // 绑定表头点击事件
    const gradesTable = document.querySelector('.grades-table table');
    if (gradesTable) {
        const headerRow = gradesTable.querySelector('thead tr');
        if (headerRow) {
            const ths = headerRow.querySelectorAll('th');
            
            // 为每个表头单元格添加点击事件
            ths.forEach((th, index) => {
                // 只对科目列启用选择（索引从2开始是科目列）
                if (index >= 2) {
                    th.addEventListener('click', function() {
                        selectColumn(index, th.textContent.trim());
                    });
                }
            });
        }
    }
    
    // 绑定粘贴按钮事件
    const pasteToCellsBtn = document.getElementById('pasteToCellsBtn');
    if (pasteToCellsBtn) {
        pasteToCellsBtn.addEventListener('click', pasteToSelectedColumn);
    }
    
    // 绑定取消选择按钮事件
    const cancelColumnSelectBtn = document.getElementById('cancelColumnSelectBtn');
    if (cancelColumnSelectBtn) {
        cancelColumnSelectBtn.addEventListener('click', cancelColumnSelection);
    }
}

// 选择列
function selectColumn(colIndex, subjectName) {
    // 如果该列已经选中，取消选择
    if (selectedColumn === colIndex) {
        cancelColumnSelection();
        return;
    }
    
    // 首先取消之前的选择
    cancelColumnSelection();
    
    // 设置新的选中列
    selectedColumn = colIndex;
    
    // 将中文表头转换为代码中使用的科目标识符
    const subjectCode = findSubjectCodeByName(subjectName);
    selectedSubject = subjectCode || subjectName;
    
    // 获取所有单元格
    const table = document.querySelector('.grades-table table');
    const rows = table.querySelectorAll('tr');
    
    // 对所有行应用选中样式
    rows.forEach(row => {
        // 获取当前行的单元格
        const cells = row.querySelectorAll('th, td');
        
        // 检查如果该单元格存在
        if (cells.length > colIndex) {
            // 往该单元格添加选中类
            cells[colIndex].classList.add('selected-column');
        }
    });
    
    // 显示粘贴控制按钮
    document.querySelectorAll('.paste-button').forEach(button => {
        button.style.display = 'inline-block';
    });
    
    // 显示提示消息
    showNotification(`已选中"${selectedSubject}"列，您可以将Excel中复制的数据粘贴到该列`, 'info');
}

// 取消列选择
function cancelColumnSelection() {
    if (selectedColumn === null) return;
    
    // 获取所有标记为选中的单元格
    const selectedCells = document.querySelectorAll('.grades-table .selected-column');
    selectedCells.forEach(cell => {
        cell.classList.remove('selected-column');
    });
    
    // 重置选中列的标记
    selectedColumn = null;
    selectedSubject = null;
    
    // 隐藏粘贴控制按钮
    document.querySelectorAll('.paste-button').forEach(button => {
        button.style.display = 'none';
    });
}

// 将复制的内容粘贴到选中列
function pasteToSelectedColumn() {
    if (selectedColumn === null || selectedSubject === null) {
        showNotification('请先选择要粘贴的列', 'warning');
        return;
    }
    
    // 显示粘贴操作指南
    showNotification(`准备粘贴到「${selectedSubject}」列，请确保您的剪贴板中包含了要粘贴的成绩数据（优、良、及格、待及格）`, 'info');
    
    // 检查navigator.clipboard是否可用
    if (navigator.clipboard && navigator.clipboard.readText) {
        // 现代浏览器API
        navigator.clipboard.readText()
            .then(text => {
                handlePastedText(text);
            })
            .catch(err => {
                console.error('无法读取剪贴板内容:', err);
                showNotification('无法直接读取剪贴板，请手动粘贴(Ctrl+V)或点击右键选择"粘贴"', 'warning');
                promptForManualPaste();
            });
    } else {
        // 备选方案：提示用户手动粘贴
        console.warn('浏览器不支持clipboard API，将使用备选方案');
        showNotification('您的浏览器不支持自动读取剪贴板，请手动粘贴(Ctrl+V)或点击右键选择"粘贴"', 'warning');
        promptForManualPaste();
    }
}

// 提示用户手动粘贴
function promptForManualPaste() {
    // 创建临时输入框用于粘贴
    const textarea = document.createElement('textarea');
    textarea.style.position = 'fixed';
    textarea.style.top = '50%';
    textarea.style.left = '50%';
    textarea.style.transform = 'translate(-50%, -50%)';
    textarea.style.width = '300px';
    textarea.style.height = '150px';
    textarea.style.zIndex = '9999';
    textarea.style.border = '2px solid #007bff';
    textarea.style.padding = '10px';
    textarea.placeholder = '请在此处粘贴复制的数据 (Ctrl+V)，然后点击外部区域';
    
    // 创建遮罩层
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    overlay.style.zIndex = '9998';
    
    // 添加到文档
    document.body.appendChild(overlay);
    document.body.appendChild(textarea);
    
    // 自动聚焦
    textarea.focus();
    
    // 处理粘贴操作
    function handleManualPaste() {
        const text = textarea.value.trim();
        if (text) {
            handlePastedText(text);
        } else {
            showNotification('未检测到粘贴内容', 'warning');
        }
        
        // 清理
        document.body.removeChild(textarea);
        document.body.removeChild(overlay);
    }
    
    // 监听点击外部和ESC按键
    overlay.addEventListener('click', handleManualPaste);
    textarea.addEventListener('blur', handleManualPaste);
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.body.removeChild(textarea);
            document.body.removeChild(overlay);
        }
    });
}

// 处理获取到的文本
function handlePastedText(text) {
    if (!text || !text.trim()) {
        showNotification('剪贴板内容为空，请先复制数据', 'warning');
        return;
    }
    
    // 显示收到的数据
    console.log('获取到的粘贴内容:', text);
    
    // 处理复制的内容
    processPastedText(text);
}

// 处理粘贴的文本
function processPastedText(text) {
    // 分行处理文本
    const lines = text.trim().split("\n");
    
    // 输出日志信息以便调试
    console.log(`准备粘贴到列: ${selectedSubject}`);
    console.log(`粘贴的行数: ${lines.length}`);
    
    // 像"体育"这样的中文科目名字，需要查询对应的科目代码（如"tiyu"）
    // 如果选中的是中文科目名，则尝试转换为对应的科目代码
    let subjectToSearch = selectedSubject;
    let subjectChineseName = selectedSubject;
    
    // 检查是否是中文科目名
    let isChineseSubject = /[\u4e00-\u9fa5]/.test(selectedSubject);
    
    if (isChineseSubject) {
        // 中文名称，查找对应代码
        for (const code in subjectNames) {
            if (subjectNames[code] === selectedSubject) {
                subjectToSearch = code;
                console.log(`将中文科目名称 "${selectedSubject}" 转换为代码 "${code}"`);
                break;
            }
        }
    } else {
        // 可能是代码，查找对应中文名
        subjectChineseName = subjectNames[selectedSubject] || selectedSubject;
    }
    
    // 尝试多种查询方式
    let gradeSelects = [];
    
    // 1. 首先直接使用用户选中的字符串查询
    let selects = document.querySelectorAll(`select[data-subject="${selectedSubject}"]`);
    if (selects.length > 0) {
        console.log(`使用原始选中文本 "${selectedSubject}" 找到 ${selects.length} 个选择框`);
        gradeSelects = selects;
    }
    
    // 2. 如果没找到，尝试使用科目代码查询
    if (gradeSelects.length === 0 && subjectToSearch !== selectedSubject) {
        selects = document.querySelectorAll(`select[data-subject="${subjectToSearch}"]`);
        if (selects.length > 0) {
            console.log(`使用科目代码 "${subjectToSearch}" 找到 ${selects.length} 个选择框`);
            gradeSelects = selects;
        }
    }
    
    // 3. 如果还是没有找到，尝试模糊匹配
    if (gradeSelects.length === 0) {
        console.log(`未找到精确匹配的选择框，尝试模糊匹配`);
        
        // 获取所有成绩选择框
        const allSelects = document.querySelectorAll('select.grade-select');
        console.log(`总计找到 ${allSelects.length} 个成绩选择框`);
        
        // 列出所有选择框的subject属性
        console.log('现有的subject属性值:');
        const subjectValues = new Set();
        allSelects.forEach(select => {
            const subject = select.getAttribute('data-subject');
            if (subject) subjectValues.add(subject);
        });
        console.log([...subjectValues]);
        
        // 尝试匹配中文名称或代码
        const searchTexts = [selectedSubject.toLowerCase(), subjectToSearch.toLowerCase(), subjectChineseName.toLowerCase()];
        
        // 找到最佳匹配
        let bestMatch = null;
        for (const subject of subjectValues) {
            const lowerSubject = subject.toLowerCase();
            for (const searchText of searchTexts) {
                if (lowerSubject === searchText || 
                    lowerSubject.includes(searchText) || 
                    searchText.includes(lowerSubject)) {
                    bestMatch = subject;
                    console.log(`找到最佳匹配: ${bestMatch}`);
                    break;
                }
            }
            if (bestMatch) break;
        }
        
        if (bestMatch) {
            gradeSelects = document.querySelectorAll(`select[data-subject="${bestMatch}"]`);
        }
    }
    
    // 如果仍然没有找到相关成绩选择框，则退出
    if (gradeSelects.length === 0) {
        showNotification(`未找到"${selectedSubject}"相关的成绩选择框，请尝试直接点击表头的科目名称选择`, 'error');
        
        // 显示可用科目列表
        const availableSubjects = Object.values(subjectNames).join('、');
        showNotification(`可用的科目有：${availableSubjects}`, 'info');
        return;
    } else {
        console.log(`找到 ${gradeSelects.length} 个选择框用于粘贴`);
    }
    
    // 验证有效的等级
    const validGrades = ['优', '良', '及格', '待及格', '/'];
    
    // 记录要更新的数据
    const updatedGrades = {};
    let validUpdatesCount = 0;
    let errorsCount = 0;
    
    // 逐行处理数据
    for (let i = 0; i < Math.min(lines.length, gradeSelects.length); i++) {
        const value = lines[i].trim();
        const select = gradeSelects[i];
        const studentId = select.getAttribute('data-student-id');
        
        // 获取班级ID
        const row = select.closest('tr');
        const classId = row ? row.getAttribute('data-class-id') : null;
        
        // 直接使用复制的等级值
        let gradeValue = value.trim();
        
        // 如果复制的不是直接的等级，则尝试进行简单的标准化处理
        if (!validGrades.includes(gradeValue)) {
            // 对于常见的误差进行修正
            if (gradeValue === '优秀' || gradeValue === '优' || gradeValue === 'A' || gradeValue === 'a') {
                gradeValue = '优';
            } else if (gradeValue === '良好' || gradeValue === '良' || gradeValue === 'B' || gradeValue === 'b') {
                gradeValue = '良';
            } else if (gradeValue === '及格' || gradeValue === '及' || gradeValue === 'C' || gradeValue === 'c' || gradeValue === '中') {
                gradeValue = '及格';
            } else if (gradeValue === '待及格' || gradeValue === '待' || gradeValue === 'D' || gradeValue === 'd' || gradeValue === '不及格') {
                gradeValue = '待及格';
            } else if (gradeValue === '/' || gradeValue === '无' || gradeValue === '缺' || gradeValue === '缺考') {
                gradeValue = '/';
            }
        }
        
        // 检查是否是有效的等级
        if (validGrades.includes(gradeValue)) {
            // 更新选择框
            select.value = gradeValue;
            
            // 更新选择框类
            select.className = 'form-select form-select-sm grade-select';
            if (gradeValue === '优') {
                select.classList.add('grade-a');
            } else if (gradeValue === '良') {
                select.classList.add('grade-b');
            } else if (gradeValue === '及格') {
                select.classList.add('grade-c');
            } else if (gradeValue === '待及格') {
                select.classList.add('grade-d');
            } else if (gradeValue === '/') {
                select.classList.add('grade-none');
            }
            
            // 添加到要保存的数据中
            if (!updatedGrades[studentId]) {
                updatedGrades[studentId] = { class_id: classId };
            }
            updatedGrades[studentId][selectedSubject] = gradeValue;
            validUpdatesCount++;
        } else {
            console.warn(`无效的成绩等级: ${value}`);
            errorsCount++;
        }
    }
    
    // 如果没有有效更新，显示错误
    if (validUpdatesCount === 0) {
        showNotification(`无效的数据格式，请确保复制的内容包含有效的成绩等级（优、良、差或相应的数字分数）`, 'error');
        return;
    }
    
    // 保存更新的成绩
    saveUpdatedGrades(updatedGrades, validUpdatesCount, errorsCount);
}

// 保存更新的成绩数据
function saveUpdatedGrades(updatedGrades, validCount, errorCount) {
    // 发送数据到服务器保存
    const promises = [];
    
    // 对每个学生发送更新请求
    for (const studentId in updatedGrades) {
        const gradeData = {
            semester: currentSemester,
            ...updatedGrades[studentId]
        };
        
        // 发送请求保存单个学生的成绩
        const promise = fetch(`/api/grades/${studentId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(gradeData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status !== 'ok') {
                throw new Error(`无法更新学生 ${studentId} 的成绩: ${data.message}`);
            }
            return data;
        });
        
        promises.push(promise);
    }
    
    // 待所有请求完成
    Promise.all(promises)
        .then(() => {
            let message = `成功更新 ${validCount} 条成绩数据`;
            if (errorCount > 0) {
                message += `，${errorCount} 条数据无效被跳过`;
            }
            showNotification(message, 'success');
            
            // 取消列选择
            cancelColumnSelection();
        })
        .catch(error => {
            console.error('保存成绩时出错:', error);
            showNotification(`保存成绩时出错: ${error.message}`, 'error');
        });
}