from datetime import datetime
from pydantic import BaseModel


class StudentOut(BaseModel):
    id: int
    name: str
    grade: int | None
    target_score: int | None
    current_level: float
    created_at: datetime

    class Config:
        from_attributes = True


class StudentIn(BaseModel):
    name: str
    grade: int | None = None
    target_score: int | None = None


class TopicOut(BaseModel):
    id: int
    name: str
    order_index: int
    description: str | None = None

    class Config:
        from_attributes = True


class TaskGroupOut(BaseModel):
    id: int
    task_number: int
    name: str
    description: str | None = None
    topics: list[TopicOut] = []

    class Config:
        from_attributes = True


class SubjectOut(BaseModel):
    id: int
    name: str
    code: str | None
    description: str | None = None
    task_groups: list[TaskGroupOut] = []

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    students: int
    subjects: int
    topics: int
    tasks: int
    attempts: int
    errors: int