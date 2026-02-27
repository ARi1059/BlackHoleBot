#!/bin/bash

# BlackHoleBot Phase 3 快速测试脚本
# 使用方法: bash docs/quick_test.sh

set -e

echo "=========================================="
echo "BlackHoleBot Phase 3 快速测试"
echo "=========================================="
echo ""

# 配置
API_BASE="http://localhost:8000"
ADMIN_TELEGRAM_ID="624144243"  # 管理员 Telegram ID

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
test_api() {
    local test_name=$1
    local method=$2
    local endpoint=$3
    local expected_status=$4
    local extra_args=${5:-""}

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "测试 $TOTAL_TESTS: $test_name ... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "$API_BASE$endpoint" $extra_args)
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE$endpoint" $extra_args)
    fi

    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (状态码: $status_code)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (期望: $expected_status, 实际: $status_code)"
        echo "响应: $body"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 步骤 1: 获取管理员 Token
echo "步骤 1: 获取管理员 Token"
echo "----------------------------------------"

if [ "$ADMIN_TELEGRAM_ID" = "YOUR_ADMIN_TELEGRAM_ID" ]; then
    echo -e "${RED}错误: 请先在脚本中设置 ADMIN_TELEGRAM_ID${NC}"
    exit 1
fi

TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"telegram_id\": $ADMIN_TELEGRAM_ID}")

TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}错误: 无法获取 Token，请检查管理员 Telegram ID${NC}"
    echo "响应: $TOKEN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Token 获取成功${NC}"
echo ""

# 步骤 2: 测试热门合集 API
echo "步骤 2: 测试热门合集分析"
echo "----------------------------------------"

test_api "获取热门合集 (默认参数)" \
    "GET" \
    "/api/analytics/popular-collections" \
    "200" \
    "-H 'Authorization: Bearer $TOKEN'"

test_api "获取热门合集 (限制10条)" \
    "GET" \
    "/api/analytics/popular-collections?limit=10" \
    "200" \
    "-H 'Authorization: Bearer $TOKEN'"

test_api "获取热门合集 (最近7天)" \
    "GET" \
    "/api/analytics/popular-collections?days=7" \
    "200" \
    "-H 'Authorization: Bearer $TOKEN'"

test_api "获取热门合集 (无权限)" \
    "GET" \
    "/api/analytics/popular-collections" \
    "401" \
    ""

echo ""

# 步骤 3: 测试用户活动 API
echo "步骤 3: 测试用户活动记录"
echo "----------------------------------------"

# 获取第一个用户的 ID
USER_ID=$(curl -s -X GET "$API_BASE/api/users?limit=1" \
    -H "Authorization: Bearer $TOKEN" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

if [ -z "$USER_ID" ]; then
    echo -e "${YELLOW}警告: 无法获取用户 ID，跳过用户活动测试${NC}"
else
    test_api "获取用户活动记录" \
        "GET" \
        "/api/analytics/users/$USER_ID/activities" \
        "200" \
        "-H 'Authorization: Bearer $TOKEN'"

    test_api "获取用户活动记录 (限制5条)" \
        "GET" \
        "/api/analytics/users/$USER_ID/activities?limit=5" \
        "200" \
        "-H 'Authorization: Bearer $TOKEN'"

    test_api "获取用户活动统计" \
        "GET" \
        "/api/analytics/users/$USER_ID/stats" \
        "200" \
        "-H 'Authorization: Bearer $TOKEN'"

    test_api "获取用户活动统计 (最近7天)" \
        "GET" \
        "/api/analytics/users/$USER_ID/stats?days=7" \
        "200" \
        "-H 'Authorization: Bearer $TOKEN'"
fi

echo ""

# 步骤 4: 测试用户统计 API
echo "步骤 4: 测试用户统计分析"
echo "----------------------------------------"

test_api "获取用户统计数据" \
    "GET" \
    "/api/users/statistics" \
    "200" \
    "-H 'Authorization: Bearer $TOKEN'"

echo ""

# 步骤 5: 测试搜索功能
echo "步骤 5: 测试搜索功能"
echo "----------------------------------------"

test_api "搜索合集" \
    "GET" \
    "/api/collections?limit=10" \
    "200" \
    "-H 'Authorization: Bearer $TOKEN'"

test_api "搜索用户" \
    "GET" \
    "/api/users?limit=10" \
    "200" \
    "-H 'Authorization: Bearer $TOKEN'"

echo ""

# 步骤 6: 数据库验证
echo "步骤 6: 数据库数据验证"
echo "----------------------------------------"

echo -n "检查 user_activities 表 ... "
ACTIVITY_COUNT=$(psql -U blackholebot_user -h localhost -d blackholebot -t -c "SELECT COUNT(*) FROM user_activities;" 2>/dev/null || echo "ERROR")

if [ "$ACTIVITY_COUNT" = "ERROR" ]; then
    echo -e "${YELLOW}跳过 (需要数据库访问权限)${NC}"
else
    echo -e "${GREEN}✓ 表存在，记录数: $(echo $ACTIVITY_COUNT | xargs)${NC}"
fi

echo -n "检查 admin_logs 表 ... "
LOG_COUNT=$(psql -U blackholebot_user -h localhost -d blackholebot -t -c "SELECT COUNT(*) FROM admin_logs;" 2>/dev/null || echo "ERROR")

if [ "$LOG_COUNT" = "ERROR" ]; then
    echo -e "${YELLOW}跳过 (需要数据库访问权限)${NC}"
else
    echo -e "${GREEN}✓ 表存在，记录数: $(echo $LOG_COUNT | xargs)${NC}"
fi

echo -n "检查索引 ... "
INDEX_COUNT=$(psql -U blackholebot_user -h localhost -d blackholebot -t -c "SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'user_activities';" 2>/dev/null || echo "ERROR")

if [ "$INDEX_COUNT" = "ERROR" ]; then
    echo -e "${YELLOW}跳过 (需要数据库访问权限)${NC}"
else
    echo -e "${GREEN}✓ 索引数量: $(echo $INDEX_COUNT | xargs)${NC}"
fi

echo ""

# 测试总结
echo "=========================================="
echo "测试总结"
echo "=========================================="
echo "总测试数: $TOTAL_TESTS"
echo -e "通过: ${GREEN}$PASSED_TESTS${NC}"
echo -e "失败: ${RED}$FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo -e "\n通过率: $PASS_RATE%"
    if [ $PASS_RATE -ge 80 ]; then
        echo -e "${YELLOW}⚠ 部分测试失败，请检查失败的测试用例${NC}"
        exit 1
    else
        echo -e "${RED}✗ 测试失败率过高，请检查系统配置${NC}"
        exit 1
    fi
fi
