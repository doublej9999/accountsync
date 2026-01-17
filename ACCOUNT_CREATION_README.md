# AccountSync 账号创建接口

AccountSync 项目新增的账号创建功能，支持异步批量创建 IDAAS、Welink 和邮箱账号。

## 功能特性

- **异步处理**：账号创建任务异步执行，每5分钟自动处理
- **顺序控制**：严格按照 IDAAS → Welink → Email 的顺序创建账号
- **重试机制**：失败任务自动重试，最多5次
- **状态跟踪**：完整记录任务执行状态和结果
- **部门映射**：支持灵活的部门代码映射配置

## API 接口

### 创建账号接口

**端点**: `POST /account-creation/create_accounts/`

**请求体**:
```json
{
    "originSystem": "oa",
    "businessKey": "65090",
    "accountType": "personal",
    "employeeType": "W",
    "systemList": ["idaas", "welink", "email"],
    "userList": [{
        "employeeNumber": "P000126",
        "employeeName": "张三",
        "departmentCode": "120000",
        "phoneNumber": "1234567890",
        "partnerCompany": "ABC",
        "country": "cn"
    }]
}
```

**响应**:
```json
{
    "success": true,
    "created_tasks": 2,
    "errors": [],
    "tasks": [...]
}
```

### 任务统计接口

**端点**: `GET /account-creation/task_stats/`

返回各账号类型的任务统计信息。

### 查看任务日志

**端点**: `GET /account-creation/{id}/logs/`

查看任务的详细错误日志记录，包括每次重试的错误信息和执行上下文。

### 部门映射管理

**端点**: `GET/POST /department-mappings/`

管理部门代码映射关系。

## 配置说明

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# IDAAS 配置
IDAAS_ACCOUNT=your_idaas_account
IDAAS_SECRET=your_idaas_secret
IDAAS_ENTERPRISE_ID=your_enterprise_id
IDAAS_DC1=domain1
IDAAS_DC2=com

# Welink 配置
WELINK_CLIENT_ID=your_welink_client_id
WELINK_CLIENT_SECRET=your_welink_client_secret

# 邮箱配置
EMAIL_DOMAIN=@qq.com
EMAIL_AUTH_TOKEN=abcdefghijklmnopqrstuvwsyz

# 功能开关
ACCOUNT_CREATION_ENABLED=true
```

### 部门映射数据

运行以下命令加载基础部门映射：

```bash
python manage.py load_department_mappings
```

## 使用流程

1. **配置环境变量**：设置 API 密钥和端点
2. **加载部门映射**：初始化部门代码映射表
3. **调用创建接口**：发送账号创建请求
4. **监控任务状态**：通过统计接口查看处理进度
5. **处理失败任务**：必要时手动重试失败的任务

## 定时任务

系统每5分钟自动执行账号创建任务：

```bash
python manage.py process_account_creation_tasks --max-tasks=50
```

## 测试

运行测试脚本验证功能：

```bash
python test_api.py
```

## 日志

相关日志文件：
- `logs/hr_sync.log`：包含账号创建相关的日志信息

## 任务日志表

系统新增 `AccountCreationLog` 表，用于记录账号创建任务的详细错误信息：

- **一对多关系**：每个任务可以有多个错误日志记录
- **重试追踪**：通过 `execution_attempt` 字段记录第几次重试
- **错误详情**：存储完整的错误信息、堆栈跟踪和执行上下文
- **动态计算**：重试次数通过日志数量动态计算，无需存储在任务表中

### 日志字段说明

- `task`: 关联的任务
- `execution_attempt`: 执行尝试次数（从1开始）
- `error_message`: 错误信息摘要
- `error_details`: 详细错误信息（JSON格式）
- `execution_context`: 执行时的上下文数据
- `created_at`: 日志创建时间

## 注意事项

1. **依赖顺序**：Welink 和 Email 账号依赖 IDAAS 账号创建完成
2. **重试限制**：通过环境变量 `ACCOUNT_CREATION_MAX_RETRIES` 配置，默认5次
3. **数据一致性**：任务执行失败不会影响其他任务
4. **并发控制**：相同用户的相同账号类型不会重复创建
5. **日志清理**：建议定期清理过期的错误日志以控制数据库大小

## 故障排除

### 常见问题

1. **任务一直处于 pending 状态**
   - 检查定时任务是否正常运行
   - 确认 ACCOUNT_CREATION_ENABLED 设置为 true

2. **API 调用失败**
   - 检查环境变量配置
   - 确认外部服务可用性
   - 查看详细错误日志

3. **部门映射未找到**
   - 运行 `load_department_mappings` 命令
   - 检查部门代码是否正确

## 扩展开发

### 添加新的账号类型

1. 在 `AccountCreationService` 中添加新的创建方法
2. 更新 `ACCOUNT_TYPE_CHOICES`
3. 配置相应的环境变量
4. 测试新的账号创建流程