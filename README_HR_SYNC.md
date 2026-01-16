# AccountSync - 人员数据定时同步系统

本项目实现了从HIEDS API定时拉取人员数据的功能，支持增量同步和自动定时任务。

## 功能特性

- ✅ 定时10分钟自动同步人员数据（可开关控制）
- ✅ 支持增量同步（根据creationDate）
- ✅ 分页获取所有数据
- ✅ 人员数据去重（根据personId）
- ✅ REST API接口查询同步状态
- ✅ 手动触发同步功能
- ✅ 完整的日志记录

## 环境配置

### 1. 环境变量设置

在`.env`文件中添加以下配置：

```bash
# 数据库配置（已有）
DB_NAME=accountsync
DB_USER=accountsync
DB_PASSWORD=your_password
DB_HOST=your_host
DB_PORT=5432

# HIEDS API 配置
HIEDS_ACCOUNT=your_account          # API账户名
HIEDS_SECRET=your_secret            # API密钥
HIEDS_PROJECT=your_project          # 项目ID
HIEDS_ENTERPRISE=your_enterprise    # 企业ID
HIEDS_PERSON_PROJECT_ID=your_project_id  # 人员数据项目ID
HIEDS_TENANT_ID=your_tenant_id      # 租户ID
HIEDS_PAGE_SIZE=20                  # 每页获取数量（默认20）

# 同步控制
HR_SYNC_ENABLED=true               # 是否启用自动同步（true/false/1/0/yes/no/on/off）
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 数据库迁移

```bash
python manage.py migrate
```

## 使用方法

### 启动服务

```bash
python manage.py runserver
```

服务启动后会自动开始定时同步检查。

### API接口

#### 1. 查看同步状态

```
GET /hr-persons/sync_status/
```

响应示例：
```json
{
    "last_sync_time": "2024-01-16T10:30:00Z",
    "total_persons": 1389,
    "last_sync_status": "success",
    "next_sync_time": "2024-01-16T10:40:00Z"
}
```

#### 2. 手动触发同步

```
POST /hr-persons/manual_sync/
```

请求体（可选）：
```json
{
    "force_full_sync": false,
    "page_size": 20
}
```

#### 3. 查询人员数据

```
GET /hr-persons/
```

支持过滤参数：
- `employee_number`: 员工编号（模糊搜索）
- `full_name`: 全名（模糊搜索）
- `employee_status`: 员工状态
- `person_type`: 人员类型
- `creation_date_gte`: 创建时间大于等于
- `creation_date_lte`: 创建时间小于等于

### 管理命令

#### 手动执行同步

```bash
# 增量同步（默认）
python manage.py sync_hr_persons

# 全量同步
python manage.py sync_hr_persons --force-full-sync

# 指定每页大小
python manage.py sync_hr_persons --page-size 50
```

#### 查看帮助

```bash
python manage.py sync_hr_persons --help
```

## 系统架构

### 数据模型

#### HrPerson（人员信息）
- 存储所有API返回的人员字段
- person_id为主键
- 支持根据personId去重更新

#### SyncConfig（同步配置）
- 存储同步状态和配置信息
- last_sync_time: 上次同步时间
- last_sync_status: 同步状态

### 定时任务机制

- 使用Django中间件实现请求级定时检查
- 每10分钟检查一次是否需要同步
- 支持并发控制，避免重复执行

### 同步流程

1. 获取访问token
2. 获取上次同步时间（增量）或全量同步
3. 分页获取人员数据
4. 解析并保存到数据库
5. 更新同步状态

## 日志和监控

### 日志文件

同步日志保存在 `logs/hr_sync.log` 文件中，包含：
- 同步开始/结束时间
- 处理的数据量
- 错误信息

### 同步状态监控

通过API `/hr-persons/sync_status/` 可以实时查看：
- 上次同步时间
- 当前总人数
- 同步状态
- 下次同步时间

## 部署注意事项

### 生产环境配置

1. 设置正确的环境变量
2. 确保网络能访问HIEDS API
3. 配置日志轮转
4. 设置适当的定时间隔
5. 根据需要开启/关闭自动同步：
   - `HR_SYNC_ENABLED=true` 开启自动同步
   - `HR_SYNC_ENABLED=false` 关闭自动同步（仅通过API手动触发）

## 同步开关控制

系统提供了同步开关功能，可以灵活控制是否启用自动定时同步：

### 开关配置

在`.env`文件中设置：
```bash
# 开启自动同步（默认）
HR_SYNC_ENABLED=true

# 关闭自动同步
HR_SYNC_ENABLED=false
```

### 支持的值

开关支持多种表示方式：
- `true`, `1`, `yes`, `on` → 开启同步
- `false`, `0`, `no`, `off` → 关闭同步

### 工作原理

- **开启状态**：每次有请求访问应用时，中间件会检查是否需要执行定时同步
- **关闭状态**：中间件跳过同步检查，定时任务完全不执行
- **手动同步**：无论开关状态如何，都可以通过API手动触发同步

### 使用场景

1. **开发测试**：关闭自动同步，避免频繁API调用
2. **维护窗口**：临时关闭同步进行系统维护
3. **故障排查**：关闭自动同步，手动控制同步时机
4. **生产部署**：开启自动同步，确保数据及时更新

### 性能优化

- 默认每页20条数据，可根据需要调整
- API请求之间有1秒延迟，避免限流
- 支持增量同步，减少数据传输

### 错误处理

- Token获取失败会记录错误
- 网络异常会自动重试
- 数据保存失败会跳过单条记录
- 同步状态会准确反映执行结果

## 故障排除

### 常见问题

1. **Token获取失败**
   - 检查环境变量配置
   - 确认网络连接
   - 验证API凭据

2. **同步无数据**
   - 检查HIEDS_PROJECT和HIEDS_PERSON_PROJECT_ID
   - 确认租户权限

3. **定时任务不执行**
   - 确认中间件已配置
   - 检查 `HR_SYNC_ENABLED` 是否设置为 `true`
   - 检查日志文件
   - 验证服务器请求频率

## 开发说明

### 添加新字段

1. 在 `HrPerson` 模型中添加字段
2. 生成迁移：`python manage.py makemigrations`
3. 应用迁移：`python manage.py migrate`
4. 更新 `sync_hr_persons.py` 中的数据映射

### 修改同步逻辑

编辑 `syncservice/management/commands/sync_hr_persons.py` 文件。

### 自定义定时任务

修改 `syncservice/cron/scheduler.py` 中的检查逻辑。