#!/bin/bash

# Celery Worker 启动脚本
# 用于处理异步任务

# 设置Django环境变量
export DJANGO_SETTINGS_MODULE=accountsync.settings

# 启动worker
# -A 指定Celery应用
# --loglevel 设置日志级别
# --concurrency 设置并发数
# --queues 指定监听的队列

celery -A accountsync worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=hr_sync,account_tasks,account_processing \
    --hostname=accountsync-worker@%h