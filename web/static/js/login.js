// 登录页面 JavaScript
const API_BASE = window.location.origin;

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const telegramId = document.getElementById('telegram_id').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                telegram_id: parseInt(telegramId),
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            // 保存 token
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));

            // 跳转到仪表盘
            window.location.href = '/dashboard';
        } else {
            alert(data.detail || '登录失败，请检查您的凭据');
        }
    } catch (error) {
        console.error('登录错误:', error);
        alert('登录失败，请稍后重试');
    }
});
