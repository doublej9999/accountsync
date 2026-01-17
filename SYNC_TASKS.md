# AccountSync 同步任务架构

本文档详细说明 AccountSync 系统中实现的三个核心同步任务调度器。

## 概述

AccountSync 实现了三个独立的定时任务调度器，每个调度器负责不同的功能模块，确保HR数据同步和账号创建流程的自动化执行。

## 1. HR同步调度器 (HrSyncScheduler)

### 职责
- 从HIEDS API同步人员数据到本地数据库
- 保持本地人员信息与HR系统的实时同步

### 触发方式
- **执行频率**: 每10分钟自动检查一次
- **手动触发**: 支持通过管理命令或API接口手动执行

### 配置控制
- **配置键**: `hr_sync_enabled`
- **默认状态**: 启用
- **控制方式**: 通过Django admin界面的SyncConfig表动态管理

### 工作流程
1. 检查同步开关是否启用
2. 获取上次同步时间戳
3. 调用HIEDS API获取增量人员数据
4. 解析并验证数据格式
5. 更新本地数据库（新增/修改人员记录）
6. 记录同步状态和时间戳

### 相关命令
```bash
# 手动执行HR数据同步
python manage.py sync_hr_persons

# 强制全量同步（忽略时间戳）
python manage.py sync_hr_persons --force-full-sync
```

### API接口
```http
POST /task-management/sync-hr-persons/
Content-Type: application/json

{
    "mode": "run",
    "force_full_sync": false
}
```

### 异常处理
- API调用失败时记录错误日志
- 数据格式异常时跳过问题记录
- 网络超时自动重试机制

## 2. 任务创建调度器 (TaskCreationScheduler)

### 职责
- 自动为有效员工创建账号创建任务
- 根据员工状态和账号类型生成相应的账号创建请求

### 触发方式
- **执行频率**: 每10分钟自动检查一次
- **触发条件**: 新增或状态变更的员工记录

### 配置控制
- **配置键**: `task_auto_creation_enabled`
- **默认状态**: 启用
- **任务类型**: IDAAS账号、Welink账号、Email账号

### 工作流程
1. 查询有效员工（employee_status在配置的有效状态列表中）
2. 检查员工是否已有对应的账号记录
3. 为缺失的账号类型创建AccountCreationTask任务
4. 设置任务依赖关系（确保正确的创建顺序）
5. 记录任务创建日志

### 相关命令
```bash
# 手动创建账号任务
python manage.py create_account_tasks

# 预览模式（仅显示将创建的任务）
python manage.py create_account_tasks --dry-run

# 指定员工状态
python manage.py create_account_tasks --employee-status "1" "2"
```

### API接口
```http
POST /task-management/create-account-tasks/
Content-Type: application/json

{
    "mode": "run",
    "employee_status": ["1", "2"]
}
```

### 任务依赖
- Email账号：无依赖，可直接创建
- IDAAS账号：无依赖，可直接创建
- Welink账号：依赖于IDAAS账号创建完成

## 3. 任务处理调度器 (AccountCreationScheduler)

### 职责
- 处理已存在的账号创建任务队列
- 调用外部API创建实际的账号
- 更新任务状态和记录执行结果

### 触发方式
- **执行频率**: 每5分钟自动检查一次
- **处理策略**: 批量处理，最大并发控制

### 配置控制
- **配置键**: `task_processing_enabled`
- **默认状态**: 启用
- **最大重试次数**: 5次（可配置）

### 工作流程
1. 查询待处理的任务（status='pending'）
2. 检查任务依赖是否满足
3. 按照依赖顺序排序执行任务
4. 调用对应的账号创建API
5. 更新任务状态和结果数据
6. 处理失败任务的重试逻辑

### 相关命令
```bash
# 处理账号创建任务
python manage.py process_account_creation_tasks

# 预览模式
python manage.py process_account_creation_tasks --dry-run

# 设置最大处理任务数
python manage.py process_account_creation_tasks --max-tasks 100
```

### API接口
```http
POST /task-management/process-account-tasks/
Content-Type: application/json

{
    "mode": "run",
    "max_tasks": 100
}
```

### 重试机制
- 失败任务自动标记为'retry'状态
- 记录详细错误信息和堆栈跟踪
- 指数退避重试策略
- 达到最大重试次数后标记为'failed'

## 调度器特性

### 独立控制
- 每个调度器可单独启用/禁用
- 通过数据库配置动态调整，无需重启服务

### 频率配置
- 每个调度器的检查间隔可单独配置
- 支持分钟级别的精确控制

### 状态监控
- 每个调度器独立记录执行日志
- 提供详细的执行统计信息
- 支持通过API查询当前状态

### 错误恢复
- 网络异常自动重试
- 数据一致性检查和修复
- 失败任务的手动重新触发

## 配置参数

### 系统功能开关
- `hr_sync_enabled`: HR同步功能开关
- `task_auto_creation_enabled`: 任务自动创建开关
- `task_processing_enabled`: 任务处理开关
- `account_creation_enabled`: 账号创建功能总开关

### 执行参数
- `hr_sync_interval_minutes`: HR同步间隔（默认10分钟）
- `task_creation_interval_minutes`: 任务创建检查间隔（默认10分钟）
- `task_processing_interval_minutes`: 任务处理间隔（默认5分钟）

### 数据参数
- `valid_employee_statuses`: 有效员工状态列表
- `account_creation_max_retries`: 最大重试次数
- `max_tasks_per_batch`: 每批最大任务数

## 监控和日志

### 日志分类
- **同步日志**: HR数据同步的详细记录
- **任务日志**: 账号创建任务的执行记录
- **错误日志**: 失败任务的错误详情和堆栈跟踪

### 监控指标
- 同步成功率和处理数量
- 任务创建和完成统计
- 失败任务数量和错误类型分布
- 系统性能指标（响应时间、吞吐量）

---

*最后更新: 2026-01-17*
*AccountSync v1.0*</content>
<parameter name="filePath">C:\Users\Administrator\Desktop\accountsync\SYNC_TASKS.md