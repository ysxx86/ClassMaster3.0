// 加载仪表盘信息
function loadDashboardInfo() {
    fetch('/api/dashboard/info')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                // 更新用户信息
                const userInfo = data.data.user;
                document.getElementById('username').textContent = userInfo.username;
                document.getElementById('userType').textContent = userInfo.is_admin ? '管理员' : '班主任';
                
                // 更新当前班级信息
                const currentClassElement = document.getElementById('currentClass');
                if (currentClassElement) {
                    currentClassElement.textContent = userInfo.current_class;
                }
                
                // 更新统计数据
                document.getElementById('studentCount').textContent = data.data.stats.student_count;
                document.getElementById('commentCount').textContent = data.data.stats.comment_count;
                document.getElementById('todoCount').textContent = data.data.stats.todo_count;
                
                // 更新成绩分布图表
                updateGradeDistribution(data.data.grade_distribution);
                
                // 更新活动列表
                updateActivitiesList(data.data.activities);
                
                // 更新待办事项列表
                updateTodosList(data.data.todos);
                
                // 更新最新评语列表
                updateCommentsList(data.data.comments);
            } else {
                showNotification(data.message || '加载仪表盘信息失败', 'error');
            }
        })
        .catch(error => {
            console.error('加载仪表盘信息时出错:', error);
            showNotification('加载仪表盘信息时发生错误', 'error');
        });
} 