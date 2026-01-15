from ninja import NinjaAPI
from typing import List
from django.shortcuts import get_object_or_404
from .models import Task
from .shemas import TaskOut, TaskIn

# 初始化 Ninja API 实例
api = NinjaAPI()

# ---------- READ (List) ----------
@api.get("/tasks", response=List[TaskOut])
def list_tasks(request):
    """获取所有任务"""
    return Task.objects.all()

# ---------- CREATE ----------
@api.post("/tasks", response=TaskOut)
def create_task(request, payload: TaskIn):
    """创建新任务"""
    # payload 是经过 Pydantic 验证后的数据
    task = Task.objects.create(**payload.dict())
    return task

# ---------- READ (Detail) ----------
@api.get("/tasks/{task_id}", response=TaskOut)
def get_task(request, task_id: int):
    """获取单个任务详情"""
    task = get_object_or_404(Task, id=task_id)
    return task

# ---------- UPDATE ----------
@api.put("/tasks/{task_id}", response=TaskOut)
def update_task(request, task_id: int, payload: TaskIn):
    """更新任务"""
    task = get_object_or_404(Task, id=task_id)
    # 遍历 payload 中的字段进行更新
    for attr, value in payload.dict().items():
        setattr(task, attr, value)
    task.save()
    return task

# ---------- DELETE ----------
@api.delete("/tasks/{task_id}")
def delete_task(request, task_id: int):
    """删除任务"""
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    # 通常删除操作返回 204 No Content，或者返回一个空字典
    return {"success": True}
