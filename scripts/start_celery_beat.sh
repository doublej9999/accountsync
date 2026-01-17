#!/bin/bash

# Celery Beat 启动脚本
# 用于定时任务调度

# 设置Django环境变量
export DJANGO_SETTINGS_MODULE=accountsync.settings

# 启动beat调度器
# -A 指定Celery应用
# --loglevel 设置日志级别
# --scheduler 指定调度器类型

celery -A accountsync beat \
    --loglevel=info \
    --scheduler=django_celery_beat.schedulers:DatabaseScheduler