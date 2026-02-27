-- BlackHoleBot Phase 3 测试数据
-- 用于快速生成测试数据

-- 1. 创建测试用户
INSERT INTO users (telegram_id, username, first_name, role, created_at, last_active_at)
VALUES
    (100001, 'test_user', 'Test User', 'user', NOW(), NOW()),
    (100002, 'test_vip', 'Test VIP', 'vip', NOW(), NOW()),
    (100003, 'test_admin', 'Test Admin', 'admin', NOW(), NOW())
ON CONFLICT (telegram_id) DO NOTHING;

-- 2. 创建测试合集
INSERT INTO collections (name, description, tags, deep_link_code, access_level, media_count, created_by, created_at, updated_at)
VALUES
    ('测试合集1', '这是一个公开的测试合集', ARRAY['测试', '示例'], 'test_col_001', 'public', 5, 1, NOW() - INTERVAL '10 days', NOW()),
    ('测试合集2', '这是一个VIP测试合集', ARRAY['测试', 'VIP'], 'test_col_002', 'vip', 3, 1, NOW() - INTERVAL '8 days', NOW()),
    ('热门合集', '这是一个热门合集', ARRAY['热门', '推荐'], 'test_col_003', 'public', 10, 1, NOW() - INTERVAL '5 days', NOW()),
    ('技术教程', 'Python编程教程合集', ARRAY['编程', '教程'], 'test_col_004', 'public', 8, 1, NOW() - INTERVAL '3 days', NOW()),
    ('电影收藏', '经典电影合集', ARRAY['电影', '娱乐'], 'test_col_005', 'vip', 15, 1, NOW() - INTERVAL '1 day', NOW())
ON CONFLICT (deep_link_code) DO NOTHING;

-- 3. 生成用户活动数据 (模拟真实用户行为)
DO $$
DECLARE
    user_record RECORD;
    collection_record RECORD;
    activity_types TEXT[] := ARRAY['view_collection', 'search', 'download'];
    activity_type TEXT;
    i INTEGER;
BEGIN
    -- 为每个用户生成活动记录
    FOR user_record IN SELECT id FROM users LIMIT 10 LOOP
        -- 每个用户生成 20-50 条活动记录
        FOR i IN 1..(20 + floor(random() * 30)::int) LOOP
            -- 随机选择活动类型
            activity_type := activity_types[1 + floor(random() * 3)::int];

            IF activity_type = 'view_collection' OR activity_type = 'download' THEN
                -- 浏览或下载需要关联合集
                SELECT id INTO collection_record FROM collections ORDER BY random() LIMIT 1;

                INSERT INTO user_activities (user_id, activity_type, collection_id, created_at)
                VALUES (
                    user_record.id,
                    activity_type,
                    collection_record.id,
                    NOW() - (random() * INTERVAL '30 days')
                );
            ELSE
                -- 搜索活动
                INSERT INTO user_activities (user_id, activity_type, collection_id, extra_data, created_at)
                VALUES (
                    user_record.id,
                    'search',
                    NULL,
                    jsonb_build_object('keywords', (ARRAY['测试', 'Python', '电影', '教程', '热门'])[1 + floor(random() * 5)::int]),
                    NOW() - (random() * INTERVAL '30 days')
                );
            END IF;
        END LOOP;
    END LOOP;
END $$;

-- 4. 生成管理员日志数据
INSERT INTO admin_logs (user_id, action, details, ip_address, user_agent, created_at)
SELECT
    (SELECT id FROM users WHERE role IN ('admin', 'super_admin') ORDER BY random() LIMIT 1),
    (ARRAY['update_user_role', 'ban_user', 'unban_user', 'delete_collection', 'batch_update_vip'])[1 + floor(random() * 5)::int],
    jsonb_build_object(
        'target_user_id', floor(random() * 100)::int,
        'old_value', 'user',
        'new_value', 'vip'
    ),
    '127.0.0.1',
    'Mozilla/5.0 (Test)',
    NOW() - (random() * INTERVAL '30 days')
FROM generate_series(1, 50);

-- 5. 更新合集的媒体数量（确保数据一致性）
UPDATE collections SET media_count = (
    SELECT COUNT(*) FROM media WHERE media.collection_id = collections.id
);

-- 6. 显示测试数据统计
SELECT '=== 测试数据统计 ===' as info;

SELECT
    '用户总数' as metric,
    COUNT(*)::text as value
FROM users
UNION ALL
SELECT
    '合集总数',
    COUNT(*)::text
FROM collections
UNION ALL
SELECT
    '活动记录总数',
    COUNT(*)::text
FROM user_activities
UNION ALL
SELECT
    '管理员日志总数',
    COUNT(*)::text
FROM admin_logs;

-- 7. 显示热门合集预览
SELECT '=== 热门合集预览 ===' as info;

SELECT
    c.name as 合集名称,
    COUNT(ua.id) as 访问次数,
    c.media_count as 媒体数量,
    c.access_level as 访问权限
FROM collections c
LEFT JOIN user_activities ua ON c.id = ua.collection_id AND ua.activity_type = 'view_collection'
GROUP BY c.id, c.name, c.media_count, c.access_level
ORDER BY COUNT(ua.id) DESC
LIMIT 5;

-- 8. 显示用户活动统计预览
SELECT '=== 用户活动统计预览 ===' as info;

SELECT
    u.username as 用户名,
    COUNT(ua.id) as 总活动数,
    COUNT(CASE WHEN ua.activity_type = 'view_collection' THEN 1 END) as 浏览次数,
    COUNT(CASE WHEN ua.activity_type = 'search' THEN 1 END) as 搜索次数,
    COUNT(CASE WHEN ua.activity_type = 'download' THEN 1 END) as 下载次数
FROM users u
LEFT JOIN user_activities ua ON u.id = ua.user_id
GROUP BY u.id, u.username
ORDER BY COUNT(ua.id) DESC
LIMIT 5;
