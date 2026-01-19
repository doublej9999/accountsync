# AccountSync项目离线部署包
# 生成时间: 2026-01-19
# 目标平台: Linux (manylinux2014_x86_64)
# Python版本: 3.13

## 包含的依赖包:
- Django >= 5.0
- Django REST Framework >= 3.14
- django-filter >= 24.0
- drf-spectacular >= 0.27
- django-safedelete >= 1.3
- django-unfold >= 0.40.0
- python-dotenv >= 1.0
- requests >= 2.28
- pypinyin >= 0.49.0
- celery >= 5.3.0
- django-celery-beat >= 2.5.0
- django-celery-results >= 2.6.0
- psycopg2-binary >= 2.9

## 使用方法:
1. 将整个offline-deployment目录复制到Linux服务器
2. 运行: chmod +x install.sh && ./install.sh
3. 按照提示完成安装

## 注意事项:
- 确保Linux系统已安装Python 3.13
- 如需PostgreSQL支持，请先安装postgresql-devel包
- 建议在虚拟环境中安装以避免依赖冲突

离线部署包已生成
文件位置
压缩包: offline-deployment.tar.gz (1.5MB)
解压目录: offline-deployment/
包含内容
✅ 15个wheel包 - 适用于Linux的二进制包
✅ 安装脚本 - install.sh (自动安装)
✅ 依赖清单 - requirements.txt
✅ 说明文档 - README.md
✅ 部署总结 - summary.txt
Linux部署步骤
# 1. 上传压缩包到Linux服务器
scp offline-deployment.tar.gz user@linux-server:/path/to/

# 2. 解压并进入目录
tar -xzf offline-deployment.tar.gz
cd offline-deployment/

# 3. 运行安装脚本
chmod +x install.sh
./install.sh