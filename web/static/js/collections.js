// collections.js - 合集管理页面

const API_BASE = '/api';
let currentPage = 1;
let currentLimit = 20;
let currentSearch = '';
let currentAccessFilter = '';
let selectedCollections = new Set();

// 页面加载
document.addEventListener('DOMContentLoaded', () => {
    loadCollections();
    setupEventListeners();
});

// 设置事件监听
function setupEventListeners() {
    // 搜索
    document.getElementById('searchInput').addEventListener('input', debounce((e) => {
        currentSearch = e.target.value;
        currentPage = 1;
        loadCollections();
    }, 500));

    // 权限筛选
    document.getElementById('accessFilter').addEventListener('change', (e) => {
        currentAccessFilter = e.target.value;
        currentPage = 1;
        loadCollections();
    });

    // 全选
    document.getElementById('selectAll').addEventListener('change', (e) => {
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

    // 批量删除
    document.getElementById('batchDeleteBtn').addEventListener('click', batchDelete);

    // 编辑表单提交
    document.getElementById('editForm').addEventListener('submit', handleEditSubmit);
}

// 加载合集列表
async function loadCollections() {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = '/';
            return;
        }

        const params = new URLSearchParams({
            page: currentPage,
            limit: currentLimit
        });

        if (currentSearch) params.append('search', currentSearch);
        if (currentAccessFilter) params.append('access_level', currentAccessFilter);

        const response = await fetch(`${API_BASE}/collections?${params}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/';
            return;
        }

        if (!response.ok) {
            throw new Error('加载失败');
        }

        const data = await response.json();
        renderCollections(data.collections);
        renderPagination(data.total, data.page, data.limit);
    } catch (error) {
        console.error('加载合集失败:', error);
        showError('加载合集失败');
    }
}

// 渲染合集列表
function renderCollections(collections) {
    const tbody = document.getElementById('collectionsTable');

    if (collections.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = collections.map(collection => `
        <tr>
            <td>
                <input type="checkbox" class="collection-checkbox"
                       data-id="${collection.id}"
                       ${selectedCollections.has(collection.id) ? 'checked' : ''}
                       onchange="handleCheckboxChange(${collection.id}, this.checked)">
            </td>
            <td>${escapeHtml(collection.name)}</td>
            <td>${escapeHtml(collection.description || '-')}</td>
            <td>${collection.media_count}</td>
            <td>
                <span class="badge badge-${collection.access_level === 'public' ? 'success' : 'warning'}">
                    ${collection.access_level === 'public' ? '公开' : 'VIP'}
                </span>
            </td>
            <td>${formatDate(collection.created_at)}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editCollection(${collection.id})">编辑</button>
                <button class="btn btn-sm btn-danger" onclick="deleteCollection(${collection.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

// 渲染分页
function renderPagination(total, page, limit) {
    const totalPages = Math.ceil(total / limit);
    const pagination = document.getElementById('pagination');

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '<div class="pagination-controls">';

    // 上一页
    if (page > 1) {
        html += `<button onclick="changePage(${page - 1})">上一页</button>`;
    }

    // 页码
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
            html += `<button class="${i === page ? 'active' : ''}" onclick="changePage(${i})">${i}</button>`;
        } else if (i === page - 3 || i === page + 3) {
            html += '<span>...</span>';
        }
    }

    // 下一页
    if (page < totalPages) {
        html += `<button onclick="changePage(${page + 1})">下一页</button>`;
    }

    html += '</div>';
    pagination.innerHTML = html;
}

// 切换页码
function changePage(page) {
    currentPage = page;
    loadCollections();
}

// 处理复选框变化
function handleCheckboxChange(id, checked) {
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
    if (selectedCollections.size > 0) {
        btn.style.display = 'inline-block';
        btn.textContent = `批量删除 (${selectedCollections.size})`;
    } else {
        btn.style.display = 'none';
    }
}

// 编辑合集
async function editCollection(id) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/collections/${id}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('获取合集信息失败');
        }

        const collection = await response.json();

        // 填充表单
        document.getElementById('editCollectionId').value = collection.id;
        document.getElementById('editName').value = collection.name;
        document.getElementById('editDescription').value = collection.description || '';
        document.getElementById('editTags').value = collection.tags ? collection.tags.join(', ') : '';
        document.getElementById('editAccessLevel').value = collection.access_level;

        // 显示模态框
        document.getElementById('editModal').style.display = 'block';
    } catch (error) {
        console.error('加载合集信息失败:', error);
        showError('加载合集信息失败');
    }
}

// 关闭编辑模态框
function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

// 处理编辑表单提交
async function handleEditSubmit(e) {
    e.preventDefault();

    const id = document.getElementById('editCollectionId').value;
    const name = document.getElementById('editName').value.trim();
    const description = document.getElementById('editDescription').value.trim();
    const tagsStr = document.getElementById('editTags').value.trim();
    const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(t => t) : [];
    const accessLevel = document.getElementById('editAccessLevel').value;

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/collections/${id}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                description,
                tags,
                access_level: accessLevel
            })
        });

        if (!response.ok) {
            throw new Error('更新失败');
        }

        showSuccess('更新成功');
        closeEditModal();
        loadCollections();
    } catch (error) {
        console.error('更新合集失败:', error);
        showError('更新合集失败');
    }
}

// 删除合集
async function deleteCollection(id) {
    if (!confirm('确定要删除这个合集吗？此操作不可恢复！')) {
        return;
    }

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/collections/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('删除失败');
        }

        showSuccess('删除成功');
        selectedCollections.delete(id);
        updateBatchDeleteButton();
        loadCollections();
    } catch (error) {
        console.error('删除合集失败:', error);
        showError('删除合集失败');
    }
}

// 批量删除
async function batchDelete() {
    if (selectedCollections.size === 0) {
        return;
    }

    if (!confirm(`确定要删除选中的 ${selectedCollections.size} 个合集吗？此操作不可恢复！`)) {
        return;
    }

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/collections/batch-delete`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                collection_ids: Array.from(selectedCollections)
            })
        });

        if (!response.ok) {
            throw new Error('批量删除失败');
        }

        const result = await response.json();
        showSuccess(result.message);
        selectedCollections.clear();
        updateBatchDeleteButton();
        document.getElementById('selectAll').checked = false;
        loadCollections();
    } catch (error) {
        console.error('批量删除失败:', error);
        showError('批量删除失败');
    }
}

// 工具函数
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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

function showSuccess(message) {
    alert(message);
}

function showError(message) {
    alert(message);
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/';
}
