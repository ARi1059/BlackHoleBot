# BlackHoleBot 第三阶段测试计划

## 测试概述

**测试阶段**: Phase 3 - 用户活动跟踪和分析系统
**测试日期**: 2026-02-27
**测试环境**: 生产环境
**测试人员**: 待定

---

## 1. 用户活动跟踪系统测试

### 1.1 活动记录创建测试

**测试目标**: 验证用户活动能够正确记录

| 测试用例 | 操作步骤 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-001 | 用户浏览合集 | 创建 view_collection 活动记录 | P0 |
| TC-002 | 用户搜索合集 | 创建 search 活动记录，extra_data 包含搜索关键词 | P0 |
| TC-003 | 用户下载媒体 | 创建 download 活动记录 | P0 |
| TC-004 | 同一用户多次操作 | 每次操作都创建独立记录 | P1 |
| TC-005 | 并发用户操作 | 所有活动都正确记录，无数据丢失 | P1 |

**测试方法**:
```bash
# 1. 启动应用
python main.py

# 2. 在浏览器中执行操作
# 3. 检查数据库记录
psql -U blackholebot_user -h localhost -d blackholebot -c "SELECT * FROM user_activities ORDER BY created_at DESC LIMIT 10;"
```

---

### 1.2 活动查询测试

**测试目标**: 验证活动记录查询功能

| 测试用例 | API 端点 | 参数 | 预期结果 | 优先级 |
|---------|---------|------|---------|--------|
| TC-006 | GET /api/analytics/users/{user_id}/activities | user_id=1 | 返回该用户所有活动 | P0 |
| TC-007 | GET /api/analytics/users/{user_id}/activities | user_id=1, activity_type=search | 只返回搜索活动 | P1 |
| TC-008 | GET /api/analytics/users/{user_id}/activities | user_id=1, limit=5 | 返回最近 5 条活动 | P1 |
| TC-009 | GET /api/analytics/users/{user_id}/activities | user_id=999 (不存在) | 返回空列表 | P2 |
| TC-010 | GET /api/analytics/users/{user_id}/activities | 无权限用户访问 | 返回 403 错误 | P0 |

**测试脚本**:
```bash
# 获取 JWT token (管理员账号)
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": YOUR_ADMIN_ID}' | jq -r '.access_token')

# 测试活动查询
curl -X GET "http://localhost:8000/api/analytics/users/1/activities?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 2. 数据分析功能测试

### 2.1 热门合集分析测试

**测试目标**: 验证热门合集排序和统计

| 测试用例 | API 端点 | 参数 | 预期结果 | 优先级 |
|---------|---------|------|---------|--------|
| TC-011 | GET /api/analytics/popular-collections | limit=10 | 返回访问量最高的 10 个合集 | P0 |
| TC-012 | GET /api/analytics/popular-collections | days=7 | 只统计最近 7 天的访问 | P1 |
| TC-013 | GET /api/analytics/popular-collections | days=30 | 只统计最近 30 天的访问 | P1 |
| TC-014 | GET /api/analytics/popular-collections | limit=100 | 最多返回 50 个（参数验证） | P2 |
| TC-015 | GET /api/analytics/popular-collections | 无活动数据 | 返回空列表 | P2 |

**测试脚本**:
```bash
# 测试热门合集
curl -X GET "http://localhost:8000/api/analytics/popular-collections?limit=10&days=7" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 2.2 用户活动统计测试

**测试目标**: 验证用户行为统计计算

| 测试用例 | API 端点 | 参数 | 预期结果 | 优先级 |
|---------|---------|------|---------|--------|
| TC-016 | GET /api/analytics/users/{user_id}/stats | user_id=1 | 返回总活动数、活动类型分布、热门合集 | P0 |
| TC-017 | GET /api/analytics/users/{user_id}/stats | user_id=1, days=7 | 只统计最近 7 天 | P1 |
| TC-018 | GET /api/analytics/users/{user_id}/stats | user_id=1, days=30 | 只统计最近 30 天 | P1 |
| TC-019 | GET /api/analytics/users/{user_id}/stats | 新用户无活动 | 返回 0 统计数据 | P2 |

**验证点**:
- total_activities: 总活动数正确
- activities_by_type: 各类型活动数量正确
- top_collections: 最常访问的合集排序正确

---

### 2.3 用户统计分析测试

**测试目标**: 验证全局用户统计

| 测试用例 | API 端点 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-020 | GET /api/users/statistics | 返回角色分布统计 | P0 |
| TC-021 | GET /api/users/statistics | 返回活跃用户统计（日/周/月） | P0 |
| TC-022 | GET /api/users/statistics | 返回用户增长趋势 | P1 |
| TC-023 | GET /api/users/statistics | 数据准确性验证 | P0 |

**测试脚本**:
```bash
# 测试用户统计
curl -X GET "http://localhost:8000/api/users/statistics" \
  -H "Authorization: Bearer $TOKEN"
```

**手动验证**:
```sql
-- 验证角色分布
SELECT role, COUNT(*) FROM users GROUP BY role;

-- 验证日活用户
SELECT COUNT(DISTINCT user_id) FROM user_activities
WHERE created_at >= NOW() - INTERVAL '1 day';

-- 验证用户增长
SELECT COUNT(*) FROM users
WHERE created_at >= NOW() - INTERVAL '7 days';
```

---

## 3. 管理员日志系统测试

### 3.1 日志记录测试

**测试目标**: 验证管理员操作被正确记录

| 测试用例 | 操作 | 预期日志 | 优先级 |
|---------|------|---------|--------|
| TC-024 | 修改用户角色 | action=update_user_role, details 包含旧角色和新角色 | P0 |
| TC-025 | 封禁用户 | action=ban_user, details 包含用户 ID 和原因 | P0 |
| TC-026 | 解封用户 | action=unban_user, details 包含用户 ID | P0 |
| TC-027 | 批量操作 | action=batch_update_vip, details 包含操作数量 | P1 |
| TC-028 | 删除合集 | action=delete_collection, details 包含合集信息 | P1 |

**验证方法**:
```sql
-- 查看最近的管理员日志
SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT 20;

-- 查看特定操作的日志
SELECT * FROM admin_logs WHERE action = 'update_user_role';

-- 查看特定管理员的操作
SELECT * FROM admin_logs WHERE user_id = 1;
```

---

### 3.2 日志查询测试

**测试目标**: 验证日志查询功能（如果有 API）

| 测试用例 | 查询条件 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-029 | 按操作类型过滤 | 只返回指定类型的日志 | P1 |
| TC-030 | 按用户过滤 | 只返回指定用户的操作 | P1 |
| TC-031 | 按时间范围过滤 | 只返回指定时间段的日志 | P2 |
| TC-032 | 分页查询 | 正确返回分页数据 | P2 |

---

## 4. 高级搜索功能测试

### 4.1 合集搜索测试

**测试目标**: 验证合集搜索功能

| 测试用例 | 搜索条件 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-033 | 按名称搜索 | 返回名称匹配的合集 | P0 |
| TC-034 | 按描述搜索 | 返回描述匹配的合集 | P1 |
| TC-035 | 按标签搜索 | 返回标签匹配的合集 | P1 |
| TC-036 | 模糊搜索 | 支持部分匹配 | P1 |
| TC-037 | 权限过滤 | 普通用户只能搜索公开合集 | P0 |
| TC-038 | 空搜索 | 返回所有合集（带权限过滤） | P2 |

**测试脚本**:
```bash
# 搜索合集
curl -X GET "http://localhost:8000/api/collections?search=测试&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 4.2 用户搜索测试

**测试目标**: 验证用户搜索功能

| 测试用例 | 搜索条件 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-039 | 按用户名搜索 | 返回用户名匹配的用户 | P0 |
| TC-040 | 按名字搜索 | 返回名字匹配的用户 | P1 |
| TC-041 | 按角色过滤 | 只返回指定角色的用户 | P1 |
| TC-042 | 组合搜索 | 搜索+角色过滤同时生效 | P2 |

**测试脚本**:
```bash
# 搜索用户
curl -X GET "http://localhost:8000/api/users?search=test&role=vip&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 5. 性能测试

### 5.1 数据库性能测试

**测试目标**: 验证大数据量下的查询性能

| 测试用例 | 数据量 | 操作 | 性能指标 | 优先级 |
|---------|--------|------|---------|--------|
| TC-043 | 10,000 条活动记录 | 查询用户活动 | < 100ms | P1 |
| TC-044 | 10,000 条活动记录 | 统计热门合集 | < 200ms | P1 |
| TC-045 | 10,000 条活动记录 | 用户活动统计 | < 150ms | P1 |
| TC-046 | 100,000 条活动记录 | 查询用户活动 | < 200ms | P2 |

**测试方法**:
```sql
-- 生成测试数据
INSERT INTO user_activities (user_id, activity_type, collection_id, created_at)
SELECT
    (random() * 100)::int + 1,
    (ARRAY['view_collection', 'search', 'download'])[floor(random() * 3 + 1)],
    (random() * 50)::int + 1,
    NOW() - (random() * INTERVAL '30 days')
FROM generate_series(1, 10000);

-- 测试查询性能
EXPLAIN ANALYZE SELECT * FROM user_activities WHERE user_id = 1 ORDER BY created_at DESC LIMIT 20;
```

---

### 5.2 API 性能测试

**测试目标**: 验证 API 响应时间

| 测试用例 | API 端点 | 并发数 | 性能指标 | 优先级 |
|---------|---------|--------|---------|--------|
| TC-047 | GET /api/analytics/popular-collections | 10 | 平均响应 < 200ms | P1 |
| TC-048 | GET /api/analytics/users/{id}/activities | 10 | 平均响应 < 150ms | P1 |
| TC-049 | GET /api/analytics/users/{id}/stats | 10 | 平均响应 < 200ms | P1 |

**测试工具**: Apache Bench (ab) 或 wrk

```bash
# 使用 ab 进行压力测试
ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analytics/popular-collections
```

---

## 6. 安全性测试

### 6.1 权限验证测试

**测试目标**: 验证权限控制正确性

| 测试用例 | 操作 | 用户角色 | 预期结果 | 优先级 |
|---------|------|---------|---------|--------|
| TC-050 | 访问分析 API | 未登录 | 401 Unauthorized | P0 |
| TC-051 | 访问分析 API | 普通用户 | 403 Forbidden | P0 |
| TC-052 | 访问分析 API | VIP 用户 | 403 Forbidden | P0 |
| TC-053 | 访问分析 API | 管理员 | 200 OK | P0 |
| TC-054 | 访问分析 API | 超级管理员 | 200 OK | P0 |

**测试脚本**:
```bash
# 测试未登录访问
curl -X GET "http://localhost:8000/api/analytics/popular-collections"
# 预期: 401

# 测试普通用户访问
USER_TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": NORMAL_USER_ID}' | jq -r '.access_token')

curl -X GET "http://localhost:8000/api/analytics/popular-collections" \
  -H "Authorization: Bearer $USER_TOKEN"
# 预期: 403
```

---

### 6.2 数据隔离测试

**测试目标**: 验证用户数据隔离

| 测试用例 | 操作 | 预期结果 | 优先级 |
|---------|------|---------|--------|
| TC-055 | 用户 A 查看用户 B 的活动 | 只有管理员可以查看 | P0 |
| TC-056 | SQL 注入测试 | 参数正确转义，无注入风险 | P0 |
| TC-057 | XSS 测试 | 输出正确转义 | P1 |

---

## 7. 集成测试

### 7.1 端到端测试流程

**测试场景**: 完整的用户行为分析流程

**步骤**:
1. 用户登录系统
2. 浏览多个合集（生成 view_collection 活动）
3. 搜索合集（生成 search 活动）
4. 下载媒体（生成 download 活动）
5. 管理员查看热门合集统计
6. 管理员查看用户活动记录
7. 管理员查看用户行为统计
8. 验证所有数据一致性

**预期结果**:
- 所有活动都被正确记录
- 统计数据准确
- 热门合集排序正确
- 用户行为分析准确

---

### 7.2 数据一致性测试

**测试目标**: 验证数据库数据一致性

| 测试用例 | 验证内容 | 优先级 |
|---------|---------|--------|
| TC-058 | 活动记录的 user_id 必须存在于 users 表 | P0 |
| TC-059 | 活动记录的 collection_id 必须存在于 collections 表（或为 NULL） | P0 |
| TC-060 | 统计数据与原始数据一致 | P0 |
| TC-061 | 外键约束正确工作 | P0 |

**验证脚本**:
```sql
-- 检查孤立的活动记录
SELECT * FROM user_activities
WHERE user_id NOT IN (SELECT id FROM users);

-- 检查无效的 collection_id
SELECT * FROM user_activities
WHERE collection_id IS NOT NULL
  AND collection_id NOT IN (SELECT id FROM collections);

-- 验证统计数据
SELECT COUNT(*) FROM user_activities WHERE user_id = 1;
-- 对比 API 返回的 total_activities
```

---

## 8. 回归测试

### 8.1 现有功能测试

**测试目标**: 确保新功能不影响现有功能

| 功能模块 | 测试内容 | 优先级 |
|---------|---------|--------|
| 用户管理 | 用户注册、登录、角色管理 | P0 |
| 合集管理 | 创建、编辑、删除合集 | P0 |
| 媒体管理 | 上传、查看、删除媒体 | P0 |
| 搬运任务 | 创建、执行、监控任务 | P0 |
| Session 管理 | 添加、删除、切换 Session | P1 |

---

## 9. 测试数据准备

### 9.1 测试用户

```sql
-- 创建测试用户
INSERT INTO users (telegram_id, username, first_name, role, created_at, last_active_at)
VALUES
    (100001, 'test_user', 'Test User', 'user', NOW(), NOW()),
    (100002, 'test_vip', 'Test VIP', 'vip', NOW(), NOW()),
    (100003, 'test_admin', 'Test Admin', 'admin', NOW(), NOW()),
    (100004, 'test_super_admin', 'Test Super Admin', 'super_admin', NOW(), NOW());
```

### 9.2 测试合集

```sql
-- 创建测试合集
INSERT INTO collections (name, description, tags, deep_link_code, access_level, created_by, created_at, updated_at)
VALUES
    ('测试合集1', '这是测试合集1', ARRAY['测试', '示例'], 'test001', 'public', 1, NOW(), NOW()),
    ('测试合集2', '这是测试合集2', ARRAY['测试', 'VIP'], 'test002', 'vip', 1, NOW(), NOW()),
    ('热门合集', '这是热门合集', ARRAY['热门'], 'test003', 'public', 1, NOW(), NOW());
```

### 9.3 测试活动数据

```sql
-- 创建测试活动数据
INSERT INTO user_activities (user_id, activity_type, collection_id, extra_data, created_at)
VALUES
    (1, 'view_collection', 1, NULL, NOW() - INTERVAL '1 hour'),
    (1, 'view_collection', 1, NULL, NOW() - INTERVAL '2 hours'),
    (1, 'search', NULL, '{"keywords": "测试"}', NOW() - INTERVAL '3 hours'),
    (1, 'download', 1, NULL, NOW() - INTERVAL '4 hours'),
    (2, 'view_collection', 1, NULL, NOW() - INTERVAL '5 hours'),
    (2, 'view_collection', 2, NULL, NOW() - INTERVAL '6 hours');
```

---

## 10. 测试环境配置

### 10.1 环境要求

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- 测试数据库: blackholebot_test

### 10.2 环境准备

```bash
# 1. 创建测试数据库
sudo -u postgres psql -c "CREATE DATABASE blackholebot_test;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE blackholebot_test TO blackholebot_user;"

# 2. 运行迁移
export DATABASE_URL=postgresql+asyncpg://blackholebot_user:blackhole_pass_2024@localhost/blackholebot_test
alembic upgrade head

# 3. 导入测试数据
psql -U blackholebot_user -h localhost -d blackholebot_test -f docs/test_data.sql

# 4. 启动测试服务器
python main.py
```

---

## 11. 测试报告模板

### 11.1 测试执行记录

| 测试用例 | 执行日期 | 执行人 | 结果 | 备注 |
|---------|---------|--------|------|------|
| TC-001 | | | ☐ Pass ☐ Fail | |
| TC-002 | | | ☐ Pass ☐ Fail | |
| ... | | | | |

### 11.2 缺陷记录

| 缺陷 ID | 严重程度 | 描述 | 重现步骤 | 状态 |
|---------|---------|------|---------|------|
| BUG-001 | Critical | | | Open |
| BUG-002 | Major | | | Open |

### 11.3 测试总结

**测试覆盖率**: __%
**通过率**: __%
**发现缺陷数**: __
**阻塞性缺陷**: __
**建议**:

---

## 12. 验收标准

### 12.1 功能验收

- ✅ 所有 P0 测试用例通过
- ✅ 90% 以上 P1 测试用例通过
- ✅ 无阻塞性缺陷
- ✅ 无严重性能问题

### 12.2 性能验收

- ✅ API 响应时间 < 200ms (P95)
- ✅ 数据库查询时间 < 100ms (P95)
- ✅ 支持 10 并发用户无性能下降

### 12.3 安全验收

- ✅ 所有权限验证测试通过
- ✅ 无 SQL 注入漏洞
- ✅ 无 XSS 漏洞
- ✅ 敏感数据正确保护

---

## 13. 测试时间表

| 阶段 | 时间 | 负责人 |
|------|------|--------|
| 测试准备 | 0.5 天 | |
| 功能测试 | 1 天 | |
| 性能测试 | 0.5 天 | |
| 安全测试 | 0.5 天 | |
| 回归测试 | 0.5 天 | |
| 测试报告 | 0.5 天 | |
| **总计** | **3.5 天** | |

---

## 附录

### A. 测试工具

- **API 测试**: curl, Postman, HTTPie
- **性能测试**: Apache Bench, wrk, Locust
- **数据库测试**: psql, pgAdmin
- **自动化测试**: pytest, pytest-asyncio

### B. 参考文档

- API 文档: `/docs` (FastAPI Swagger UI)
- 数据库模型: `database/models.py`
- CRUD 操作: `database/crud.py`
- API 端点: `web/api/analytics.py`

### C. 联系方式

- 项目负责人:
- 测试负责人:
- 技术支持:

---

**文档版本**: 1.0
**最后更新**: 2026-02-27
**状态**: 待审核
