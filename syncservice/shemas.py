from ninja import Schema
from datetime import datetime

# 用于创建任务的输入 Schema
class TaskIn(Schema):
    title: str
    completed: bool = False  # 默认为 False

# 用于列表展示和详情的输出 Schema
class TaskOut(Schema):
    id: int
    title: str
    completed: bool
    created_at: datetime
