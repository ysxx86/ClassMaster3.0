(function () {
    var contentArea = document.getElementById('content-area');
    var sidebar = document.getElementById('sidebar');
    var sidebarToggle = document.getElementById('sidebar-toggle');
    var btnExportPdf = document.getElementById('btn-export-pdf');
    var commitsContainer = document.getElementById('commits-container');
    var commitsLoading = document.getElementById('commits-loading');
    var commitsEnd = document.getElementById('commits-end');
    var navItems = document.querySelectorAll('.nav-item[data-target]');

    var currentSkip = 0;
    var loadLimit = 20;
    var isLoading = false;
    var hasMore = true;
    var isExporting = false;
    var allCommits = [];

    function initSidebarToggle() {
        var sectionTitles = document.querySelectorAll('.nav-section-title');
        sectionTitles.forEach(function (title) {
            title.addEventListener('click', function () {
                var targetId = this.getAttribute('data-toggle');
                var targetNav = document.getElementById(targetId);
                if (!targetNav) return;

                this.classList.toggle('collapsed');
                targetNav.classList.toggle('collapsed');
            });
        });
    }

    function initNavigation() {
        navItems.forEach(function (item) {
            item.addEventListener('click', function (e) {
                e.preventDefault();
                var targetId = this.getAttribute('data-target');
                var targetEl = document.getElementById(targetId);
                if (!targetEl) return;

                targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });

                navItems.forEach(function (n) { n.classList.remove('active'); });
                this.classList.add('active');

                if (window.innerWidth <= 768 && sidebar.classList.contains('active')) {
                    sidebar.classList.remove('active');
                }
            });
        });
    }

    function initScrollSpy() {
        if (!contentArea) return;
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var targetId = entry.target.id;
                    navItems.forEach(function (n) { n.classList.remove('active'); });
                    var matching = document.querySelectorAll('.nav-item[data-target="' + targetId + '"]');
                    matching.forEach(function (m) { m.classList.add('active'); });
                }
            });
        }, {
            root: null,
            rootMargin: '-80px 0px -60% 0px',
            threshold: 0
        });

        var sections = document.querySelectorAll('.content-section');
        sections.forEach(function (sec) {
            observer.observe(sec);
        });
    }

    function initInfiniteScroll() {
        window.addEventListener('scroll', function () {
            if (isLoading || !hasMore) return;

            var scrollBottom = window.innerHeight + window.scrollY;
            var docHeight = document.documentElement.scrollHeight;

            if (scrollBottom >= docHeight - 400) {
                loadCommits();
            }
        });
    }

    function loadCommits() {
        if (isLoading || !hasMore) return;

        isLoading = true;
        commitsLoading.style.display = 'flex';

        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/dev-guide/api/commits?skip=' + currentSkip + '&limit=' + loadLimit, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onreadystatechange = function () {
            if (xhr.readyState !== 4) return;

            isLoading = false;
            commitsLoading.style.display = 'none';

            if (xhr.status !== 200) {
                return;
            }

            try {
                var data = JSON.parse(xhr.responseText);
                if (data.status !== 'ok') return;

                hasMore = data.has_more;
                currentSkip += data.commits.length;

                data.commits.forEach(function (c) {
                    allCommits.push(c);
                });

                renderTimeline();
            } catch (e) {
                // ignore parse errors
            }
        };
        xhr.onerror = function () {
            isLoading = false;
            commitsLoading.style.display = 'none';
        };
        xhr.send();
    }

    function renderTimeline() {
        var grouped = {};
        allCommits.forEach(function (c) {
            var year = c.year || 'unknown';
            if (!grouped[year]) grouped[year] = {};
            var month = c.month || 'unknown';
            if (!grouped[year][month]) grouped[year][month] = [];
            grouped[year][month].push(c);
        });

        var html = '';
        var years = Object.keys(grouped).sort().reverse();

        years.forEach(function (year) {
            html += '<div class="timeline-year">';
            html += '<div class="timeline-year-header" onclick="this.classList.toggle(\'collapsed\'); this.nextElementSibling.classList.toggle(\'collapsed\')">';
            html += '<i class=\'bx bx-calendar\'></i> ' + escapeHtml(year) + ' 年';
            html += ' <span style="font-size:12px;font-weight:400;opacity:0.8">(' + countYearCommits(grouped[year]) + ' 条记录)</span>';
            html += '<i class=\'bx bx-chevron-down toggle-icon\'></i>';
            html += '</div>';
            html += '<div class="timeline-year-content">';

            var months = Object.keys(grouped[year]).sort().reverse();
            months.forEach(function (month) {
                var monthNames = ['', '一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];
                var monthLabel = monthNames[parseInt(month)] || month + '月';

                html += '<div class="timeline-month">';
                html += '<div class="timeline-month-header" onclick="this.classList.toggle(\'collapsed\'); this.nextElementSibling.classList.toggle(\'collapsed\')">';
                html += '<i class=\'bx bx-calendar-event\'></i> ' + escapeHtml(monthLabel);
                html += ' <span style="font-size:11px;font-weight:400;opacity:0.7">(' + grouped[year][month].length + ' 条)</span>';
                html += '<i class=\'bx bx-chevron-down toggle-icon\'></i>';
                html += '</div>';
                html += '<div class="timeline-month-content">';

                grouped[year][month].forEach(function (c) {
                    var timeStr = c.time || '';
                    if (timeStr.length > 19) timeStr = timeStr.substring(0, 19);
                    html += '<div class="commit-item">';
                    html += '<div class="commit-icon"><i class=\'bx bx-git-commit\'></i></div>';
                    html += '<div class="commit-info">';
                    html += '<div class="commit-message">' + escapeHtml(c.message) + '</div>';
                    html += '<div class="commit-meta">';
                    html += '<span><i class=\'bx bx-time-five\'></i> ' + escapeHtml(timeStr) + '</span>';
                    html += '<span><i class=\'bx bx-user\'></i> ' + escapeHtml(c.author) + '</span>';
                    html += '</div>';
                    html += '</div>';
                    html += '</div>';
                });

                html += '</div></div>';
            });

            html += '</div></div>';
        });

        commitsContainer.innerHTML = html;

        if (!hasMore) {
            commitsEnd.style.display = 'block';
        } else {
            commitsEnd.style.display = 'none';
        }
    }

    function countYearCommits(yearData) {
        var count = 0;
        Object.keys(yearData).forEach(function (month) {
            count += yearData[month].length;
        });
        return count;
    }

    function initExportPdf() {
        if (!btnExportPdf) return;

        btnExportPdf.addEventListener('click', function () {
            if (isExporting) return;

            isExporting = true;
            btnExportPdf.classList.add('loading');
            var spanEl = btnExportPdf.querySelector('span');
            var originalText = spanEl ? spanEl.textContent : '';
            if (spanEl) spanEl.textContent = '正在生成...';

            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/dev-guide/api/export-pdf', true);
            xhr.responseType = 'blob';
            xhr.onreadystatechange = function () {
                if (xhr.readyState !== 4) return;

                isExporting = false;
                btnExportPdf.classList.remove('loading');
                if (spanEl) spanEl.textContent = originalText;

                if (xhr.status === 200) {
                    var blob = xhr.response;
                    var url = window.URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;

                    var disposition = xhr.getResponseHeader('Content-Disposition');
                    var filename = 'ClassMaster3.0_开发手册.pdf';
                    if (disposition) {
                        var matches = disposition.match(/filename\*?=(?:UTF-8'')?([^;\n]+)/i);
                        if (matches && matches[1]) {
                            filename = decodeURIComponent(matches[1].replace(/['"]/g, ''));
                        }
                    }

                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                } else {
                    alert('导出失败，请重试');
                }
            };
            xhr.onerror = function () {
                isExporting = false;
                btnExportPdf.classList.remove('loading');
                if (spanEl) spanEl.textContent = originalText;
                alert('导出失败，请重试');
            };
            xhr.send();
        });
    }

    function initMobileSidebar() {
        if (!sidebarToggle || !sidebar) return;

        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('active');
        });

        document.addEventListener('click', function (e) {
            if (window.innerWidth <= 768 &&
                sidebar.classList.contains('active') &&
                !sidebar.contains(e.target) &&
                !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function init() {
        initSidebarToggle();
        initNavigation();
        initScrollSpy();
        initInfiniteScroll();
        initExportPdf();
        initMobileSidebar();
        loadCommits();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
