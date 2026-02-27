// 仪表盘 JavaScript
const API_BASE = window.location.origin;
let currentUser = null;

// 检查登录状态
function checkAuth() {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');

    if (!token || !user) {
        window.location.href = '/login';
        return false;
    }

    currentUser = JSON.parse(user);
    return true;
}

// API 请求封装
async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem('token');

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    });

    if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return;
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || data.message || `HTTP ${response.status}`);
    }

    return data;
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

// 加载用户信息
function loadUserInfo() {
    if (currentUser) {
        const roleNames = {
            'user': '👤 普通用户',
            'vip': '💎 VIP',
            'admin': '👨‍💼 管理员',
            'super_admin': '👑 超级管理员'
        };
        document.getElementById('userInfo').textContent =
            `${currentUser.username || currentUser.first_name} (${roleNames[currentUser.role] || currentUser.role})`;
    }
}

// 加载仪表盘数据
async function loadDashboard() {
    const content = document.getElementById('pageContent');
    content.innerHTML = '<h2>📊 仪表盘</h2><p>加载中...</p>';

    try {
        const data = await apiRequest('/api/dashboard/stats');

        content.innerHTML = `
            <h2>📊 系统概览</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px;">
                    <h3 style="font-size: 14px; margin-bottom: 10px;">总用户数</h3>
                    <p style="font-size: 32px; font-weight: bold;">${data.total_users || 0}</p>
                </div>
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 8px;">
                    <h3 style="font-size: 14px; margin-bottom: 10px;">合集数量</h3>
                    <p style="font-size: 32px; font-weight: bold;">${data.total_collections || 0}</p>
                </div>
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 8px;">
                    <h3 style="font-size: 14px; margin-bottom: 10px;">搬运任务</h3>
                    <p style="font-size: 32px; font-weight: bold;">${data.total_tasks || 0}</p>
                </div>
                <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; padding: 20px; border-radius: 8px;">
                    <h3 style="font-size: 14px; margin-bottom: 10px;">Session 账号</h3>
                    <p style="font-size: 32px; font-weight: bold;">${data.total_sessions || 0}</p>
                </div>
            </div>
        `;
    } catch (error) {
        content.innerHTML = '<h2>📊 仪表盘</h2><p style="color: red;">加载失败，请刷新重试</p>';
        console.error('加载仪表盘失败:', error);
    }
}

// 合集管理相关变量
let collectionsCurrentPage = 1;
let collectionsCurrentLimit = 20;
let collectionsCurrentSearch = '';
let collectionsCurrentAccessFilter = '';
let selectedCollections = new Set();
let cachedBotUsername = null; // 缓存 BOT_USERNAME

// 加载合集管理
async function loadCollections() {
    const content = document.getElementById('pageContent');
    content.innerHTML = `
        <div class="page-header">
            <h2>📁 合集管理</h2>
            <div class="header-actions" style="display: flex; gap: 10px; align-items: center;">
                <input type="text" id="searchInput" placeholder="搜索合集..." class="search-input" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                <select id="accessFilter" class="filter-select" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    <option value="">全部权限</option>
                    <option value="public">公开</option>
                    <option value="vip">VIP</option>
                </select>
                <button id="batchDeleteBtn" class="btn btn-danger" style="display: none; padding: 8px 16px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">批量删除</button>
            </div>
        </div>
        <div class="collections-container">
            <table class="data-table" style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <thead>
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 12px; width: 50px;"><input type="checkbox" id="selectAll"></th>
                        <th style="padding: 12px; text-align: left;">名称</th>
                        <th style="padding: 12px; text-align: left;">描述</th>
                        <th style="padding: 12px; text-align: left;">媒体数</th>
                        <th style="padding: 12px; text-align: left;">访问权限</th>
                        <th style="padding: 12px; text-align: left;">深链接</th>
                        <th style="padding: 12px; text-align: left;">创建时间</th>
                        <th style="padding: 12px; text-align: left; width: 200px;">操作</th>
                    </tr>
                </thead>
                <tbody id="collectionsTable">
                    <tr><td colspan="8" style="padding: 20px; text-align: center;">加载中...</td></tr>
                </tbody>
            </table>
            <div class="pagination" id="collectionsPagination" style="margin-top: 20px; text-align: center;"></div>
        </div>

        <!-- 编辑合集模态框 -->
        <div id="editModal" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);">
            <div class="modal-content" style="background: white; margin: 5% auto; padding: 20px; width: 500px; border-radius: 8px;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3>编辑合集</h3>
                    <span class="close" onclick="closeEditModal()" style="cursor: pointer; font-size: 24px;">&times;</span>
                </div>
                <div class="modal-body">
                    <form id="editForm">
                        <input type="hidden" id="editCollectionId">
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">合集名称</label>
                            <input type="text" id="editName" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">描述</label>
                            <textarea id="editDescription" rows="3" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;"></textarea>
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">标签（用逗号分隔）</label>
                            <input type="text" id="editTags" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">访问权限</label>
                            <select id="editAccessLevel" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                <option value="public">公开</option>
                                <option value="vip">VIP</option>
                            </select>
                        </div>
                        <div class="form-actions" style="display: flex; gap: 10px; justify-content: flex-end;">
                            <button type="button" class="btn btn-secondary" onclick="closeEditModal()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                            <button type="button" class="btn btn-success" onclick="triggerAddMedia()" style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">➕ 新增资源</button>
                            <button type="submit" class="btn btn-primary" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">保存</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;

    // 设置事件监听
    setupCollectionsEventListeners();

    // 加载数据
    await loadCollectionsData();
}

// 设置合集管理事件监听
function setupCollectionsEventListeners() {
    // 搜索
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce((e) => {
            collectionsCurrentSearch = e.target.value;
            collectionsCurrentPage = 1;
            loadCollectionsData();
        }, 500));
    }

    // 权限筛选
    const accessFilter = document.getElementById('accessFilter');
    if (accessFilter) {
        accessFilter.addEventListener('change', (e) => {
            collectionsCurrentAccessFilter = e.target.value;
            collectionsCurrentPage = 1;
            loadCollectionsData();
        });
    }

    // 全选
    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.collection-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = e.target.checked;
                if (e.target.checked) {
                    selectedCollections.add(parseInt(cb.dataset.id));
                } else {
                    selectedCollections.delete(parseInt(cb.dataset.id));
                }
            });
            updateBatchDeleteButton();
        });
    }

    // 批量删除
    const batchDeleteBtn = document.getElementById('batchDeleteBtn');
    if (batchDeleteBtn) {
        batchDeleteBtn.addEventListener('click', batchDeleteCollections);
    }

    // 编辑表单提交
    const editForm = document.getElementById('editForm');
    if (editForm) {
        editForm.addEventListener('submit', handleCollectionEditSubmit);
    }
}

// 加载合集数据
async function loadCollectionsData() {
    try {
        // 如果还没有缓存 BOT_USERNAME，先获取
        if (!cachedBotUsername) {
            try {
                const settings = await apiRequest('/api/settings');
                cachedBotUsername = settings.BOT_USERNAME || 'your_bot';
            } catch (err) {
                console.error('获取 BOT_USERNAME 失败:', err);
                cachedBotUsername = 'your_bot';
            }
        }

        const params = new URLSearchParams({
            page: collectionsCurrentPage,
            limit: collectionsCurrentLimit
        });

        if (collectionsCurrentSearch) params.append('search', collectionsCurrentSearch);
        if (collectionsCurrentAccessFilter) params.append('access_level', collectionsCurrentAccessFilter);

        const data = await apiRequest(`/api/collections?${params}`);
        renderCollectionsTable(data.collections);
        renderCollectionsPagination(data.total, data.page, data.limit);
    } catch (error) {
        console.error('加载合集失败:', error);
        document.getElementById('collectionsTable').innerHTML = '<tr><td colspan="8" style="padding: 20px; text-align: center; color: red;">加载失败</td></tr>';
    }
}

// 渲染合集表格
function renderCollectionsTable(collections) {
    const tbody = document.getElementById('collectionsTable');

    if (collections.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="padding: 20px; text-align: center; color: #999;">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = collections.map(col => {
        const escapedName = col.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const escapedCode = col.deep_link_code.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const deepLink = `https://t.me/${cachedBotUsername}?start=${col.deep_link_code}`;
        const escapedDeepLink = deepLink.replace(/'/g, "\\'").replace(/"/g, '&quot;');

        return `
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 12px;">
                <input type="checkbox" class="collection-checkbox" data-id="${col.id}" onchange="handleCollectionCheckbox(${col.id}, this.checked)">
            </td>
            <td style="padding: 12px;">${col.name}</td>
            <td style="padding: 12px;">${col.description || '-'}</td>
            <td style="padding: 12px;">${col.media_count}</td>
            <td style="padding: 12px;">${col.access_level === 'public' ? '公开' : 'VIP'}</td>
            <td style="padding: 12px;">
                <div style="display: flex; align-items: center; gap: 5px;">
                    <a href="${deepLink}" target="_blank" style="font-size: 12px; color: #007bff; text-decoration: none; word-break: break-all;">${deepLink}</a>
                    <button onclick="copyDeepLinkDirect('${escapedDeepLink}')" style="padding: 4px 8px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; flex-shrink: 0;" title="复制深链接">📋</button>
                </div>
            </td>
            <td style="padding: 12px;">${new Date(col.created_at).toLocaleString('zh-CN')}</td>
            <td style="padding: 12px;">
                <button onclick="editCollection(${col.id})" style="padding: 4px 12px; margin-right: 5px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">编辑</button>
                <button onclick="deleteCollection(${col.id}, '${escapedName}')" style="padding: 4px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">删除</button>
            </td>
        </tr>
    `;
    }).join('');
}

// 渲染分页
function renderCollectionsPagination(total, page, limit) {
    const totalPages = Math.ceil(total / limit);
    const pagination = document.getElementById('collectionsPagination');

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '<div style="display: flex; gap: 5px; justify-content: center; align-items: center;">';

    if (page > 1) {
        html += `<button onclick="goToCollectionsPage(${page - 1})" style="padding: 5px 10px; border: 1px solid #ddd; background: white; cursor: pointer; border-radius: 4px;">上一页</button>`;
    }

    html += `<span style="padding: 5px 15px;">第 ${page} / ${totalPages} 页</span>`;

    if (page < totalPages) {
        html += `<button onclick="goToCollectionsPage(${page + 1})" style="padding: 5px 10px; border: 1px solid #ddd; background: white; cursor: pointer; border-radius: 4px;">下一页</button>`;
    }

    html += '</div>';
    pagination.innerHTML = html;
}

// 跳转页面
function goToCollectionsPage(page) {
    collectionsCurrentPage = page;
    loadCollectionsData();
}

// 处理复选框变化
function handleCollectionCheckbox(id, checked) {
    if (checked) {
        selectedCollections.add(id);
    } else {
        selectedCollections.delete(id);
    }
    updateBatchDeleteButton();
}

// 更新批量删除按钮
function updateBatchDeleteButton() {
    const btn = document.getElementById('batchDeleteBtn');
    if (btn) {
        btn.style.display = selectedCollections.size > 0 ? 'block' : 'none';
        btn.textContent = `批量删除 (${selectedCollections.size})`;
    }
}

// 编辑合集
async function editCollection(id) {
    try {
        const data = await apiRequest(`/api/collections/${id}`);

        document.getElementById('editCollectionId').value = data.id;
        document.getElementById('editName').value = data.name;
        document.getElementById('editDescription').value = data.description || '';
        document.getElementById('editTags').value = data.tags ? data.tags.join(', ') : '';
        document.getElementById('editAccessLevel').value = data.access_level;

        document.getElementById('editModal').style.display = 'block';
    } catch (error) {
        console.error('加载合集详情失败:', error);
        alert('加载合集详情失败');
    }
}

// 关闭编辑模态框
function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

// 处理编辑表单提交
async function handleCollectionEditSubmit(e) {
    e.preventDefault();

    const id = document.getElementById('editCollectionId').value;
    const name = document.getElementById('editName').value;
    const description = document.getElementById('editDescription').value;
    const tags = document.getElementById('editTags').value.split(',').map(t => t.trim()).filter(t => t);
    const access_level = document.getElementById('editAccessLevel').value;

    try {
        await apiRequest(`/api/collections/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ name, description, tags, access_level })
        });

        closeEditModal();
        loadCollectionsData();
        alert('更新成功');
    } catch (error) {
        console.error('更新失败:', error);
        alert('更新失败');
    }
}

// 删除合集
async function deleteCollection(id, name) {
    if (!confirm(`确定要删除合集 "${name}" 吗？此操作不可恢复！`)) {
        return;
    }

    try {
        await apiRequest(`/api/collections/${id}`, {
            method: 'DELETE'
        });

        loadCollectionsData();
        alert('删除成功');
    } catch (error) {
        console.error('删除失败:', error);
        alert('删除失败');
    }
}

// 批量删除合集
async function batchDeleteCollections() {
    if (selectedCollections.size === 0) {
        return;
    }

    if (!confirm(`确定要删除选中的 ${selectedCollections.size} 个合集吗？此操作不可恢复！`)) {
        return;
    }

    try {
        const ids = Array.from(selectedCollections);
        await apiRequest('/api/collections/batch', {
            method: 'DELETE',
            body: JSON.stringify({ collection_ids: ids })
        });

        selectedCollections.clear();
        loadCollectionsData();
        alert('批量删除成功');
    } catch (error) {
        console.error('批量删除失败:', error);
        alert('批量删除失败');
    }
}

// 触发添加媒体
async function triggerAddMedia() {
    const collectionId = document.getElementById('editCollectionId').value;

    if (!collectionId) {
        alert('无法获取合集 ID');
        return;
    }

    try {
        const data = await apiRequest(`/api/collections/${collectionId}/trigger-add-media`, {
            method: 'POST'
        });

        closeEditModal();
        alert(data.message || '已通知 Bot，请在 Telegram 中继续操作');
    } catch (error) {
        console.error('触发添加媒体失败:', error);
        alert('触发失败: ' + (error.message || '未知错误'));
    }
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 加载其他页面（占位）
function loadTasks() {
    const content = document.getElementById('pageContent');
    content.innerHTML = `
        <div class="page-header">
            <h2>🔄 搬运任务</h2>
            <div class="header-actions" style="display: flex; gap: 10px; align-items: center;">
                <select id="taskStatusFilter" class="filter-select" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    <option value="">全部状态</option>
                    <option value="pending">等待中</option>
                    <option value="running">执行中</option>
                    <option value="completed">已完成</option>
                    <option value="failed">失败</option>
                </select>
                <button id="createTaskBtn" class="btn btn-primary" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">➕ 创建任务</button>
            </div>
        </div>
        <div class="tasks-container">
            <table class="data-table" style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <thead>
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 12px; text-align: left;">任务名称</th>
                        <th style="padding: 12px; text-align: left;">来源频道</th>
                        <th style="padding: 12px; text-align: left;">过滤类型</th>
                        <th style="padding: 12px; text-align: left;">状态</th>
                        <th style="padding: 12px; text-align: left;">进度</th>
                        <th style="padding: 12px; text-align: left;">创建时间</th>
                        <th style="padding: 12px; text-align: left; width: 200px;">操作</th>
                    </tr>
                </thead>
                <tbody id="tasksTable">
                    <tr><td colspan="7" style="padding: 20px; text-align: center;">加载中...</td></tr>
                </tbody>
            </table>
            <div class="pagination" id="tasksPagination" style="margin-top: 20px; text-align: center;"></div>
        </div>

        <!-- 创建任务模态框 -->
        <div id="createTaskModal" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);">
            <div class="modal-content" style="background: white; margin: 5% auto; padding: 20px; width: 500px; border-radius: 8px;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3>创建搬运任务</h3>
                    <span class="close" onclick="closeCreateTaskModal()" style="cursor: pointer; font-size: 24px;">&times;</span>
                </div>
                <div class="modal-body">
                    <form id="createTaskForm">
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">任务名称</label>
                            <input type="text" id="taskName" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">来源频道 ID</label>
                            <input type="text" id="sourceChatId" required placeholder="-1001234567890 或 @username" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">过滤类型</label>
                            <select id="filterType" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                <option value="all">全部媒体</option>
                                <option value="photo">仅图片</option>
                                <option value="video">仅视频</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">关键词过滤（用逗号分隔，可选）</label>
                            <input type="text" id="filterKeywords" placeholder="关键词1, 关键词2" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: flex; align-items: center; cursor: pointer;">
                                <input type="checkbox" id="transferAllHistory" style="margin-right: 8px; width: 18px; height: 18px; cursor: pointer;">
                                <span>搬运全部历史消息</span>
                            </label>
                            <small style="color: #666; display: block; margin-top: 5px;">勾选后将搬运频道的所有历史消息，不勾选则只搬运指定时间范围内的消息</small>
                        </div>
                        <div id="dateRangeGroup" class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">日期范围（可选）</label>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <div style="flex: 1;">
                                    <label style="display: block; margin-bottom: 5px; font-size: 12px; color: #666;">开始日期</label>
                                    <input type="date" id="filterDateFrom" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                </div>
                                <div style="flex: 1;">
                                    <label style="display: block; margin-bottom: 5px; font-size: 12px; color: #666;">结束日期</label>
                                    <input type="date" id="filterDateTo" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                </div>
                            </div>
                            <small style="color: #666; display: block; margin-top: 5px;">不填写则搬运所有消息</small>
                        </div>
                        <div class="form-actions" style="display: flex; gap: 10px; justify-content: flex-end;">
                            <button type="button" class="btn btn-secondary" onclick="closeCreateTaskModal()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                            <button type="submit" class="btn btn-primary" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">创建</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <!-- 审核任务模态框 -->
        <div id="approveTaskModal" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);">
            <div class="modal-content" style="background: white; margin: 5% auto; padding: 20px; width: 500px; border-radius: 8px;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3>审核任务并创建合集</h3>
                    <span class="close" onclick="closeApproveTaskModal()" style="cursor: pointer; font-size: 24px;">&times;</span>
                </div>
                <div class="modal-body">
                    <form id="approveTaskForm">
                        <input type="hidden" id="approveTaskId">
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">合集名称</label>
                            <input type="text" id="approveName" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">描述</label>
                            <textarea id="approveDescription" rows="3" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;"></textarea>
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">标签（用逗号分隔）</label>
                            <input type="text" id="approveTags" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">访问权限</label>
                            <select id="approveAccessLevel" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                <option value="public">公开</option>
                                <option value="vip">VIP</option>
                            </select>
                        </div>
                        <div class="form-actions" style="display: flex; gap: 10px; justify-content: flex-end;">
                            <button type="button" class="btn btn-secondary" onclick="closeApproveTaskModal()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                            <button type="submit" class="btn btn-primary" style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">创建合集</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;

    // 设置事件监听
    setupTasksEventListeners();

    // 加载数据
    loadTasksData();
}

function loadSessions() {
    const content = document.getElementById('pageContent');
    content.innerHTML = `
        <div class="page-header">
            <h2>🔑 Session 管理</h2>
            <div class="header-actions" style="display: flex; gap: 10px; align-items: center;">
                <button id="addSessionBtn" class="btn btn-primary" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">➕ 添加账号</button>
            </div>
        </div>
        <div class="sessions-container">
            <table class="data-table" style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <thead>
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 12px; text-align: left;">手机号</th>
                        <th style="padding: 12px; text-align: left;">优先级</th>
                        <th style="padding: 12px; text-align: left;">状态</th>
                        <th style="padding: 12px; text-align: left;">搬运次数</th>
                        <th style="padding: 12px; text-align: left;">冷却时间</th>
                        <th style="padding: 12px; text-align: left;">最后使用</th>
                        <th style="padding: 12px; text-align: left; width: 200px;">操作</th>
                    </tr>
                </thead>
                <tbody id="sessionsTable">
                    <tr><td colspan="7" style="padding: 20px; text-align: center;">加载中...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- 添加 Session 模态框 -->
        <div id="addSessionModal" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);">
            <div class="modal-content" style="background: white; margin: 5% auto; padding: 20px; width: 500px; border-radius: 8px;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3>添加 Session 账号</h3>
                    <span class="close" onclick="closeAddSessionModal()" style="cursor: pointer; font-size: 24px;">&times;</span>
                </div>
                <div class="modal-body">
                    <div id="sessionLoginStep1">
                        <form id="addSessionForm">
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px;">手机号（带国家码）</label>
                                <input type="text" id="sessionPhone" required placeholder="+8613800138000" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            </div>
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px;">API ID</label>
                                <input type="number" id="sessionApiId" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            </div>
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px;">API Hash</label>
                                <input type="text" id="sessionApiHash" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            </div>
                            <div class="form-actions" style="display: flex; gap: 10px; justify-content: flex-end;">
                                <button type="button" class="btn btn-secondary" onclick="closeAddSessionModal()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                                <button type="submit" class="btn btn-primary" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">发送验证码</button>
                            </div>
                        </form>
                    </div>
                    <div id="sessionLoginStep2" style="display: none;">
                        <form id="addSessionCodeForm">
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px;">验证码</label>
                                <input type="text" id="sessionCode" required placeholder="请输入收到的验证码" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            </div>
                            <div class="form-actions" style="display: flex; gap: 10px; justify-content: flex-end;">
                                <button type="button" class="btn btn-secondary" onclick="closeAddSessionModal()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                                <button type="submit" class="btn btn-primary" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">登录</button>
                            </div>
                        </form>
                    </div>
                    <div id="sessionLoginStep3" style="display: none;">
                        <form id="addSessionPasswordForm">
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px;">两步验证密码</label>
                                <input type="password" id="sessionPassword" required placeholder="请输入两步验证密码" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            </div>
                            <div class="form-actions" style="display: flex; gap: 10px; justify-content: flex-end;">
                                <button type="button" class="btn btn-secondary" onclick="closeAddSessionModal()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                                <button type="submit" class="btn btn-primary" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">登录</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <!-- 编辑 Session 模态框 -->
        <div id="editSessionModal" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);">
            <div class="modal-content" style="background: white; margin: 5% auto; padding: 20px; width: 500px; border-radius: 8px;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3>编辑 Session 账号</h3>
                    <span class="close" onclick="closeEditSessionModal()" style="cursor: pointer; font-size: 24px;">&times;</span>
                </div>
                <div class="modal-body">
                    <form id="editSessionForm">
                        <input type="hidden" id="editSessionId">
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">优先级</label>
                            <input type="number" id="editSessionPriority" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            <small style="color: #666;">数字越大优先级越高</small>
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: flex; align-items: center; gap: 10px;">
                                <input type="checkbox" id="editSessionActive">
                                <span>启用此账号</span>
                            </label>
                        </div>
                        <div class="form-actions" style="display: flex; gap: 10px; justify-content: flex-end;">
                            <button type="button" class="btn btn-secondary" onclick="closeEditSessionModal()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                            <button type="submit" class="btn btn-primary" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">保存</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;

    // 设置事件监听
    setupSessionsEventListeners();

    // 加载数据
    loadSessionsData();
}

// ==================== Session 管理 ====================

let sessionLoginData = {}; // 保存登录过程中的数据

// 设置 Session 事件监听
function setupSessionsEventListeners() {
    // 添加账号按钮
    const addSessionBtn = document.getElementById('addSessionBtn');
    if (addSessionBtn) {
        addSessionBtn.addEventListener('click', openAddSessionModal);
    }

    // 第一步：发送验证码
    const addSessionForm = document.getElementById('addSessionForm');
    if (addSessionForm) {
        addSessionForm.addEventListener('submit', handleSendCodeSubmit);
    }

    // 第二步：输入验证码
    const addSessionCodeForm = document.getElementById('addSessionCodeForm');
    if (addSessionCodeForm) {
        addSessionCodeForm.addEventListener('submit', handleCodeSubmit);
    }

    // 第三步：输入两步验证密码
    const addSessionPasswordForm = document.getElementById('addSessionPasswordForm');
    if (addSessionPasswordForm) {
        addSessionPasswordForm.addEventListener('submit', handlePasswordSubmit);
    }

    // 编辑 Session 表单提交
    const editSessionForm = document.getElementById('editSessionForm');
    if (editSessionForm) {
        editSessionForm.addEventListener('submit', handleEditSessionSubmit);
    }
}

// 加载 Session 数据
async function loadSessionsData() {
    try {
        const data = await apiRequest('/api/sessions');
        renderSessionsTable(data);
    } catch (error) {
        console.error('加载 Session 失败:', error);
        document.getElementById('sessionsTable').innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: red;">加载失败</td></tr>';
    }
}

// 渲染 Session 表格
function renderSessionsTable(sessions) {
    const tbody = document.getElementById('sessionsTable');

    if (sessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: #999;">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = sessions.map(session => {
        const status = session.is_active ? '✅ 启用' : '❌ 禁用';
        const cooldown = session.cooldown_until
            ? new Date(session.cooldown_until) > new Date()
                ? `冷却至 ${new Date(session.cooldown_until).toLocaleString('zh-CN')}`
                : '-'
            : '-';
        const lastUsed = session.last_used_at
            ? new Date(session.last_used_at).toLocaleString('zh-CN')
            : '从未使用';

        return `
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 12px;">${session.phone_number}</td>
            <td style="padding: 12px;">${session.priority}</td>
            <td style="padding: 12px;">${status}</td>
            <td style="padding: 12px;">${session.transfer_count}</td>
            <td style="padding: 12px;">${cooldown}</td>
            <td style="padding: 12px;">${lastUsed}</td>
            <td style="padding: 12px;">
                <button onclick="editSession(${session.id}, ${session.priority}, ${session.is_active})" style="padding: 4px 12px; margin-right: 5px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">编辑</button>
                <button onclick="deleteSession(${session.id}, '${session.phone_number}')" style="padding: 4px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">删除</button>
            </td>
        </tr>
    `;
    }).join('');
}

// 打开添加 Session 模态框
function openAddSessionModal() {
    document.getElementById('addSessionModal').style.display = 'block';
    // 重置到第一步
    document.getElementById('sessionLoginStep1').style.display = 'block';
    document.getElementById('sessionLoginStep2').style.display = 'none';
    document.getElementById('sessionLoginStep3').style.display = 'none';
    document.getElementById('addSessionForm').reset();
    sessionLoginData = {};
}

// 关闭添加 Session 模态框
function closeAddSessionModal() {
    document.getElementById('addSessionModal').style.display = 'none';
    sessionLoginData = {};
}

// 第一步：发送验证码
async function handleSendCodeSubmit(e) {
    e.preventDefault();

    const phone_number = document.getElementById('sessionPhone').value;
    const api_id = parseInt(document.getElementById('sessionApiId').value);
    const api_hash = document.getElementById('sessionApiHash').value;

    // 保存数据供后续步骤使用
    sessionLoginData = {
        phone_number,
        api_id,
        api_hash
    };

    try {
        const data = await apiRequest('/api/sessions/login', {
            method: 'POST',
            body: JSON.stringify({
                phone_number,
                api_id,
                api_hash,
                code: null,
                password: null
            })
        });

        if (data.success && data.message && data.message.includes('验证码')) {
            // 验证码已发送，显示第二步
            document.getElementById('sessionLoginStep1').style.display = 'none';
            document.getElementById('sessionLoginStep2').style.display = 'block';
            alert(data.message || '验证码已发送，请查收');
        } else {
            alert(data.message || '发送验证码失败');
        }
    } catch (error) {
        console.error('发送验证码失败:', error);
        alert('发送验证码失败: ' + (error.message || '未知错误'));
    }
}

// 第二步：输入验证码
async function handleCodeSubmit(e) {
    e.preventDefault();

    const code = document.getElementById('sessionCode').value;

    try {
        const data = await apiRequest('/api/sessions/login', {
            method: 'POST',
            body: JSON.stringify({
                phone_number: sessionLoginData.phone_number,
                api_id: sessionLoginData.api_id,
                api_hash: sessionLoginData.api_hash,
                code: code,
                password: null
            })
        });

        if (data.success && !data.password_required) {
            // 登录成功
            closeAddSessionModal();
            loadSessionsData();
            alert(data.message || '登录成功');
        } else if (data.password_required) {
            // 需要两步验证密码，显示第三步
            document.getElementById('sessionLoginStep2').style.display = 'none';
            document.getElementById('sessionLoginStep3').style.display = 'block';
            alert(data.message || '需要输入两步验证密码');
        } else {
            alert(data.message || '验证码错误');
        }
    } catch (error) {
        console.error('验证码登录失败:', error);
        alert('验证码登录失败: ' + (error.message || '未知错误'));
    }
}

// 第三步：输入两步验证密码
async function handlePasswordSubmit(e) {
    e.preventDefault();

    const password = document.getElementById('sessionPassword').value;
    const code = document.getElementById('sessionCode').value;

    try {
        const data = await apiRequest('/api/sessions/login', {
            method: 'POST',
            body: JSON.stringify({
                phone_number: sessionLoginData.phone_number,
                api_id: sessionLoginData.api_id,
                api_hash: sessionLoginData.api_hash,
                code: code,
                password: password
            })
        });

        if (data.success) {
            // 登录成功
            closeAddSessionModal();
            loadSessionsData();
            alert(data.message || '登录成功');
        } else {
            alert(data.message || '密码错误');
        }
    } catch (error) {
        console.error('两步验证失败:', error);
        alert('两步验证失败: ' + (error.message || '未知错误'));
    }
}

// 编辑 Session
function editSession(sessionId, priority, isActive) {
    document.getElementById('editSessionId').value = sessionId;
    document.getElementById('editSessionPriority').value = priority;
    document.getElementById('editSessionActive').checked = isActive;
    document.getElementById('editSessionModal').style.display = 'block';
}

// 关闭编辑 Session 模态框
function closeEditSessionModal() {
    document.getElementById('editSessionModal').style.display = 'none';
}

// 处理编辑 Session 表单提交
async function handleEditSessionSubmit(e) {
    e.preventDefault();

    const sessionId = document.getElementById('editSessionId').value;
    const priority = parseInt(document.getElementById('editSessionPriority').value);
    const is_active = document.getElementById('editSessionActive').checked;

    try {
        await apiRequest(`/api/sessions/${sessionId}`, {
            method: 'PUT',
            body: JSON.stringify({ priority, is_active })
        });

        closeEditSessionModal();
        loadSessionsData();
        alert('更新成功');
    } catch (error) {
        console.error('更新失败:', error);
        alert('更新失败');
    }
}

// 删除 Session
async function deleteSession(sessionId, phoneNumber) {
    if (!confirm(`确定要删除账号 "${phoneNumber}" 吗？`)) {
        return;
    }

    try {
        await apiRequest(`/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });

        loadSessionsData();
        alert('账号已删除');
    } catch (error) {
        console.error('删除失败:', error);
        alert('删除失败');
    }
}

// ==================== 搬运任务管理 ====================

let tasksCurrentPage = 1;
let tasksCurrentLimit = 20;
let tasksCurrentStatusFilter = '';

// 设置搬运任务事件监听
function setupTasksEventListeners() {
    // 状态筛选
    const statusFilter = document.getElementById('taskStatusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', (e) => {
            tasksCurrentStatusFilter = e.target.value;
            tasksCurrentPage = 1;
            loadTasksData();
        });
    }

    // 创建任务按钮
    const createTaskBtn = document.getElementById('createTaskBtn');
    if (createTaskBtn) {
        createTaskBtn.addEventListener('click', openCreateTaskModal);
    }

    // 全频道搬运复选框
    const transferAllHistory = document.getElementById('transferAllHistory');
    if (transferAllHistory) {
        transferAllHistory.addEventListener('change', (e) => {
            const dateRangeGroup = document.getElementById('dateRangeGroup');
            if (e.target.checked) {
                // 勾选时禁用时间选择
                dateRangeGroup.style.display = 'none';
                document.getElementById('filterDateFrom').value = '';
                document.getElementById('filterDateTo').value = '';
            } else {
                // 不勾选时显示时间选择
                dateRangeGroup.style.display = 'block';
            }
        });
    }

    // 创建任务表单提交
    const createTaskForm = document.getElementById('createTaskForm');
    if (createTaskForm) {
        createTaskForm.addEventListener('submit', handleCreateTaskSubmit);
    }

    // 审核任务表单提交
    const approveTaskForm = document.getElementById('approveTaskForm');
    if (approveTaskForm) {
        approveTaskForm.addEventListener('submit', handleApproveTaskSubmit);
    }
}

// 加载搬运任务数据
async function loadTasksData() {
    try {
        const params = new URLSearchParams({
            page: tasksCurrentPage,
            limit: tasksCurrentLimit
        });

        if (tasksCurrentStatusFilter) params.append('status', tasksCurrentStatusFilter);

        const data = await apiRequest(`/api/tasks?${params}`);
        renderTasksTable(data.tasks);
        renderTasksPagination(data.total, data.page, data.limit);
    } catch (error) {
        console.error('加载任务失败:', error);
        document.getElementById('tasksTable').innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: red;">加载失败</td></tr>';
    }
}

// 渲染任务表格
function renderTasksTable(tasks) {
    const tbody = document.getElementById('tasksTable');

    if (tasks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: #999;">暂无数据</td></tr>';
        return;
    }

    const statusMap = {
        'pending': '⏳ 等待中',
        'running': '▶️ 执行中',
        'completed': '✅ 已完成',
        'failed': '❌ 失败'
    };

    const filterTypeMap = {
        'all': '全部媒体',
        'photo': '仅图片',
        'video': '仅视频'
    };

    tbody.innerHTML = tasks.map(task => {
        const progress = task.progress_total > 0
            ? `${task.progress_current}/${task.progress_total}`
            : '-';

        const sourceChat = task.source_chat_username
            ? `@${task.source_chat_username}`
            : task.source_chat_id;

        let actions = '';
        if (task.status === 'completed') {
            actions = `<button onclick="approveTask(${task.id})" style="padding: 4px 12px; margin-right: 5px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">审核</button>`;
        }
        actions += `<button onclick="deleteTask(${task.id}, '${task.task_name.replace(/'/g, "\\'")}'))" style="padding: 4px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">删除</button>`;

        return `
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 12px;">${task.task_name}</td>
            <td style="padding: 12px;">${sourceChat}</td>
            <td style="padding: 12px;">${filterTypeMap[task.filter_type] || task.filter_type}</td>
            <td style="padding: 12px;">${statusMap[task.status] || task.status}</td>
            <td style="padding: 12px;">${progress}</td>
            <td style="padding: 12px;">${new Date(task.created_at).toLocaleString('zh-CN')}</td>
            <td style="padding: 12px;">${actions}</td>
        </tr>
    `;
    }).join('');
}

// 渲染分页
function renderTasksPagination(total, page, limit) {
    const totalPages = Math.ceil(total / limit);
    const pagination = document.getElementById('tasksPagination');

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '<div style="display: flex; gap: 5px; justify-content: center; align-items: center;">';

    if (page > 1) {
        html += `<button onclick="goToTasksPage(${page - 1})" style="padding: 5px 10px; border: 1px solid #ddd; background: white; cursor: pointer; border-radius: 4px;">上一页</button>`;
    }

    html += `<span style="padding: 5px 15px;">第 ${page} / ${totalPages} 页</span>`;

    if (page < totalPages) {
        html += `<button onclick="goToTasksPage(${page + 1})" style="padding: 5px 10px; border: 1px solid #ddd; background: white; cursor: pointer; border-radius: 4px;">下一页</button>`;
    }

    html += '</div>';
    pagination.innerHTML = html;
}

// 跳转页面
function goToTasksPage(page) {
    tasksCurrentPage = page;
    loadTasksData();
}

// 打开创建任务模态框
function openCreateTaskModal() {
    document.getElementById('createTaskModal').style.display = 'block';
    document.getElementById('createTaskForm').reset();
}

// 关闭创建任务模态框
function closeCreateTaskModal() {
    document.getElementById('createTaskModal').style.display = 'none';
}

// 处理创建任务表单提交
async function handleCreateTaskSubmit(e) {
    e.preventDefault();

    const taskName = document.getElementById('taskName').value;
    const sourceChatInput = document.getElementById('sourceChatId').value.trim();
    const filterType = document.getElementById('filterType').value;
    const filterKeywordsInput = document.getElementById('filterKeywords').value;
    const transferAllHistory = document.getElementById('transferAllHistory').checked;
    const filterDateFrom = document.getElementById('filterDateFrom').value;
    const filterDateTo = document.getElementById('filterDateTo').value;

    // 解析频道 ID
    let sourceChatId = 0;
    let sourceChatUsername = null;

    if (sourceChatInput.startsWith('@')) {
        sourceChatUsername = sourceChatInput.substring(1);
    } else {
        try {
            sourceChatId = parseInt(sourceChatInput);
        } catch (e) {
            alert('无效的频道 ID 格式');
            return;
        }
    }

    // 解析关键词
    const filterKeywords = filterKeywordsInput
        ? filterKeywordsInput.split(',').map(k => k.trim()).filter(k => k)
        : [];

    // 构建请求数据
    const requestData = {
        task_name: taskName,
        source_chat_id: sourceChatId,
        source_chat_username: sourceChatUsername,
        filter_type: filterType,
        filter_keywords: filterKeywords
    };

    // 如果不是全频道搬运，且有时间范围，则添加时间过滤
    if (!transferAllHistory) {
        if (filterDateFrom) {
            // 只发送日期，格式：YYYY-MM-DD
            requestData.filter_date_from = filterDateFrom;
        }
        if (filterDateTo) {
            // 只发送日期，格式：YYYY-MM-DD
            requestData.filter_date_to = filterDateTo;
        }
    }

    try {
        await apiRequest('/api/tasks', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });

        closeCreateTaskModal();
        loadTasksData();
        alert('任务已创建，等待执行');
    } catch (error) {
        console.error('创建任务失败:', error);
        alert('创建任务失败: ' + (error.message || '未知错误'));
    }
}

// 审核任务
async function approveTask(taskId) {
    document.getElementById('approveTaskId').value = taskId;
    document.getElementById('approveTaskModal').style.display = 'block';
    document.getElementById('approveTaskForm').reset();
}

// 关闭审核任务模态框
function closeApproveTaskModal() {
    document.getElementById('approveTaskModal').style.display = 'none';
}

// 处理审核任务表单提交
async function handleApproveTaskSubmit(e) {
    e.preventDefault();

    const taskId = document.getElementById('approveTaskId').value;
    const name = document.getElementById('approveName').value;
    const description = document.getElementById('approveDescription').value;
    const tags = document.getElementById('approveTags').value.split(',').map(t => t.trim()).filter(t => t);
    const access_level = document.getElementById('approveAccessLevel').value;

    try {
        const data = await apiRequest(`/api/tasks/${taskId}/approve`, {
            method: 'POST',
            body: JSON.stringify({ name, description, tags, access_level })
        });

        closeApproveTaskModal();
        loadTasksData();
        alert('合集创建成功！');
    } catch (error) {
        console.error('审核失败:', error);
        alert('审核失败: ' + (error.message || '未知错误'));
    }
}

// 删除任务
async function deleteTask(taskId, taskName) {
    if (!confirm(`确定要删除任务 "${taskName}" 吗？`)) {
        return;
    }

    try {
        await apiRequest(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });

        loadTasksData();
        alert('任务已删除');
    } catch (error) {
        console.error('删除失败:', error);
        alert('删除失败');
    }
}

// 用户管理相关变量
let currentUsersPage = 1;
let usersSearchText = '';
let usersRoleFilter = '';

async function loadUsers(page = 1) {
    currentUsersPage = page;

    try {
        const params = new URLSearchParams({
            page: page,
            limit: 20
        });

        if (usersSearchText) {
            params.append('search', usersSearchText);
        }

        if (usersRoleFilter) {
            params.append('role', usersRoleFilter);
        }

        const response = await fetch(`/api/users?${params}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) throw new Error('获取用户列表失败');

        const data = await response.json();
        renderUsersPage(data);
    } catch (error) {
        console.error('加载用户列表失败:', error);
        document.getElementById('pageContent').innerHTML = '<h2>👥 用户管理</h2><p>加载失败，请重试</p>';
    }
}

function renderUsersPage(data) {
    const totalPages = Math.ceil(data.total / 20);

    const html = `
        <div class="page-header">
            <h2>👥 用户管理</h2>
            <div class="header-actions">
                <span class="total-count">共 ${data.total} 个用户</span>
            </div>
        </div>

        <div class="filters">
            <input type="text" id="usersSearch" placeholder="搜索用户名..." value="${usersSearchText}">
            <select id="usersRoleFilter">
                <option value="">所有角色</option>
                <option value="USER" ${usersRoleFilter === 'USER' ? 'selected' : ''}>普通用户</option>
                <option value="VIP" ${usersRoleFilter === 'VIP' ? 'selected' : ''}>VIP</option>
                <option value="ADMIN" ${usersRoleFilter === 'ADMIN' ? 'selected' : ''}>管理员</option>
                <option value="SUPER_ADMIN" ${usersRoleFilter === 'SUPER_ADMIN' ? 'selected' : ''}>超级管理员</option>
            </select>
            <button onclick="applyUsersFilters()">搜索</button>
            <button onclick="resetUsersFilters()">重置</button>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Telegram ID</th>
                    <th>用户名</th>
                    <th>姓名</th>
                    <th>角色</th>
                    <th>状态</th>
                    <th>最后活跃</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                ${data.users.map(user => `
                    <tr>
                        <td>${user.telegram_id}</td>
                        <td>${user.username || '-'}</td>
                        <td>${user.first_name || ''} ${user.last_name || ''}</td>
                        <td><span class="role-badge role-${user.role.toLowerCase()}">${getRoleDisplayName(user.role)}</span></td>
                        <td><span class="status-badge ${user.is_banned ? 'status-banned' : 'status-active'}">${user.is_banned ? '已封禁' : '正常'}</span></td>
                        <td>${formatDateTime(user.last_active_at)}</td>
                        <td>
                            <button class="btn-small" onclick="viewUserDetail(${user.id})">详情</button>
                            ${user.role !== 'SUPER_ADMIN' ? `
                                <button class="btn-small" onclick="showEditRoleModal(${user.id}, '${user.role}')">修改角色</button>
                            ` : ''}
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>

        ${totalPages > 1 ? `
            <div class="pagination">
                <button onclick="loadUsers(${currentUsersPage - 1})" ${currentUsersPage === 1 ? 'disabled' : ''}>上一页</button>
                <span>第 ${currentUsersPage} / ${totalPages} 页</span>
                <button onclick="loadUsers(${currentUsersPage + 1})" ${currentUsersPage === totalPages ? 'disabled' : ''}>下一页</button>
            </div>
        ` : ''}

        <!-- 用户详情模态框 -->
        <div id="userDetailModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeUserDetailModal()">&times;</span>
                <h3>用户详情</h3>
                <div id="userDetailContent"></div>
            </div>
        </div>

        <!-- 修改角色模态框 -->
        <div id="editRoleModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeEditRoleModal()">&times;</span>
                <h3>修改用户角色</h3>
                <div id="editRoleContent"></div>
            </div>
        </div>
    `;

    document.getElementById('pageContent').innerHTML = html;
}

function getRoleDisplayName(role) {
    const roleNames = {
        'USER': '普通用户',
        'VIP': 'VIP',
        'ADMIN': '管理员',
        'SUPER_ADMIN': '超级管理员'
    };
    return roleNames[role] || role;
}

function applyUsersFilters() {
    usersSearchText = document.getElementById('usersSearch').value.trim();
    usersRoleFilter = document.getElementById('usersRoleFilter').value;
    loadUsers(1);
}

function resetUsersFilters() {
    usersSearchText = '';
    usersRoleFilter = '';
    document.getElementById('usersSearch').value = '';
    document.getElementById('usersRoleFilter').value = '';
    loadUsers(1);
}

async function viewUserDetail(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) throw new Error('获取用户详情失败');

        const data = await response.json();

        const html = `
            <div class="user-detail">
                <div class="detail-section">
                    <h4>基本信息</h4>
                    <p><strong>Telegram ID:</strong> ${data.telegram_id}</p>
                    <p><strong>用户名:</strong> ${data.username || '-'}</p>
                    <p><strong>姓名:</strong> ${data.first_name || ''} ${data.last_name || ''}</p>
                    <p><strong>角色:</strong> <span class="role-badge role-${data.role.toLowerCase()}">${getRoleDisplayName(data.role)}</span></p>
                    <p><strong>状态:</strong> <span class="status-badge ${data.is_banned ? 'status-banned' : 'status-active'}">${data.is_banned ? '已封禁' : '正常'}</span></p>
                    <p><strong>注册时间:</strong> ${formatDateTime(data.created_at)}</p>
                    <p><strong>最后活跃:</strong> ${formatDateTime(data.last_active_at)}</p>
                </div>

                <div class="detail-section">
                    <h4>使用统计</h4>
                    <p><strong>创建合集数:</strong> ${data.statistics.collections_created}</p>
                    <p><strong>创建搬运任务数:</strong> ${data.statistics.transfer_tasks_created}</p>
                    <p><strong>上传媒体总数:</strong> ${data.statistics.total_media_uploaded}</p>
                </div>

                <div class="modal-actions">
                    <button onclick="closeUserDetailModal()">关闭</button>
                </div>
            </div>
        `;

        document.getElementById('userDetailContent').innerHTML = html;
        document.getElementById('userDetailModal').style.display = 'block';
    } catch (error) {
        console.error('加载用户详情失败:', error);
        alert('加载用户详情失败');
    }
}

function closeUserDetailModal() {
    document.getElementById('userDetailModal').style.display = 'none';
}

function showEditRoleModal(userId, currentRole) {
    const html = `
        <form onsubmit="updateUserRole(event, ${userId})">
            <div class="form-group">
                <label>当前角色: <span class="role-badge role-${currentRole.toLowerCase()}">${getRoleDisplayName(currentRole.toUpperCase())}</span></label>
            </div>
            <div class="form-group">
                <label for="newRole">新角色:</label>
                <select id="newRole" required>
                    <option value="user" ${currentRole === 'user' ? 'selected' : ''}>普通用户</option>
                    <option value="vip" ${currentRole === 'vip' ? 'selected' : ''}>VIP</option>
                    <option value="admin" ${currentRole === 'admin' ? 'selected' : ''}>管理员</option>
                </select>
                <small>注意: 普通管理员只能设置为普通用户或VIP</small>
            </div>
            <div class="modal-actions">
                <button type="submit">确认修改</button>
                <button type="button" onclick="closeEditRoleModal()">取消</button>
            </div>
        </form>
    `;

    document.getElementById('editRoleContent').innerHTML = html;
    document.getElementById('editRoleModal').style.display = 'block';
}

function closeEditRoleModal() {
    document.getElementById('editRoleModal').style.display = 'none';
}

async function updateUserRole(event, userId) {
    event.preventDefault();

    const newRole = document.getElementById('newRole').value;

    try {
        const response = await fetch(`/api/users/${userId}/role`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ role: newRole })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '修改角色失败');
        }

        alert('角色修改成功');
        closeEditRoleModal();
        loadUsers(currentUsersPage);
    } catch (error) {
        console.error('修改角色失败:', error);
        alert(error.message);
    }
}

// 批量VIP管理页面
async function loadBatchVIP() {
    const html = `
        <div class="page-header">
            <h2>💎 批量VIP管理</h2>
        </div>

        <div class="batch-vip-container">
            <div class="form-section">
                <h3>批量设置VIP</h3>
                <p style="color: #666; margin-bottom: 15px;">请输入Telegram ID，每行一个</p>
                <textarea id="batchVipIds" rows="10" placeholder="123456789&#10;987654321&#10;111222333" style="width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 6px; font-family: monospace;"></textarea>

                <div style="margin-top: 15px; display: flex; gap: 10px;">
                    <button onclick="executeBatchVIP('grant')" style="flex: 1; padding: 12px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px;">
                        ✅ 授予VIP
                    </button>
                    <button onclick="executeBatchVIP('revoke')" style="flex: 1; padding: 12px; background: #f44336; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px;">
                        ❌ 撤销VIP
                    </button>
                </div>
            </div>

            <div id="batchVipResult" style="margin-top: 30px;"></div>
        </div>
    `;

    document.getElementById('pageContent').innerHTML = html;
}

async function executeBatchVIP(action) {
    const idsText = document.getElementById('batchVipIds').value.trim();

    if (!idsText) {
        alert('请输入Telegram ID');
        return;
    }

    // 解析ID列表
    const telegram_ids = idsText
        .split('\n')
        .map(line => line.trim())
        .filter(line => line && /^\d+$/.test(line))
        .map(id => parseInt(id));

    if (telegram_ids.length === 0) {
        alert('没有有效的Telegram ID');
        return;
    }

    if (!confirm(`确定要${action === 'grant' ? '授予' : '撤销'} ${telegram_ids.length} 个用户的VIP权限吗？`)) {
        return;
    }

    try {
        const response = await fetch('/api/users/batch-vip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                telegram_ids: telegram_ids,
                action: action
            })
        });

        if (!response.ok) {
            let errorMessage = '操作失败';
            try {
                const error = await response.json();
                errorMessage = error.detail || errorMessage;
            } catch (e) {
                // 如果响应不是JSON，使用状态文本
                errorMessage = `${response.status} ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }

        const data = await response.json();

        // 显示结果
        let resultHtml = `
            <div style="background: #e8f5e9; padding: 20px; border-radius: 8px; border-left: 4px solid #4caf50;">
                <h3 style="color: #2e7d32; margin-bottom: 10px;">✅ ${data.message}</h3>
                <div style="color: #666;">
                    <p>总数: ${data.details.total}</p>
                    <p>成功: ${data.details.success_count}</p>
                    <p>失败: ${data.details.failed_count}</p>
                    ${data.details.failed_ids.length > 0 ? `
                        <p style="margin-top: 10px;">失败的ID: ${data.details.failed_ids.join(', ')}</p>
                    ` : ''}
                </div>
            </div>
        `;

        document.getElementById('batchVipResult').innerHTML = resultHtml;

        // 清空输入框
        document.getElementById('batchVipIds').value = '';

    } catch (error) {
        console.error('批量VIP操作失败:', error);
        document.getElementById('batchVipResult').innerHTML = `
            <div style="background: #ffebee; padding: 20px; border-radius: 8px; border-left: 4px solid #f44336;">
                <h3 style="color: #c62828; margin-bottom: 10px;">❌ 操作失败</h3>
                <p style="color: #666;">${error.message}</p>
            </div>
        `;
    }
}

// 用户统计页面
async function loadUserStats() {
    document.getElementById('pageContent').innerHTML = '<h2>📊 用户统计</h2><p>加载中...</p>';

    try {
        const response = await fetch('/api/users/statistics', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) throw new Error('获取统计数据失败');

        const data = await response.json();

        const html = `
            <div class="page-header">
                <h2>📊 用户统计分析</h2>
            </div>

            <!-- 概览卡片 -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px;">
                    <h3 style="font-size: 14px; margin-bottom: 10px;">总用户数</h3>
                    <p style="font-size: 32px; font-weight: bold;">${data.total_users}</p>
                </div>
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 8px;">
                    <h3 style="font-size: 14px; margin-bottom: 10px;">日活跃用户</h3>
                    <p style="font-size: 32px; font-weight: bold;">${data.active_users.daily}</p>
                </div>
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 8px;">
                    <h3 style="font-size: 14px; margin-bottom: 10px;">周活跃用户</h3>
                    <p style="font-size: 32px; font-weight: bold;">${data.active_users.weekly}</p>
                </div>
                <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; padding: 20px; border-radius: 8px;">
                    <h3 style="font-size: 14px; margin-bottom: 10px;">月活跃用户</h3>
                    <p style="font-size: 32px; font-weight: bold;">${data.active_users.monthly}</p>
                </div>
            </div>

            <!-- 角色分布 -->
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin-bottom: 15px;">角色分布</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                    ${Object.entries(data.role_distribution).map(([role, count]) => `
                        <div style="text-align: center; padding: 15px; background: #f5f5f5; border-radius: 6px;">
                            <div style="font-size: 24px; font-weight: bold; color: #667eea;">${count}</div>
                            <div style="color: #666; margin-top: 5px;">${getRoleDisplayName(role.toUpperCase())}</div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- 增长趋势 - 最近7天 -->
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin-bottom: 15px;">用户增长趋势（最近7天）</h3>
                <table style="width: 100%;">
                    <thead>
                        <tr>
                            <th style="text-align: left; padding: 10px; background: #f5f5f5;">日期</th>
                            <th style="text-align: right; padding: 10px; background: #f5f5f5;">新增用户</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.growth_trend.last_7_days.map(item => `
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #e0e0e0;">${item.date}</td>
                                <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; text-align: right; font-weight: bold; color: #667eea;">${item.new_users}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>

            <!-- 其他统计 -->
            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin-bottom: 15px;">其他统计</h3>
                <p style="color: #666; margin-bottom: 10px;">封禁用户数: <strong style="color: #f44336;">${data.banned_users}</strong></p>
                <p style="color: #666;">活跃率（日/总）: <strong style="color: #667eea;">${((data.active_users.daily / data.total_users) * 100).toFixed(2)}%</strong></p>
            </div>
        `;

        document.getElementById('pageContent').innerHTML = html;

    } catch (error) {
        console.error('加载统计数据失败:', error);
        document.getElementById('pageContent').innerHTML = '<h2>📊 用户统计</h2><p style="color: red;">加载失败，请重试</p>';
    }
}

function loadSettings() {
    document.getElementById('pageContent').innerHTML = '<h2>⚙️ 系统设置</h2><p>功能开发中...</p>';
}

// 复制深链接（简化版，直接复制传入的链接）
function copyDeepLinkDirect(deepLink) {
    // 使用兼容性更好的复制方法
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(deepLink).then(() => {
            alert('深链接已复制到剪贴板');
        }).catch(err => {
            fallbackCopy(deepLink);
        });
    } else {
        fallbackCopy(deepLink);
    }
}

// 降级复制方法
function fallbackCopy(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand('copy');
        textArea.remove();
        alert('深链接已复制到剪贴板');
    } catch (err) {
        textArea.remove();
        prompt('请手动复制以下深链接:', text);
    }
}

// 复制深链接（旧版本，保留用于其他地方可能的调用）
async function copyDeepLink(code) {
    try {
        const data = await apiRequest('/api/settings');
        console.log('Settings API response:', data);
        const botUsername = data.BOT_USERNAME || 'your_bot';
        const deepLink = `https://t.me/${botUsername}?start=${code}`;

        // 使用兼容性更好的复制方法
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(deepLink);
            alert('深链接已复制到剪贴板:\n' + deepLink);
        } else {
            // 降级方案：使用传统的 execCommand 方法
            const textArea = document.createElement('textarea');
            textArea.value = deepLink;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                textArea.remove();
                alert('深链接已复制到剪贴板:\n' + deepLink);
            } catch (err) {
                textArea.remove();
                // 最后的降级方案：显示链接让用户手动复制
                prompt('请手动复制以下深链接:', deepLink);
            }
        }
    } catch (error) {
        console.error('复制失败:', error);
        alert('复制失败: ' + error.message);
    }
}

// 页面路由
const routes = {
    'dashboard': loadDashboard,
    'collections': loadCollections,
    'tasks': loadTasks,
    'sessions': loadSessions,
    'users': loadUsers,
    'user-stats': loadUserStats,
    'batch-vip': loadBatchVIP,
    'settings': loadSettings
};

// 初始化函数
function init() {
    // 导航切换
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            const page = item.dataset.page;

            // 只有当链接有 data-page 属性且对应路由存在时，才阻止默认行为并动态加载
            if (page && routes[page]) {
                e.preventDefault();

                // 更新导航状态
                document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');

                // 加载对应页面
                routes[page]();
            }
        });
    });

    // 退出登录
    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
    });

    // 检查认证并加载数据
    if (checkAuth()) {
        loadUserInfo();
        loadDashboard();
    }
}

// 等待 DOM 加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
