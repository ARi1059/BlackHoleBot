# BlackHoleBot 第三阶段测试指南

## 快速开始

第三阶段（用户活动跟踪和分析系统）已完成开发，现在可以开始测试。

---

## 📋 测试前准备

### 1. 确认环境

确保以下服务正在运行：

```bash
# 检查 PostgreSQL
sudo systemctl status postgresql

# 检查 Redis
sudo systemctl status redis

# 检查应用是否运行
ps aux | grep python | grep main.py
```

### 2. 导入测试数据（可选）

如果需要测试数据：

```bash
# 导入测试数据
psql -U blackholebot_user -h localhost -d blackholebot -f docs/test_data.sql
```

这将创建：
- 3 个测试用户（普通用户、VIP、管理员）
- 5 个测试合集
- 200+ 条用户活动记录
- 50 条管理员日志

---

## 🚀 快速测试

### 方法 1: 使用自动化测试脚本

```bash
# 1. 在 Telegram Bot 中发送 /login 命令获取验证码

# 2. 运行测试脚本（会提示输入验证码）
bash docs/quick_test.sh
```

测试脚本会自动执行：
- ✅ 获取管理员 Token
- ✅ 测试热门合集 API
- ✅ 测试用户活动 API
- ✅ 测试用户统计 API
- ✅ 测试搜索功能
- ✅ 验证数据库数据

---

### 方法 2: 手动测试

#### 步骤 1: 获取管理员 Token

**重要**: 登录需要验证码，请先在 Telegram Bot 中获取

```bash
# 1. 在 Telegram Bot 中发送 /login 命令
# 2. Bot 会返回一个 6 位验证码
# 3. 使用验证码登录

# 替换 YOUR_ADMIN_TELEGRAM_ID 和 YOUR_CODE
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": YOUR_ADMIN_TELEGRAM_ID, "password": "YOUR_CODE"}' \
  | jq -r '.access_token'

# 保存返回的 token
export TOKEN="your_token_here"
```

#### 步骤 2: 测试热门合集分析

```bash
# 获取热门合集（默认参数）
curl -X GET "http://localhost:8000/api/analytics/popular-collections" \
  -H "Authorization: Bearer $TOKEN" | jq

# 获取最近 7 天的热门合集
curl -X GET "http://localhost:8000/api/analytics/popular-collections?days=7&limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**预期结果**：
```json
{
  "collections": [
    {
      "collection_id": 1,
      "collection_name": "热门合集",
      "view_count": 45,
      "media_count": 10,
      "access_level": "public"
    }
  ]
}
```

#### 步骤 3: 测试用户活动记录

```bash
# 获取用户活动记录（替换 USER_ID）
curl -X GET "http://localhost:8000/api/analytics/users/1/activities?limit=20" \
  -H "Authorization: Bearer $TOKEN" | jq

# 只获取搜索活动
curl -X GET "http://localhost:8000/api/analytics/users/1/activities?activity_type=search" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**预期结果**：
```json
{
  "activities": [
    {
      "id": 1,
      "user_id": 1,
      "activity_type": "view_collection",
      "collection_id": 3,
      "extra_data": null,
      "created_at": "2026-02-27T10:30:00"
    }
  ],
  "total": 45
}
```

#### 步骤 4: 测试用户行为统计

```bash
# 获取用户活动统计
curl -X GET "http://localhost:8000/api/analytics/users/1/stats" \
  -H "Authorization: Bearer $TOKEN" | jq

# 获取最近 7 天的统计
curl -X GET "http://localhost:8000/api/analytics/users/1/stats?days=7" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**预期结果**：
```json
{
  "user_id": 1,
  "total_activities": 45,
  "activities_by_type": {
    "view_collection": 30,
    "search": 10,
    "download": 5
  },
  "top_collections": [
    {
      "collection_id": 3,
      "collection_name": "热门合集",
      "view_count": 15
    }
  ]
}
```

#### 步骤 5: 测试用户统计分析

```bash
# 获取全局用户统计
curl -X GET "http://localhost:8000/api/users/statistics" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**预期结果**：
```json
{
  "total_users": 100,
  "users_by_role": {
    "user": 85,
    "vip": 10,
    "admin": 4,
    "super_admin": 1
  },
  "active_users": {
    "daily": 25,
    "weekly": 60,
    "monthly": 90
  },
  "user_growth": {
    "last_7_days": 5,
    "last_30_days": 15
  }
}
```

---

## 🔍 数据库验证

### 检查数据完整性

```bash
# 连接数据库
psql -U blackholebot_user -h localhost -d blackholebot
```

```sql
-- 1. 检查 user_activities 表
SELECT COUNT(*) as 活动记录总数 FROM user_activities;

-- 2. 检查活动类型分布
SELECT activity_type, COUNT(*) as 数量
FROM user_activities
GROUP BY activity_type;

-- 3. 检查热门合集
SELECT
    c.name as 合集名称,
    COUNT(ua.id) as 访问次数
FROM collections c
LEFT JOIN user_activities ua ON c.id = ua.collection_id
    AND ua.activity_type = 'view_collection'
GROUP BY c.id, c.name
ORDER BY COUNT(ua.id) DESC
LIMIT 10;

-- 4. 检查用户活动统计
SELECT
    u.username as 用户名,
    COUNT(ua.id) as 总活动数
FROM users u
LEFT JOIN user_activities ua ON u.id = ua.user_id
GROUP BY u.id, u.username
ORDER BY COUNT(ua.id) DESC
LIMIT 10;

-- 5. 检查管理员日志
SELECT action, COUNT(*) as 数量
FROM admin_logs
GROUP BY action;

-- 6. 检查索引
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'user_activities';
```

---

## 🎯 功能测试清单

### 核心功能

- [ ] **用户活动跟踪**
  - [ ] 浏览合集时创建活动记录
  - [ ] 搜索时创建活动记录
  - [ ] 下载时创建活动记录
  - [ ] 活动记录包含正确的时间戳

- [ ] **热门合集分析**
  - [ ] 按访问次数正确排序
  - [ ] 时间范围过滤正常工作
  - [ ] 返回正确的统计数据

- [ ] **用户行为统计**
  - [ ] 总活动数计算正确
  - [ ] 活动类型分组正确
  - [ ] 热门合集排序正确

- [ ] **用户统计分析**
  - [ ] 角色分布统计正确
  - [ ] 活跃用户统计正确
  - [ ] 用户增长趋势正确

- [ ] **权限控制**
  - [ ] 未登录用户无法访问
  - [ ] 普通用户无法访问
  - [ ] 管理员可以访问
  - [ ] 超级管理员可以访问

---

## 📊 性能测试

### 测试查询性能

```sql
-- 测试用户活动查询性能
EXPLAIN ANALYZE
SELECT * FROM user_activities
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 20;

-- 测试热门合集查询性能
EXPLAIN ANALYZE
SELECT
    c.id,
    c.name,
    COUNT(ua.id) as view_count
FROM collections c
LEFT JOIN user_activities ua ON c.id = ua.collection_id
    AND ua.activity_type = 'view_collection'
    AND ua.created_at >= NOW() - INTERVAL '7 days'
GROUP BY c.id, c.name
ORDER BY view_count DESC
LIMIT 10;
```

**性能指标**：
- 查询时间应 < 100ms
- 索引应被正确使用

---

## 🐛 常见问题

### 1. Token 获取失败

**问题**: 无法获取管理员 Token

**解决方案**:
```bash
# 检查用户角色
psql -U blackholebot_user -h localhost -d blackholebot -c \
  "SELECT telegram_id, username, role FROM users WHERE telegram_id = YOUR_ID;"

# 如果不是管理员，更新角色
psql -U blackholebot_user -h localhost -d blackholebot -c \
  "UPDATE users SET role = 'admin' WHERE telegram_id = YOUR_ID;"
```

### 2. API 返回 403 错误

**问题**: 有 Token 但仍然返回 403

**原因**: 用户角色不是 admin 或 super_admin

**解决方案**: 参考问题 1

### 3. 没有活动数据

**问题**: API 返回空数据

**解决方案**:
```bash
# 导入测试数据
psql -U blackholebot_user -h localhost -d blackholebot -f docs/test_data.sql
```

### 4. 数据库连接失败

**问题**: psql 命令失败

**解决方案**:
```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 检查连接
psql -U blackholebot_user -h localhost -d blackholebot -c "SELECT 1;"
```

---

## 📝 测试报告

测试完成后，请记录以下信息：

### 功能测试结果

| 功能 | 状态 | 备注 |
|------|------|------|
| 用户活动跟踪 | ☐ 通过 ☐ 失败 | |
| 热门合集分析 | ☐ 通过 ☐ 失败 | |
| 用户行为统计 | ☐ 通过 ☐ 失败 | |
| 用户统计分析 | ☐ 通过 ☐ 失败 | |
| 权限控制 | ☐ 通过 ☐ 失败 | |

### 性能测试结果

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| API 响应时间 | < 200ms | ___ ms | ☐ 通过 ☐ 失败 |
| 数据库查询时间 | < 100ms | ___ ms | ☐ 通过 ☐ 失败 |

### 发现的问题

1.
2.
3.

---

## 📞 反馈

测试完成后，请提供以下反馈：

1. **功能完整性**: 所有功能是否按预期工作？
2. **性能表现**: 响应速度是否满意？
3. **用户体验**: 使用是否流畅？
4. **发现的 Bug**: 列出所有发现的问题
5. **改进建议**: 有什么可以改进的地方？

---

## 📚 相关文档

- [完整测试计划](phase3_test_plan.md) - 详细的测试用例和流程
- [API 文档](http://localhost:8000/docs) - FastAPI Swagger UI
- [数据库模型](../database/models.py) - 数据库表结构
- [CRUD 操作](../database/crud.py) - 数据库操作函数

---

**文档版本**: 1.0
**最后更新**: 2026-02-27
**状态**: 待测试
