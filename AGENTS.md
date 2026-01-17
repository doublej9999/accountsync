# AGENTS.md - AccountSync 项目开发指南

本文件为 AccountSync 项目的代理编码助手提供开发指南，包含构建、测试、代码风格等关键信息。

## 项目概述

AccountSync 是一个基于 Django REST Framework (DRF) 的 Web API 项目，实现完整的HR数据同步和账号自动创建系统。

- **技术栈**: Django 5.0+, Django REST Framework, PostgreSQL/SQLite
- **主要依赖**: django-filter, drf-spectacular, django-safedelete, django-unfold
- **核心功能**: HR数据同步、账号自动创建、任务队列处理

## 构建和运行命令

### 开发服务器
```bash
# 启动开发服务器
python manage.py runserver

# 指定端口和主机
python manage.py runserver 0.0.0.0:8000
```

### 数据库操作
```bash
# 创建迁移文件
python manage.py makemigrations

# 应用迁移
python manage.py migrate

# 显示迁移状态
python manage.py showmigrations
```

### 测试命令

#### 运行所有测试
```bash
python manage.py test
```

#### 运行特定应用的测试
```bash
python manage.py test syncservice
```

#### 运行单个测试类 ⭐重点
```bash
python manage.py test syncservice.tests.TestClassName
```

#### 运行单个测试方法 ⭐重点
```bash
python manage.py test syncservice.tests.TestClassName.test_method_name
```

#### 测试选项
```bash
# 详细输出 (-v 0=quiet, 1=normal, 2=verbose)
python manage.py test -v 2

# 首次失败时停止
python manage.py test --failfast

# 并行运行测试
python manage.py test --parallel auto

# 只运行匹配的测试 (支持正则表达式)
python manage.py test -k "test_name"

# 保持测试数据库 (复用数据库避免重复创建)
python manage.py test --keepdb
```

### 代码检查和验证

#### Django 系统检查
```bash
# 检查整个项目
python manage.py check

# 检查特定应用
python manage.py check syncservice

# 部署检查
python manage.py check --deploy
```

#### API 文档生成
```bash
# 生成 OpenAPI schema
python manage.py spectacular --file schema.yml
```

### 管理命令
```bash
# 初始化同步配置
python manage.py init_sync_config

# 创建超级用户
python manage.py createsuperuser

# 收集静态文件
python manage.py collectstatic
```

## 代码风格指南

### 导入规范

按照以下顺序组织导入语句：

```python
# 1. 标准库导入
import os
from pathlib import Path

# 2. Django 核心导入
from django.db import models
from django.urls import path

# 3. 第三方库导入 (按字母顺序)
from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet

# 4. 本地应用导入
from .models import HrPerson
from .serializers import HrPersonSerializer
```

### 命名约定

#### 变量和函数
- 使用 `snake_case` 命名
- 函数名应描述其功能

```python
# 变量和函数: snake_case
def get_active_persons():
    return HrPerson.objects.filter(employee_status='active')

# 类: PascalCase
class HrPerson(models.Model):
    pass

# 常量: UPPER_CASE
DEFAULT_PAGE_SIZE = 10
```

### 错误处理

#### 使用 get_object_or_404
```python
from django.shortcuts import get_object_or_404

def get_person(request, person_id):
    person = get_object_or_404(HrPerson, id=person_id)
    return person
```

#### DRF 异常处理
```python
from rest_framework.exceptions import ValidationError

class HrPersonViewSet(ModelViewSet):
    def perform_create(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError("人员创建失败：数据完整性错误")
```

### 测试编写

```python
# 模型测试
class HrPersonModelTest(TestCase):
    def test_person_creation(self):
        self.assertEqual(self.person.employee_number, "001")

# API 测试
class HrPersonAPITest(APITestCase):
    def test_list_persons(self):
        response = self.client.get('/api/hr-persons/')
        self.assertEqual(response.status_code, 200)
```

### 安全注意事项

- 密码和密钥使用环境变量，不在代码中硬编码
- 使用 .env 文件管理环境变量
- API 权限控制使用 `IsAuthenticated` 等权限类

---

*最后更新: 2026-01-17*
*Django 版本: 5.0+*
*Python 版本: 3.13*</content>
