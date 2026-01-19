# AccountSync项目PostgreSQL数据库切换及启动教程

## 项目概述

AccountSync是一个基于Django REST Framework的HR账号自动化管理系统，支持PostgreSQL和SQLite数据库。

## 前置要求

- Python 3.13+
- PostgreSQL 12+
- pip包管理器

## 步骤1: PostgreSQL数据库准备

### 1.1 安装PostgreSQL

**Windows:**
```bash
# 下载并安装PostgreSQL
# https://www.postgresql.org/download/windows/

# 或者使用Chocolatey
choco install postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**macOS:**
```bash
brew install postgresql
```

### 1.2 创建数据库和用户

```sql
-- 连接到PostgreSQL
psql -U postgres

-- 创建数据库
CREATE DATABASE accountsync;

-- 创建用户
CREATE USER accountsync WITH PASSWORD 'your_password';

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE accountsync TO accountsync;

-- 退出
\q
```

## 步骤2: 项目环境配置

### 2.1 克隆项目（如果尚未克隆）

```bash
git clone <repository-url>
cd accountsync
```

### 2.2 配置环境变量

编辑 `.env` 文件：

```bash
# Database Configuration
DB_NAME=accountsync
DB_USER=accountsync
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

> **注意**: 确保密码与步骤1.2中创建的用户密码一致

### 2.3 修改Django设置

编辑 `accountsync/settings.py`，取消注释PostgreSQL配置并注释掉SQLite配置：

```python
# 注释掉SQLite配置
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# 启用PostgreSQL配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}
```

## 步骤3: 安装依赖

```bash
# 安装Python依赖（包含PostgreSQL驱动）
pip install -r requirements.txt
```

## 步骤4: 数据库迁移

### 4.1 执行Django迁移

```bash
# 生成迁移文件（如果有新的模型变更）
python manage.py makemigrations

# 执行迁移
python manage.py migrate
```

### 4.2 初始化系统配置

```bash
# 初始化同步配置
python manage.py init_sync_config
```

## 步骤5: 启动服务

AccountSync需要启动三个服务：

### 5.1 启动Django开发服务器

```bash
# 终端1: 启动Web服务器
python manage.py runserver
```

### 5.2 启动Celery Worker（异步任务处理）

**Linux/macOS:**
```bash
# 终端2: 启动Celery Worker
./scripts/start_celery_worker.sh
```

**Windows:**
```bash
# 终端2: 启动Celery Worker
celery -A accountsync worker --loglevel=info --concurrency=2 --queues=hr_sync,account_tasks,account_processing --hostname=accountsync-worker@%h
```

### 5.3 启动Celery Beat（定时任务调度）

**Linux/macOS:**
```bash
# 终端3: 启动Celery Beat
./scripts/start_celery_beat.sh
```

**Windows:**
```bash
# 终端3: 启动Celery Beat
celery -A accountsync beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
```

## 步骤6: 验证安装

### 6.1 访问系统

- **Web界面**: http://localhost:8000
- **Admin后台**: http://localhost:8000/admin/

### 6.2 创建超级用户

```bash
python manage.py createsuperuser
```

### 6.3 验证数据库连接

```bash
# 检查Django系统
python manage.py check

# 查看迁移状态
python manage.py showmigrations
```

## 常见问题解决

### PostgreSQL连接问题

1. **确保PostgreSQL服务正在运行**
   ```bash
   # Windows
   net start postgresql-x64-15

   # Linux
   sudo systemctl status postgresql
   ```

2. **检查连接参数**
   ```bash
   # 测试数据库连接
   psql -h localhost -p 5432 -U accountsync -d accountsync
   ```

### 依赖安装问题

```bash
# 如果psycopg2安装失败，尝试
pip install psycopg2-binary
```

### 迁移问题

```bash
# 如果迁移失败，尝试重置
python manage.py migrate --run-syncdb
```

## 项目结构说明

- **accountsync/**: Django项目主目录
- **syncservice/**: 核心业务应用
- **scripts/**: 启动脚本
- **logs/**: 日志文件目录
- **.env**: 环境变量配置

## 定时任务说明

系统默认配置了以下定时任务：
- HR数据同步：每10分钟执行一次
- 账号任务创建：每10分钟执行一次
- 账号任务处理：每5分钟执行一次

## 后续操作

1. 根据实际需求修改 `.env` 文件中的配置
2. 在Admin后台配置HR同步和账号创建相关参数
3. 监控日志文件：`logs/hr_sync.log`

---

**注意**: 生产环境部署时，请确保：
- 修改 `SECRET_KEY`
- 设置 `DEBUG = False`
- 配置适当的 `ALLOWED_HOSTS`
- 使用更安全的数据库用户权限
- 配置日志轮转和备份策略