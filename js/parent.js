let deyuChart = null;
let editingMessageId = null;
let historyLoaded = false;

$(function () {
    checkSession();
    bindEvents();
});

function checkSession() {
    $.get('/api/parent/student-info')
        .done(function (data) {
            if (data.status === 'ok' && data.student) {
                renderStudentHeader(data.student);
                renderComment(data.student.comments);
                renderDeyuChart(data.student.deyu);
                renderGradesList(data.student.scores);
                loadMessages();
                switchView('info');
            } else {
                loadGrades();
                switchView('verify');
            }
        })
        .fail(function (xhr) {
            loadGrades();
            switchView('verify');
        });
}

function bindEvents() {
    $('#grade-select').on('change', onGradeChange);
    $('#verify-btn').on('click', onVerify);
    $('#logout-btn').on('click', onLogout);
    $('#history-btn').on('click', onHistoryToggle);
    $('#message-input').on('input', onMessageInput);
    $('#submit-msg-btn').on('click', onSubmitMessage);
}

function loadGrades() {
    $.get('/api/parent/grades')
        .done(function (data) {
            if (data.status === 'ok' && data.grades) {
                var $select = $('#grade-select');
                $select.find('option:not(:first)').remove();
                data.grades.forEach(function (g) {
                    $select.append($('<option>').val(g).text(g));
                });
            }
        })
        .fail(function () {
            showVerifyError('网络异常，请稍后重试');
        });
}

function onGradeChange() {
    var grade = $(this).val();
    var $classSelect = $('#class-select');

    $classSelect.find('option:not(:first)').remove();
    $classSelect.append($('<option>').val('').text('请选择班级'));

    if (!grade) {
        $classSelect.prop('disabled', true);
        return;
    }

    $classSelect.prop('disabled', false);

    $.get('/api/parent/classes', { grade: grade })
        .done(function (data) {
            if (data.status === 'ok' && data.classes) {
                data.classes.forEach(function (c) {
                    $classSelect.append($('<option>').val(c.id).text(c.class_name));
                });
            }
        })
        .fail(function () {
            showVerifyError('网络异常，请稍后重试');
        });
}

function onVerify() {
    var grade = $('#grade-select').val();
    var classId = $('#class-select').val();
    var studentName = $('#student-name').val().trim();

    hideVerifyError();

    if (!grade) {
        showVerifyError('请选择年级');
        return;
    }
    if (!classId) {
        showVerifyError('请选择班级');
        return;
    }
    if (!studentName) {
        showVerifyError('请输入学生姓名');
        return;
    }
    if (studentName.length < 2 || studentName.length > 10) {
        showVerifyError('学生姓名应为2-10个字符');
        return;
    }

    setBtnLoading('#verify-btn', true);

    $.ajax({
        url: '/api/parent/verify',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ grade: grade, class_id: classId, student_name: studentName })
    })
        .done(function (data) {
            if (data.status === 'ok') {
                switchView('info');
                loadStudentInfo();
            } else {
                showVerifyError(data.message || '未找到匹配的学生信息，请检查输入');
            }
        })
        .fail(function (xhr) {
            if (xhr.status === 401) {
                showVerifyError('登录已过期，请重新验证');
            } else {
                showVerifyError('网络异常，请稍后重试');
            }
        })
        .always(function () {
            setBtnLoading('#verify-btn', false);
        });
}

function loadStudentInfo() {
    $.get('/api/parent/student-info')
        .done(function (data) {
            if (data.status === 'ok' && data.student) {
                renderStudentHeader(data.student);
                renderComment(data.student.comments);
                renderDeyuChart(data.student.deyu);
                renderGradesList(data.student.scores);
                loadMessages();
            }
        })
        .fail(function (xhr) {
            if (xhr.status === 401) {
                showVerifyError('登录已过期，请重新验证');
                switchView('verify');
            }
        });
}

function renderStudentHeader(student) {
    $('#student-name-display').text(student.name);
    $('#student-class-display').text(student.class_name);
}

function renderComment(comments) {
    var $content = $('#comment-content');
    if (comments && comments.trim()) {
        $content.text(comments);
    } else {
        $content.html('<div class="empty-tip">暂无评语</div>');
    }
}

function renderDeyuChart(deyu) {
    var $wrapper = $('#deyu-chart-wrapper');
    var $empty = $('#deyu-empty');

    if (!deyu) {
        $wrapper.addClass('d-none');
        $empty.removeClass('d-none');
        return;
    }

    var labels = Object.keys(deyu);
    var values = labels.map(function (k) { return deyu[k] || 0; });
    var hasData = values.some(function (v) { return v > 0; });

    if (!hasData) {
        $wrapper.addClass('d-none');
        $empty.removeClass('d-none');
        return;
    }

    $wrapper.removeClass('d-none');
    $empty.addClass('d-none');

    if (deyuChart) {
        deyuChart.destroy();
    }

    var ctx = document.getElementById('deyu-chart').getContext('2d');
    deyuChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: '德育得分',
                data: values,
                backgroundColor: 'rgba(102, 126, 234, 0.2)',
                borderColor: '#667eea',
                borderWidth: 2,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#667eea'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        font: { size: 10 }
                    },
                    pointLabels: {
                        font: { size: 13 }
                    }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderGradesList(scores) {
    var $list = $('#grades-list');
    var $empty = $('#grades-empty');
    $list.empty();

    if (!scores) {
        $empty.removeClass('d-none');
        return;
    }

    var hasAny = false;
    var keys = Object.keys(scores);

    keys.forEach(function (k) {
        var val = scores[k];
        if (val !== null && val !== undefined && val !== '') {
            hasAny = true;
            $list.append(
                '<div class="grade-item">' +
                    '<span class="subject-name">' + escapeHtml(k) + '</span>' +
                    '<span class="subject-score">' + escapeHtml(String(val)) + '</span>' +
                '</div>'
            );
        }
    });

    if (!hasAny) {
        $empty.removeClass('d-none');
    } else {
        $empty.addClass('d-none');
    }
}

function onHistoryToggle() {
    var $section = $('#history-section');
    var $btn = $('#history-btn');

    if ($section.hasClass('d-none')) {
        if (!historyLoaded) {
            loadHistoryGrades();
        }
        $section.removeClass('d-none');
        $btn.text('收起历史成绩');
    } else {
        $section.addClass('d-none');
        $btn.text('查看历史成绩');
    }
}

function loadHistoryGrades() {
    var $section = $('#history-section');
    $section.html('<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary"></div> 加载中...</div>');

    $.get('/api/parent/student-history-grades')
        .done(function (data) {
            if (data.status === 'ok' && data.history && data.history.length > 0) {
                renderHistoryGrades(data.history);
                historyLoaded = true;
            } else {
                $section.html('<div class="empty-tip">暂无历史成绩</div>');
            }
        })
        .fail(function (xhr) {
            if (xhr.status === 401) {
                showVerifyError('登录已过期，请重新验证');
                switchView('verify');
            } else {
                $section.html('<div class="empty-tip">网络异常，请稍后重试</div>');
            }
        });
}

function renderHistoryGrades(history) {
    var $section = $('#history-section');
    var grouped = {};

    history.forEach(function (item) {
        var key = item.exam_name;
        if (!grouped[key]) {
            grouped[key] = { exam_name: item.exam_name, exam_date: item.exam_date, subjects: [] };
        }
        grouped[key].subjects.push(item);
    });

    var html = '';
    Object.keys(grouped).forEach(function (key) {
        var group = grouped[key];
        html += '<div class="history-exam-group">';
        html += '<div class="history-exam-title">' + escapeHtml(group.exam_name) +
                '<span class="history-exam-date">' + escapeHtml(group.exam_date || '') + '</span></div>';
        group.subjects.forEach(function (s) {
            html += '<div class="grade-item">' +
                        '<span class="subject-name">' + escapeHtml(s.subject) + '</span>' +
                        '<span class="subject-score">' + escapeHtml(String(s.score)) + '</span>' +
                    '</div>';
        });
        html += '</div>';
    });

    $section.html(html);
}

function loadMessages() {
    $.get('/api/parent/messages')
        .done(function (data) {
            if (data.status === 'ok' && data.messages) {
                renderMessages(data.messages);
            }
        })
        .fail(function (xhr) {
            if (xhr.status === 401) {
                showVerifyError('登录已过期，请重新验证');
                switchView('verify');
            }
        });
}

function renderMessages(messages) {
    var $list = $('#messages-list');
    $list.empty();

    if (!messages || messages.length === 0) {
        return;
    }

    messages.forEach(function (msg) {
        var html = '<div class="message-item" data-id="' + msg.id + '">' +
            '<div class="message-content">' + escapeHtml(msg.content) + '</div>' +
            '<div class="message-time">' + escapeHtml(msg.updated_at || msg.created_at || '') + '</div>' +
            '<div class="message-actions">' +
                '<button class="btn btn-sm btn-outline-primary btn-edit-msg" data-id="' + msg.id + '" data-content="' + escapeAttr(msg.content) + '">修改</button> ' +
                '<button class="btn btn-sm btn-outline-danger btn-delete-msg" data-id="' + msg.id + '">删除</button>' +
            '</div>' +
        '</div>';
        $list.append(html);
    });

    $list.off('click', '.btn-edit-msg').on('click', '.btn-edit-msg', function () {
        var id = $(this).data('id');
        var content = $(this).data('content');
        editingMessageId = id;
        $('#message-input').val(content).trigger('input').focus();
        $('#submit-msg-btn .btn-text').text('修改寄语');
    });

    $list.off('click', '.btn-delete-msg').on('click', '.btn-delete-msg', function () {
        var id = $(this).data('id');
        if (confirm('确定要删除这条寄语吗？')) {
            deleteMessage(id);
        }
    });
}

function onMessageInput() {
    var len = $(this).val().length;
    var $counter = $('#char-count');
    $counter.text(len + '/200');
    if (len > 200) {
        $counter.addClass('over-limit');
    } else {
        $counter.removeClass('over-limit');
    }
}

function onSubmitMessage() {
    var content = $('#message-input').val().trim();

    if (!content) {
        alert('请输入寄语内容');
        return;
    }
    if (content.length > 200) {
        alert('寄语内容不能超过200字');
        return;
    }

    setBtnLoading('#submit-msg-btn', true);

    if (editingMessageId) {
        $.ajax({
            url: '/api/parent/messages/' + editingMessageId,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({ content: content })
        })
            .done(function (data) {
                if (data.status === 'ok') {
                    editingMessageId = null;
                    $('#message-input').val('').trigger('input');
                    $('#submit-msg-btn .btn-text').text('提交寄语');
                    loadMessages();
                } else {
                    alert(data.message || '修改失败');
                }
            })
            .fail(function (xhr) {
                if (xhr.status === 401) {
                    showVerifyError('登录已过期，请重新验证');
                    switchView('verify');
                } else {
                    alert('网络异常，请稍后重试');
                }
            })
            .always(function () {
                setBtnLoading('#submit-msg-btn', false);
            });
    } else {
        $.ajax({
            url: '/api/parent/messages',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ content: content })
        })
            .done(function (data) {
                if (data.status === 'ok') {
                    $('#message-input').val('').trigger('input');
                    loadMessages();
                } else {
                    alert(data.message || '提交失败');
                }
            })
            .fail(function (xhr) {
                if (xhr.status === 401) {
                    showVerifyError('登录已过期，请重新验证');
                    switchView('verify');
                } else {
                    alert('网络异常，请稍后重试');
                }
            })
            .always(function () {
                setBtnLoading('#submit-msg-btn', false);
            });
    }
}

function deleteMessage(id) {
    $.ajax({
        url: '/api/parent/messages/' + id,
        method: 'DELETE'
    })
        .done(function (data) {
            if (data.status === 'ok') {
                loadMessages();
            } else {
                alert(data.message || '删除失败');
            }
        })
        .fail(function (xhr) {
            if (xhr.status === 401) {
                showVerifyError('登录已过期，请重新验证');
                switchView('verify');
            } else {
                alert('网络异常，请稍后重试');
            }
        });
}

function onLogout() {
    $.ajax({
        url: '/api/parent/logout',
        method: 'POST'
    }).always(function () {
        editingMessageId = null;
        historyLoaded = false;
        if (deyuChart) {
            deyuChart.destroy();
            deyuChart = null;
        }
        $('#grade-select').val('');
        $('#class-select').val('').prop('disabled', true).find('option:not(:first)').remove();
        $('#class-select').append($('<option>').val('').text('请先选择年级'));
        $('#student-name').val('');
        $('#message-input').val('').trigger('input');
        $('#submit-msg-btn .btn-text').text('提交寄语');
        hideVerifyError();
        switchView('verify');
    });
}

function switchView(view) {
    $('.view-section').removeClass('active');
    if (view === 'verify') {
        $('#verify-view').addClass('active');
    } else if (view === 'info') {
        $('#info-view').addClass('active');
    }
}

function showVerifyError(msg) {
    var $el = $('#verify-error');
    $el.text(msg).removeClass('d-none');
}

function hideVerifyError() {
    $('#verify-error').addClass('d-none');
}

function setBtnLoading(selector, loading) {
    var $btn = $(selector);
    if (loading) {
        $btn.prop('disabled', true);
        $btn.find('.btn-text').addClass('d-none');
        $btn.find('.btn-loading').removeClass('d-none');
    } else {
        $btn.prop('disabled', false);
        $btn.find('.btn-text').removeClass('d-none');
        $btn.find('.btn-loading').addClass('d-none');
    }
}

function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

function escapeAttr(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
