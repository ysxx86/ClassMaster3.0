(function () {
    var contentArea = document.getElementById('content-area');
    var sidebar = document.getElementById('sidebar');
    var sidebarToggle = document.getElementById('sidebar-toggle');
    var btnExportPdf = document.getElementById('btn-export-pdf');
    var commitsContainer = document.getElementById('commits-container');
    var commitsPagination = document.getElementById('commits-pagination');
    var navItems = document.querySelectorAll('.nav-item[data-target]');

    var currentPage = 1;
    var perPage = 20;
    var totalCommits = 0;
    var isExporting = false;

    function initNavigation() {
        navItems.forEach(function (item) {
            item.addEventListener('click', function (e) {
                e.preventDefault();
                var targetId = this.getAttribute('data-target');
                var targetEl = document.getElementById(targetId);
                if (!targetEl) return;

                contentArea.scrollTo({
                    top: targetEl.offsetTop - contentArea.offsetTop - 20,
                    behavior: 'smooth'
                });

                setActiveNav(this);

                if (window.innerWidth <= 768 && sidebar.classList.contains('active')) {
                    sidebar.classList.remove('active');
                }
            });
        });
    }

    function setActiveNav(activeItem) {
        navItems.forEach(function (item) {
            item.classList.remove('active');
        });
        if (activeItem) {
            activeItem.classList.add('active');
            var subItems = document.querySelectorAll('.nav-sub-item[data-target="' + activeItem.getAttribute('data-target') + '"]');
            subItems.forEach(function (sub) {
                sub.classList.add('active');
            });
            var mainItems = document.querySelectorAll('.nav-item:not(.nav-sub-item)[data-target="' + activeItem.getAttribute('data-target') + '"]');
            mainItems.forEach(function (main) {
                main.classList.add('active');
            });
        }
    }

    function initScrollSpy() {
        if (!contentArea) return;

        contentArea.addEventListener('scroll', function () {
            var sections = document.querySelectorAll('.content-section');
            var scrollTop = contentArea.scrollTop;
            var currentSection = null;

            sections.forEach(function (section) {
                var sectionTop = section.offsetTop - contentArea.offsetTop - 40;
                if (scrollTop >= sectionTop) {
                    currentSection = section;
                }
            });

            if (currentSection) {
                var targetId = currentSection.id;
                navItems.forEach(function (item) {
                    item.classList.remove('active');
                });
                var matchingItems = document.querySelectorAll('.nav-item[data-target="' + targetId + '"]');
                matchingItems.forEach(function (item) {
                    item.classList.add('active');
                });
            }
        });
    }

    function loadCommits(page) {
        currentPage = page || 1;

        commitsContainer.innerHTML = '<div class="commits-loading">加载中...</div>';

        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/dev-guide/api/commits?page=' + currentPage + '&per_page=' + perPage, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onreadystatechange = function () {
            if (xhr.readyState !== 4) return;

            if (xhr.status !== 200) {
                commitsContainer.innerHTML = '<div class="commits-error">无法加载开发记录，请稍后重试</div>';
                return;
            }

            try {
                var data = JSON.parse(xhr.responseText);
                if (data.status !== 'ok') {
                    commitsContainer.innerHTML = '<div class="commits-error">无法加载开发记录</div>';
                    return;
                }

                totalCommits = data.total;
                renderCommits(data.commits);
                renderPagination(data.page, data.per_page, data.total);
            } catch (e) {
                commitsContainer.innerHTML = '<div class="commits-error">数据解析失败</div>';
            }
        };
        xhr.onerror = function () {
            commitsContainer.innerHTML = '<div class="commits-error">网络异常，请稍后重试</div>';
        };
        xhr.send();
    }

    function renderCommits(commits) {
        if (!commits || commits.length === 0) {
            commitsContainer.innerHTML = '<div class="commits-empty">暂无开发记录</div>';
            return;
        }

        var html = '';
        commits.forEach(function (commit) {
            var timeStr = commit.time || '';
            if (timeStr.length > 19) {
                timeStr = timeStr.substring(0, 19);
            }
            html += '<div class="commit-item">';
            html += '<div class="commit-header">';
            html += '<span class="commit-time"><i class="bx bx-time-five"></i> ' + escapeHtml(timeStr) + '</span>';
            html += '<span class="commit-author"><i class="bx bx-user"></i> ' + escapeHtml(commit.author) + '</span>';
            html += '</div>';
            html += '<div class="commit-message">' + escapeHtml(commit.message) + '</div>';
            html += '</div>';
        });

        commitsContainer.innerHTML = html;
    }

    function renderPagination(page, perPage, total) {
        if (!commitsPagination) return;

        var totalPages = Math.ceil(total / perPage);
        if (totalPages <= 1) {
            commitsPagination.innerHTML = '';
            return;
        }

        var html = '';

        html += '<button class="page-btn" data-page="1"' + (page <= 1 ? ' disabled' : '') + '><i class="bx bx-chevrons-left"></i></button>';
        html += '<button class="page-btn" data-page="' + (page - 1) + '"' + (page <= 1 ? ' disabled' : '') + '><i class="bx bx-chevron-left"></i></button>';

        var startPage = Math.max(1, page - 2);
        var endPage = Math.min(totalPages, page + 2);

        if (startPage > 1) {
            html += '<span class="page-ellipsis">...</span>';
        }

        for (var i = startPage; i <= endPage; i++) {
            html += '<button class="page-btn' + (i === page ? ' active' : '') + '" data-page="' + i + '">' + i + '</button>';
        }

        if (endPage < totalPages) {
            html += '<span class="page-ellipsis">...</span>';
        }

        html += '<button class="page-btn" data-page="' + (page + 1) + '"' + (page >= totalPages ? ' disabled' : '') + '><i class="bx bx-chevron-right"></i></button>';
        html += '<button class="page-btn" data-page="' + totalPages + '"' + (page >= totalPages ? ' disabled' : '') + '><i class="bx bx-chevrons-right"></i></button>';

        commitsPagination.innerHTML = html;

        var pageButtons = commitsPagination.querySelectorAll('.page-btn[data-page]');
        pageButtons.forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (this.disabled) return;
                var p = parseInt(this.getAttribute('data-page'));
                if (p >= 1 && p <= totalPages) {
                    loadCommits(p);
                }
            });
        });
    }

    function initExportPdf() {
        if (!btnExportPdf) return;

        btnExportPdf.addEventListener('click', function () {
            if (isExporting) return;

            isExporting = true;
            btnExportPdf.classList.add('loading');
            var spanEl = btnExportPdf.querySelector('span');
            var originalText = spanEl ? spanEl.textContent : '';
            if (spanEl) spanEl.textContent = '正在生成PDF...';

            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/dev-guide/api/export-pdf', true);
            xhr.responseType = 'blob';
            xhr.onreadystatechange = function () {
                if (xhr.readyState !== 4) {
                    return;
                }

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

    function initSidebarToggle() {
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
        initNavigation();
        initScrollSpy();
        initExportPdf();
        initSidebarToggle();
        loadCommits(1);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
