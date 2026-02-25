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

    return response.json();
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
                        <th style="padding: 12px; text-align: left;">创建时间</th>
                        <th style="padding: 12px; text-align: left; width: 200px;">操作</th>
                    </tr>
                </thead>
                <tbody id="collectionsTable">
                    <tr><td colspan="7" style="padding: 20px; text-align: center;">加载中...</td></tr>
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
        document.getElementById('collectionsTable').innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: red;">加载失败</td></tr>';
    }
}

// 渲染合集表格
function renderCollectionsTable(collections) {
    const tbody = document.getElementById('collectionsTable');

    if (collections.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: #999;">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = collections.map(col => {
        const escapedName = col.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        return `
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 12px;">
                <input type="checkbox" class="collection-checkbox" data-id="${col.id}" onchange="handleCollectionCheckbox(${col.id}, this.checked)">
            </td>
            <td style="padding: 12px;">${col.name}</td>
            <td style="padding: 12px;">${col.description || '-'}</td>
            <td style="padding: 12px;">${col.media_count}</td>
            <td style="padding: 12px;">${col.access_level === 'public' ? '公开' : 'VIP'}</td>
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
    document.getElementById('pageContent').innerHTML = '<h2>🔄 搬运任务</h2><p>功能开发中...</p>';
}

function loadSessions() {
    document.getElementById('pageContent').innerHTML = '<h2>🔑 Session 管理</h2><p>功能开发中...</p>';
}

function loadUsers() {
    document.getElementById('pageContent').innerHTML = '<h2>👥 用户管理</h2><p>功能开发中...</p>';
}

function loadSettings() {
    document.getElementById('pageContent').innerHTML = '<h2>⚙️ 系统设置</h2><p>功能开发中...</p>';
}

// 页面路由
const routes = {
    'dashboard': loadDashboard,
    'collections': loadCollections,
    'tasks': loadTasks,
    'sessions': loadSessions,
    'users': loadUsers,
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
