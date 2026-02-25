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

// 加载合集管理
async function loadCollections() {
    const content = document.getElementById('pageContent');
    content.innerHTML = '<h2>📁 合集管理</h2><p>加载中...</p>';

    try {
        const data = await apiRequest('/api/collections?skip=0&limit=50');

        let html = '<h2>📁 合集管理</h2>';
        html += '<table style="width: 100%; border-collapse: collapse; margin-top: 20px;">';
        html += '<thead><tr style="background: #f5f5f5;"><th style="padding: 12px; text-align: left;">名称</th><th style="padding: 12px; text-align: left;">描述</th><th style="padding: 12px; text-align: left;">媒体数</th><th style="padding: 12px; text-align: left;">访问级别</th></tr></thead>';
        html += '<tbody>';

        if (data.items && data.items.length > 0) {
            data.items.forEach(item => {
                html += `<tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px;">${item.name}</td>
                    <td style="padding: 12px;">${item.description || '-'}</td>
                    <td style="padding: 12px;">${item.media_count}</td>
                    <td style="padding: 12px;">${item.access_level === 'public' ? '公开' : 'VIP'}</td>
                </tr>`;
            });
        } else {
            html += '<tr><td colspan="4" style="padding: 20px; text-align: center; color: #999;">暂无数据</td></tr>';
        }

        html += '</tbody></table>';
        content.innerHTML = html;
    } catch (error) {
        content.innerHTML = '<h2>📁 合集管理</h2><p style="color: red;">加载失败</p>';
        console.error('加载合集失败:', error);
    }
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
            // 否则让链接正常跳转（如 /collections）
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
