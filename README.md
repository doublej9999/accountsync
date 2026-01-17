# AccountSync

HR账号自动化管理系统

## 快速启动

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 初始化配置
python manage.py init_sync_config
```

### 2. 启动服务

**开发环境需要启动三个服务:**

```bash
# 终端1: 启动Django开发服务器
python manage.py runserver

# 终端2: 启动Celery Worker (处理异步任务)
./scripts/start_celery_worker.sh

# 终端3: 启动Celery Beat (定时任务调度)
./scripts/start_celery_beat.sh
```

### 3. 访问系统

- Web界面: http://localhost:8000
- Admin后台: http://localhost:8000/admin/

## 架构说明

- **Django**: Web框架和API
- **Celery**: 异步任务队列
- **Redis**: 消息代理
- **PostgreSQL/SQLite**: 数据库

## 详细文档

- [Celery部署指南](CELERY_DEPLOYMENT.md)
- [API文档](AGENTS.md)