# 账号创建接口优化方案

## 概述

本方案通过引入请求缓冲区机制，实现了 `create_accounts` 对外接口与定时任务的完全解耦，避免了数据冲突问题。

## 架构设计

### 核心思路

```
create_accounts 接口 → 请求缓冲区 → 定时任务统一处理
```

### 数据模型

#### 1. AccountCreationRequest（账号创建请求）

存储接口接收的创建请求元数据：

| 字段 | 类型 | 说明 |
|------|------|------|
| request_id | CharField | 唯一请求ID |
| origin_system | CharField | 来源系统 |
| business_key | CharField | 业务键 |
| account_type | CharField | 账号类型 |
| employee_type | CharField | 员工类型 |
| system_list | JSONField | 系统列表 (idaas, welink, email) |
| status | CharField | 状态 (pending/processing/completed/partial_failed/failed) |
| total_users | IntegerField | 总用户数 |
| processed_users | IntegerField | 已处理用户数 |
| error_summary | JSONField | 错误摘要 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |
| completed_at | DateTimeField | 完成时间 |

#### 2. AccountCreationRequestItem（账号创建请求项）

存储请求中的每个用户数据：

| 字段 | 类型 | 说明 |
|------|------|------|
| request | ForeignKey | 关联请求 |
| employee_number | CharField | 员工编号 |
| employee_name | CharField | 员工姓名 |
| department_code | CharField | 部门代码 |
| phone_number | CharField | 电话号码 |
| partner_company | CharField | 合作公司 |
| country | CharField | 国家 |
| status | CharField | 状态 (pending/synced/task_created/completed/failed) |
| hr_person | ForeignKey | 关联的HR人员 |
| error_message | TextField | 错误信息 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

### 定时任务处理流程

#### 1. sync_hr_persons_task（HR数据同步）

**处理流程：**

1. **处理账号创建请求缓冲区**
   - 查询所有 `status='pending'` 的 AccountCreationRequest
   - 更新请求状态为 `processing`
   - 遍历请求中的每个用户（AccountCreationRequestItem）
     - 根据请求项数据创建或更新 HrPerson
     - 标记来源为 `account_creation_api`
     - 更新请求项状态为 `synced`
     - 如果是新创建的人员，创建默认账号记录
   - 更新请求的已处理用户数

2. **同步HR系统数据**（原有逻辑保持不变）

**关键代码：** `syncservice/management/commands/sync_hr_persons.py:26`

```python
def _process_account_creation_requests(self):
    """处理账号创建请求缓冲区"""
    pending_requests = AccountCreationRequest.objects.filter(status='pending')

    for request in pending_requests:
        request.update_status('processing')

        items = request.items.filter(status='pending')
        for item in items:
            # 创建或更新 HrPerson
            person, created = HrPerson.objects.update_or_create(
                employee_number=item.employee_number,
                defaults={
                    'person_id': person_id_int,
                    'full_name': item.employee_name,
                    'telephone_number1': item.phone_number,
                    'person_type': request.account_type,
                    'employee_status': request.employee_type,
                    'tenant_id': request.business_key,
                    'created_by': 'account_creation_api',
                    'last_updated_by': 'account_creation_api',
                    'creation_date': timezone.now(),
                    'last_update_date': timezone.now(),
                    'person_dept': [{
                        'department_code': item.department_code,
                        'partner_company': item.partner_company or '',
                        'country': item.country
                    }]
                }
            )

            item.hr_person = person
            item.status = 'synced'
            item.save()
```

#### 2. create_account_tasks_task（账号任务创建）

**处理流程：**

1. **处理账号创建请求中的用户**
   - 查询所有 `status='processing'` 的 AccountCreationRequest
   - 获取已同步但未创建任务的请求项（`status='synced'`）
   - 为这些用户创建 AccountCreationTask
   - 更新请求项状态为 `task_created`
   - 检查是否所有请求项都已完成，更新请求状态

2. **处理HR同步的用户**（原有逻辑保持不变）

**关键代码：** `syncservice/management/commands/create_account_tasks.py:26`

```python
def _process_account_creation_requests(self, dry_run=False):
    """处理账号创建请求，为已同步的用户创建账号任务"""
    requests = AccountCreationRequest.objects.filter(status='processing')

    for request in requests:
        items = request.items.filter(status='synced')

        for item in items:
            person = item.hr_person
            system_list = request.system_list

            # 创建账号任务
            tasks_for_person = self._get_tasks_for_person(person, system_list)
            if tasks_for_person:
                person_tasks = self._create_tasks_for_person(person, tasks_for_person)
                item.status = 'task_created'
                item.save()

        # 更新请求状态
        self._update_request_status(request)
```

#### 3. process_account_creation_tasks_task（账号任务处理）

保持不变，处理所有 AccountCreationTask 的执行。

## API 接口

### 1. 创建账号请求

**端点：** `POST /account-creation/create_accounts/`

**请求示例：**

```json
{
  "originSystem": "HR_SYSTEM",
  "businessKey": "BATCH_20250121_001",
  "accountType": "供应商",
  "employeeType": "1",
  "systemList": ["idaas", "welink", "email"],
  "userList": [
    {
      "employeeNumber": "TEST001",
      "employeeName": "张三",
      "departmentCode": "D001",
      "phoneNumber": "13800138001",
      "partnerCompany": "测试公司",
      "country": "中国"
    },
    {
      "employeeNumber": "TEST002",
      "employeeName": "李四",
      "departmentCode": "D002",
      "phoneNumber": "13800138002",
      "partnerCompany": "测试公司",
      "country": "中国"
    }
  ]
}
```

**响应示例：**

```json
{
  "success": true,
  "requestId": "req_20250121_abc123def456",
  "status": "pending",
  "totalUsers": 2,
  "message": "请求已提交，正在处理中"
}
```

### 2. 查询请求状态

**端点：** `GET /account-creation/requests/{request_id}/`

**响应示例：**

```json
{
  "requestId": "req_20250121_abc123def456",
  "originSystem": "HR_SYSTEM",
  "businessKey": "BATCH_20250121_001",
  "accountType": "供应商",
  "employeeType": "1",
  "systemList": ["idaas", "welink", "email"],
  "status": "completed",
  "status_display": "已完成",
  "totalUsers": 2,
  "processedUsers": 2,
  "progress": "100.0%",
  "errorSummary": null,
  "createdAt": "2025-01-21T10:00:00Z",
  "updatedAt": "2025-01-21T10:05:00Z",
  "completedAt": "2025-01-21T10:05:00Z",
  "items": [
    {
      "id": 1,
      "employeeNumber": "TEST001",
      "employeeName": "张三",
      "departmentCode": "D001",
      "phoneNumber": "13800138001",
      "partnerCompany": "测试公司",
      "country": "中国",
      "status": "completed",
      "status_display": "已完成",
      "hrPersonInfo": {
        "employeeNumber": "TEST001",
        "fullName": "张三",
        "email": "zhangsan@example.com"
      },
      "errorMessage": null,
      "createdAt": "2025-01-21T10:00:00Z",
      "updatedAt": "2025-01-21T10:05:00Z"
    }
  ]
}
```

## 状态流转

### AccountCreationRequest 状态流转

```
pending → processing → completed
           ↓           ↓
        partial_failed
           ↓
        failed
```

- **pending**: 初始状态，等待处理
- **processing**: 正在处理中
- **completed**: 所有用户都成功处理
- **partial_failed**: 部分用户处理失败
- **failed**: 所有用户都处理失败

### AccountCreationRequestItem 状态流转

```
pending → synced → task_created → completed
          ↓
        failed
```

- **pending**: 初始状态
- **synced**: HR人员数据已同步
- **task_created**: 账号任务已创建
- **completed**: 账号创建完成
- **failed**: 处理失败

## 测试

### 测试脚本

使用 `test_new_api.py` 进行测试：

```bash
python test_new_api.py
```

### 手动触发定时任务

为了快速测试，可以手动触发定时任务：

```bash
# 触发HR数据同步（会处理请求缓冲区）
python manage.py sync_hr_persons

# 触发账号任务创建
python manage.py create_account_tasks

# 触发账号任务处理
python manage.py process_account_creation_tasks
```

或通过 API：

```bash
# 触发HR数据同步
POST /task-management/sync_hr_persons/
{
  "mode": "run"
}

# 触发账号任务创建
POST /task-management/create_account_tasks/
{
  "mode": "run"
}

# 触发账号任务处理
POST /task-management/process_account_tasks/
{
  "mode": "run"
}
```

## 管理后台

新模型已注册到 Django Admin，可以访问：

- `/admin/syncservice/accountcreationrequest/` - 查看所有账号创建请求
- `/admin/syncservice/accountcreationrequestitem/` - 查看所有请求项

## 优点

1. ✅ **完全避免数据冲突**：接口和定时任务操作不同的数据模型
2. ✅ **统一处理逻辑**：所有数据都通过定时任务处理，逻辑一致
3. ✅ **异步执行**：接口快速返回，用户体验好
4. ✅ **可追溯**：完整的请求处理记录
5. ✅ **可扩展**：易于添加新的数据源或处理逻辑
6. ✅ **可监控**：可以通过请求状态和进度实时查看处理情况

## 注意事项

1. **定时任务频率**：建议设置为 5-10 分钟
2. **请求清理**：需要定期清理已完成的旧请求（建议保留 30 天）
3. **错误处理**：失败的任务会记录在 `error_summary` 中，方便排查问题

## 实施步骤

1. ✅ 创建数据模型（AccountCreationRequest, AccountCreationRequestItem）
2. ✅ 创建数据库迁移
3. ✅ 更新序列化器
4. ✅ 修改 create_accounts 接口
5. ✅ 添加查询接口
6. ✅ 修改定时任务（sync_hr_persons, create_account_tasks）
7. ✅ 注册管理后台
8. ✅ 测试验证

## 后续优化建议

1. **请求限流**：添加限流机制，防止短时间内大量请求
2. **优先级队列**：为不同来源的请求设置不同优先级
3. **重试机制**：失败的请求项支持自动重试
4. **通知机制**：请求完成时发送通知（邮件/消息）
5. **请求取消**：支持取消未处理的请求
6. **数据校验**：在接口接收时进行更严格的数据校验

---

*最后更新: 2025-01-21*
*Django 版本: 5.0+*
*Python 版本: 3.13*
