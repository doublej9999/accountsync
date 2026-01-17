# AccountSync Celery 部署指南

## 概述

本项目已成功移除 `HrSyncMiddleware` 中间件，并使用 Celery Beat 替代，实现真正的异步定时任务调度。

## 架构变更

### 移除内容
- ❌ `syncservice.middleware.HrSyncMiddleware` - 每次请求中执行定时任务检查
- ❌ `syncservice/middleware.py` 文件

### 新增内容
- ✅ Celery 配置 (`accountsync/celery.py`)
- ✅ Celery 任务定义 (`syncservice/tasks.py`)
- ✅ 启动脚本 (`scripts/start_celery_*.sh`)

## 依赖要求

### 系统要求
- **开发环境**: 无需额外服务（使用Django数据库作为消息代理）
- **生产环境**: Redis 或 RabbitMQ 服务器（推荐）
- Python 3.8+

### Python 包
```
celery>=5.3.0
django-celery-beat>=2.5.0
django-celery-results>=2.6.0
# redis>=4.5.0  # 生产环境需要，开发环境可选
```

## 定时任务配置

### 任务列表
1. **HR数据同步** (`syncservice.tasks.sync_hr_persons_task`)
   - 执行: `python manage.py sync_hr_persons`
   - 频率: 每10分钟

2. **账号任务创建** (`syncservice.tasks.create_account_tasks_task`)
   - 执行: `python manage.py create_account_tasks`
   - 频率: 每10分钟

3. **账号任务处理** (`syncservice.tasks.process_account_creation_tasks_task`)
   - 执行: `python manage.py process_account_creation_tasks`
   - 频率: 每5分钟

## 部署步骤

### 1. 环境配置

**开发环境:**
无需额外配置，直接使用Django数据库作为消息代理

**生产环境 (推荐使用Redis):**
```bash
# Windows
choco install redis-64

# Linux
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 2. 环境变量配置

**开发环境:**
无需环境变量，使用默认的数据库broker

**生产环境 (使用Redis):**
```bash
export REDIS_URL=redis://localhost:6379/0
```

### 3. 数据库迁移

```bash
python manage.py migrate
```

### 4. 启动服务

#### 开发环境

**终端1: 启动 Celery Worker**
```bash
# 使用脚本启动
./scripts/start_celery_worker.sh

# 或手动启动
celery -A accountsync worker --loglevel=info --concurrency=4 --queues=hr_sync,account_tasks,account_processing
```

**终端2: 启动 Celery Beat**
```bash
# 使用脚本启动
./scripts/start_celery_beat.sh

# 或手动启动
celery -A accountsync beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
```

**终端3: 启动 Django**
```bash
python manage.py runserver
```

#### 生产环境

推荐使用进程管理器如 Supervisor 或 systemd 来管理 Celery 进程。

**Supervisor 配置示例 (`/etc/supervisor/conf.d/accountsync.conf`):**

```ini
[program:accountsync-worker]
command=celery -A accountsync worker --loglevel=info --concurrency=4 --queues=hr_sync,account_tasks,account_processing
directory=/path/to/accountsync
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

[program:accountsync-beat]
command=celery -A accountsync beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
directory=/path/to/accountsync
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

## 监控和维护

### 检查任务状态

```bash
# 查看注册的任务
celery -A accountsync inspect registered

# 查看活跃任务
celery -A accountsync inspect active

# 查看调度状态
celery -A accountsync inspect scheduled
```

### 管理界面

访问 Django Admin 可以查看:
- `/admin/django_celery_beat/` - 定时任务配置
- `/admin/django_celery_results/` - 任务执行结果

### 日志位置

- Celery Worker: `/var/log/celery/worker.log`
- Celery Beat: `/var/log/celery/beat.log`

## 故障排除

### 常见问题

**Q: 数据库broker连接问题**
```bash
# 检查Django数据库连接
python manage.py dbshell

# 确保已运行迁移
python manage.py migrate
```

**Q: Redis 连接失败 (生产环境)**
```bash
# 检查 Redis 服务状态
redis-cli ping

# 启动 Redis 服务
sudo systemctl start redis-server
```

**Q: 任务没有按时执行**
```bash
# 检查 Beat 进程是否运行
ps aux | grep celery

# 查看 Beat 日志
tail -f /var/log/celery/beat.log
```

**Q: 任务执行失败**
```bash
# 查看 Worker 日志
tail -f /var/log/celery/worker.log

# 手动执行任务测试
python manage.py sync_hr_persons
```

### 性能优化

- 根据服务器配置调整 `--concurrency` 参数
- 为不同类型的任务分配专门的队列
- 监控队列长度，避免积压

## 迁移说明

原有中间件的定时任务逻辑已完全迁移到 Celery:
- 不再阻塞 HTTP 请求
- 支持任务失败重试
- 提供更好的监控和调试能力
- 可扩展到分布式部署

## 版本信息

- Django: 5.0+
- Celery: 5.3.0+
- Python: 3.8+
- Redis: 4.5.0+