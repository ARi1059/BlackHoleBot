# Bot 管理员功能使用说明

## 已完成的功能

### ✅ 核心模块

1. **FSM 状态定义** (`bot/states.py`)
   - `UploadStates` - 上传合集状态机
   - `AddMediaStates` - 添加媒体状态机
   - `EditCollectionStates` - 编辑合集状态机
   - `BatchDeleteStates` - 批量删除状态机

2. **管理员处理器** (`bot/handlers/admin.py`)
   - 权限检查装饰器 `@require_admin`
   - 完整的上传流程（FSM）
   - 合集管理功能
   - 编辑和删除功能
   - 批量操作功能

3. **主程序更新** (`bot/main.py`)
   - 注册管理员路由

## 实现的功能

### 1. 创建新合集 (`/upload`)

**完整流程**:
```
/upload
  ↓
发送媒体文件（图片/视频）
  ↓
/done
  ↓
输入合集名称
  ↓
输入描述（可 /skip）
  ↓
输入标签（可 /skip）
  ↓
选择权限（公开/VIP）
  ↓
✅ 创建成功，返回深链接
```

**特性**:
- ✅ 支持图片和视频
- ✅ 自动去重（file_unique_id）
- ✅ 实时反馈已接收文件数
- ✅ 完整的输入验证
- ✅ FSM 状态管理
- ✅ 可随时 `/cancel` 取消

### 2. 查看所有合集 (`/list_collections`)

**功能**:
- 显示所有合集列表
- 显示深链接码、媒体数量、创建时间
- 区分公开/VIP 合集
- 最多显示 20 个

### 3. 删除合集 (`/delete_collection`)

**用法**: `/delete_collection abc123`

**特性**:
- ✅ 二次确认（防误删）
- ✅ 显示合集信息
- ✅ 级联删除媒体
- ✅ 记录操作日志

### 4. 添加媒体到现有合集 (`/add_media`)

**用法**: `/add_media abc123`

**流程**:
```
/add_media abc123
  ↓
发送媒体文件
  ↓
/done
  ↓
✅ 添加成功
```

**特性**:
- ✅ 自动计算 order_index
- ✅ 更新合集媒体数量
- ✅ 支持去重

### 5. 编辑合集信息 (`/edit_collection`)

**用法**: `/edit_collection abc123`

**可编辑项**:
- 📝 合集名称
- 📄 描述
- 🏷️ 标签
- 🔒 访问权限

**特性**:
- ✅ 显示当前信息
- ✅ 按钮选择编辑项
- ✅ 完整的输入验证
- ✅ 记录操作日志

### 6. 批量删除合集 (`/batch_delete`)

**流程**:
```
/batch_delete
  ↓
输入深链接码（每行一个）
abc123
def456
ghi789
  ↓
确认删除
  ↓
✅ 批量删除成功
```

**特性**:
- ✅ 显示将要删除的合集列表
- ✅ 二次确认
- ✅ 统计删除数量

### 7. 取消操作 (`/cancel`)

**功能**:
- 在任何 FSM 状态下都可以取消
- 清除所有临时数据
- 友好的提示信息

## 管理员命令列表

| 命令 | 描述 | 权限要求 |
|------|------|---------|
| `/upload` | 创建新合集 | admin/super_admin |
| `/list_collections` | 查看所有合集 | admin/super_admin |
| `/delete_collection {code}` | 删除合集 | admin/super_admin |
| `/add_media {code}` | 添加媒体到合集 | admin/super_admin |
| `/edit_collection {code}` | 编辑合集信息 | admin/super_admin |
| `/batch_delete` | 批量删除合集 | admin/super_admin |
| `/cancel` | 取消当前操作 | 所有用户 |

## 权限系统

### 权限检查装饰器

```python
@require_admin
async def cmd_upload(message: Message, user: User, state: FSMContext):
    # 只有 admin 和 super_admin 可以访问
    pass
```

### 权限等级

- `user` - 普通用户（无管理权限）
- `vip` - VIP 用户（无管理权限）
- `admin` - 管理员（所有管理功能）
- `super_admin` - 超级管理员（所有管理功能 + 用户管理）

## 操作日志

所有管理员操作都会记录到 `admin_logs` 表：

**记录的操作**:
- `create_collection` - 创建合集
- `delete_collection` - 删除合集
- `edit_collection` - 编辑合集
- `add_media` - 添加媒体
- `batch_delete_collections` - 批量删除

**日志内容**:
- 用户 ID
- 操作类型
- 详细信息（JSON）
- 时间戳

## 测试步骤

### 1. 创建管理员账号

```bash
python scripts/create_admin.py --telegram-id YOUR_ID
```

### 2. 测试上传功能

1. 发送 `/upload`
2. 发送几张图片
3. 发送 `/done`
4. 按提示输入名称、描述、标签
5. 选择权限
6. 查看返回的深链接

### 3. 测试查看功能

```
/list_collections
```

应该看到刚才创建的合集

### 4. 测试编辑功能

```
/edit_collection abc123
```

点击按钮编辑各项信息

### 5. 测试删除功能

```
/delete_collection abc123
```

确认删除

## 注意事项

1. **权限检查**: 所有管理命令都会检查用户角色
2. **FSM 状态**: 使用状态机管理复杂流程
3. **输入验证**: 所有输入都有完整的验证
4. **错误处理**: 捕获异常并友好提示
5. **操作日志**: 记录所有管理操作

## 文件结构

```
BlackHoleBot/
├── bot/
│   ├── handlers/
│   │   ├── user.py          ✅ 用户端处理器
│   │   ├── admin.py         ✅ 管理员处理器
│   │   └── __init__.py      ✅ 导出路由
│   ├── middlewares/
│   │   └── auth.py          ✅ 认证中间件
│   ├── keyboards/
│   │   └── inline.py        ✅ 内联键盘
│   ├── states.py            ✅ FSM 状态定义
│   └── main.py              ✅ Bot 主程序
├── database/                ✅ 数据库模块
├── utils/                   ✅ 工具函数
└── config.py                ✅ 配置文件
```

## 下一步开发

管理员功能已完成，接下来可以开发：

1. **搬运系统** - 自动搬运媒体
2. **Web 后台** - 可视化管理界面
3. **更多管理功能** - 用户管理、系统设置等

## 常见问题

### Q: 非管理员能使用管理命令吗？
A: 不能，所有管理命令都有 `@require_admin` 装饰器保护。

### Q: 上传过程中可以取消吗？
A: 可以，任何时候发送 `/cancel` 都可以取消。

### Q: 如何查看操作日志？
A: 操作日志存储在数据库的 `admin_logs` 表中，可以通过 Web 后台查看。

### Q: 删除合集会删除媒体吗？
A: 会，数据库设置了级联删除（ON DELETE CASCADE）。

### Q: 可以编辑已有合集的媒体吗？
A: 目前支持添加新媒体，删除媒体功能可以后续添加。
