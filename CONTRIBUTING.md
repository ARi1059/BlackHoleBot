# 贡献指南

感谢你对 BlackHoleBot 项目的关注！本文档将帮助你快速上手项目开发。

## 开发环境设置

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/BlackHoleBot.git
cd BlackHoleBot
```

### 2. 安装依赖

**使用 Docker（推荐）**：
```bash
docker compose up -d
```

**手动安装**：
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填写必要配置
```

### 4. 初始化数据库

```bash
# Docker
docker compose exec bot alembic upgrade head

# 手动
alembic upgrade head
```

## 开发流程

### 分支管理

- `main` - 主分支，保持稳定
- `develop` - 开发分支
- `feature/*` - 功能分支
- `bugfix/*` - 修复分支
- `hotfix/*` - 紧急修复

### 工作流程

1. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **开发功能**
   - 编写代码
   - 添加注释
   - 遵循代码规范

3. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   ```

4. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 描述
   - 等待代码审查

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构代码
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关

### 示例

```bash
feat(bot): 添加批量删除合集功能

- 添加 /batch_delete 命令
- 实现批量选择界面
- 添加确认对话框

Closes #123
```

## 代码规范

### Python 代码风格

遵循 [PEP 8](https://pep8.org/) 规范：

```python
# 好的示例
async def get_user_by_id(user_id: int) -> Optional[User]:
    """根据 ID 获取用户

    Args:
        user_id: 用户 ID

    Returns:
        用户对象，不存在返回 None
    """
    async with get_db() as db:
        return await db.get(User, user_id)


# 避免
async def getUserById(userId):
    db = get_db()
    return db.get(User, userId)
```

### 命名规范

- **文件名**: 小写下划线 `user_handler.py`
- **类名**: 大驼峰 `UserHandler`
- **函数名**: 小写下划线 `get_user_info`
- **常量**: 大写下划线 `MAX_RETRY_COUNT`
- **私有变量**: 下划线前缀 `_internal_state`

### 类型注解

所有函数都应该有类型注解：

```python
from typing import List, Optional

async def get_collections(
    user_id: int,
    limit: int = 10,
    offset: int = 0
) -> List[Collection]:
    """获取用户的合集列表"""
    pass
```

### 文档字符串

使用 Google 风格的 docstring：

```python
def complex_function(param1: str, param2: int) -> bool:
    """函数简短描述

    详细描述函数的功能和用途。

    Args:
        param1: 参数1的描述
        param2: 参数2的描述

    Returns:
        返回值的描述

    Raises:
        ValueError: 参数无效时抛出

    Example:
        >>> complex_function("test", 42)
        True
    """
    pass
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_user.py

# 查看覆盖率
pytest --cov=. --cov-report=html
```

### 编写测试

```python
import pytest
from database.models import User

@pytest.mark.asyncio
async def test_create_user():
    """测试创建用户"""
    user = User(
        telegram_id=123456,
        username="testuser"
    )
    assert user.telegram_id == 123456
    assert user.username == "testuser"
```

## 数据库迁移

### 创建迁移

```bash
# 自动生成迁移
alembic revision --autogenerate -m "添加新字段"

# 手动创建迁移
alembic revision -m "自定义迁移"
```

### 执行迁移

```bash
# 升级到最新版本
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看迁移历史
alembic history
```

## 调试技巧

### 本地调试

```python
# 使用 logging
import logging
logger = logging.getLogger(__name__)

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### Docker 调试

```bash
# 查看日志
docker compose logs -f bot

# 进入容器
docker compose exec bot bash

# 执行 Python 命令
docker compose exec bot python -c "print('test')"
```

## 常见问题

### Q: 如何添加新的 Bot 命令？

1. 在 `bot/handlers/` 下创建或编辑处理器
2. 注册路由到 `bot/main.py`
3. 更新文档

### Q: 如何添加新的 API 接口？

1. 在 `web/api/` 下创建或编辑路由
2. 添加 Pydantic 模型验证
3. 更新 API 文档

### Q: 如何修改数据库结构？

1. 修改 `database/models.py`
2. 创建迁移：`alembic revision --autogenerate -m "描述"`
3. 执行迁移：`alembic upgrade head`

### Q: 如何添加新的依赖？

1. 添加到 `requirements.txt`
2. 重新构建 Docker 镜像：`docker compose build`
3. 或在虚拟环境中安装：`pip install package-name`

## 代码审查清单

提交 PR 前请检查：

- [ ] 代码遵循项目规范
- [ ] 添加了必要的注释和文档
- [ ] 添加了类型注解
- [ ] 通过了所有测试
- [ ] 更新了相关文档
- [ ] 提交信息符合规范
- [ ] 没有遗留调试代码
- [ ] 没有提交敏感信息

## 性能优化建议

1. **数据库查询**
   - 使用索引
   - 避免 N+1 查询
   - 使用批量操作

2. **异步编程**
   - 正确使用 async/await
   - 避免阻塞操作
   - 使用连接池

3. **缓存策略**
   - 缓存热点数据
   - 设置合理的过期时间
   - 及时清理过期缓存

## 安全注意事项

1. **永远不要提交**：
   - `.env` 文件
   - API 密钥
   - 数据库密码
   - Session 文件

2. **输入验证**：
   - 使用 Pydantic 验证
   - 检查用户权限
   - 防止 SQL 注入

3. **错误处理**：
   - 不要暴露敏感信息
   - 记录详细日志
   - 友好的错误提示

## 获取帮助

- 查看 [文档](docs/)
- 提交 [Issue](https://github.com/yourusername/BlackHoleBot/issues)
- 加入讨论组

## 许可证

通过贡献代码，你同意你的贡献将在 MIT 许可证下发布。
