from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship
from database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, default="Ученик")
    grade = Column(Integer, nullable=True)
    target_score = Column(Integer, nullable=True)
    current_level = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    attempts = relationship("Attempt", back_populates="student")
    errors = relationship("Error", back_populates="student")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True)
    description = Column(Text, nullable=True)

    task_groups = relationship(
        "TaskGroup", back_populates="subject",
        cascade="all, delete-orphan",
        order_by="TaskGroup.task_number",
    )


class TaskGroup(Base):
    __tablename__ = "task_groups"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    task_number = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    subject = relationship("Subject", back_populates="task_groups")
    topics = relationship(
        "Topic", back_populates="task_group",
        cascade="all, delete-orphan",
        order_by="Topic.order_index",
    )


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    task_group_id = Column(Integer, ForeignKey("task_groups.id"), nullable=False)
    name = Column(String(200), nullable=False)
    order_index = Column(Integer, default=0)
    description = Column(Text, nullable=True)

    # ★ НОВОЕ — для плана и повторений
    mastered_at = Column(DateTime, nullable=True)          # когда закрыта 5/5
    mastery_level = Column(Float, default=0.0)             # 0–100
    last_reviewed_at = Column(DateTime, nullable=True)     # последнее повторение
    next_review_at = Column(DateTime, nullable=True)       # когда повторить

    task_group = relationship("TaskGroup", back_populates="topics")
    tasks = relationship("Task", back_populates="topic")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    difficulty = Column(Integer, default=1)
    explanation = Column(Text, nullable=True)

    topic = relationship("Topic", back_populates="tasks")
    attempts = relationship("Attempt", back_populates="task")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, default=False)
    time_spent = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="attempts")
    task = relationship("Task", back_populates="attempts")


class Error(Base):
    __tablename__ = "errors"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ★ НОВОЕ — для анализа ошибок
    error_type = Column(String(50), nullable=True)      # theory_gap / formula / calculation / attention / ...
    severity = Column(Integer, default=1)               # 1–5
    number_of_repeats = Column(Integer, default=1)      # сколько раз повторилась
    next_review_at = Column(DateTime, nullable=True)    # когда переспросить

    student = relationship("Student", back_populates="errors")


# ============================================================
# ★ НОВЫЕ ТАБЛИЦЫ ДЛЯ ПЛАНА
# ============================================================

class PlanPhase(Base):
    """Фаза плана: 'Разгон', 'Алгебра и механика', 'Экзамен'..."""
    __tablename__ = "plan_phases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, default=0)

    days = relationship(
        "DayPlan", back_populates="phase",
        cascade="all, delete-orphan",
        order_by="DayPlan.date",
    )


class DayPlan(Base):
    """План на конкретный день."""
    __tablename__ = "day_plans"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    phase_id = Column(Integer, ForeignKey("plan_phases.id"), nullable=True)
    mode = Column(String(20), default="NORMAL")        # NORMAL / LIGHT / MINIMUM
    minutes_planned = Column(Integer, default=60)
    minutes_done = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    phase = relationship("PlanPhase", back_populates="days")
    items = relationship(
        "DayPlanItem", back_populates="day",
        cascade="all, delete-orphan",
    )


class DayPlanItem(Base):
    """Конкретный пункт плана дня."""
    __tablename__ = "day_plan_items"

    id = Column(Integer, primary_key=True, index=True)
    day_plan_id = Column(Integer, ForeignKey("day_plans.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    type = Column(String(30), default="new")           # new / review / weak / practice / diagnostic
    priority = Column(Integer, default=3)              # 1 = высший, 5 = низший
    minutes_planned = Column(Integer, default=15)
    minutes_done = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    source = Column(String(30), default="calendar")    # calendar / interval / error / adaptation

    day = relationship("DayPlan", back_populates="items")


class IntervalReview(Base):
    """Интервальное повторение (1 / 3 / 7 / 21 / 60 дней)."""
    __tablename__ = "interval_reviews"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    interval_days = Column(Integer, nullable=False)    # 1, 3, 7, 21, 60
    scheduled_at = Column(DateTime, nullable=False)    # когда должно быть
    completed_at = Column(DateTime, nullable=True)     # когда реально сделано
    result_pct = Column(Float, nullable=True)          # 0–100 (как решил)
    next_interval_days = Column(Integer, nullable=True)


class StudySession(Base):
    """Реальная сессия занятий — для адаптации нагрузки."""
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    minutes_spent = Column(Integer, default=0)
    mood = Column(String(20), nullable=True)           # ok / tired / exhausted
    tasks_done = Column(Integer, default=0)