"""
Логика ежедневного планировщика.
Пока без ИИ — работает по правилам.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Student, Subject, TaskGroup, Topic, Task, Attempt, Error


def get_today_plan(db: Session, minutes_available: int = 60) -> dict:
    student = db.query(Student).first()
    if not student:
        return {"error": "Ученик не найден. Заполни профиль."}

    plan_items = []
    minutes_left = minutes_available
    used_topic_ids = set()

    # 1. ПОВТОРЕНИЕ: ошибки за 7 дней
    recent_errors = (
        db.query(Error)
        .filter(Error.student_id == student.id)
        .filter(Error.created_at >= datetime.utcnow() - timedelta(days=7))
        .all()
    )
    for err in recent_errors:
        if err.topic_id and err.topic_id not in used_topic_ids:
            topic = db.get(Topic, err.topic_id)
            if topic:
                used_topic_ids.add(err.topic_id)
                plan_items.append({
                    "type": "review", "type_label": "Повторение",
                    "topic_id": topic.id, "topic_name": topic.name,
                    "minutes": 10, "reason": "Была ошибка за последние 7 дней",
                })
                minutes_left -= 10
                if minutes_left <= 0:
                    break

    # 2. СЛАБЫЕ ТЕМЫ
    if minutes_left > 0:
        weak_rows = (
            db.query(Error.topic_id)
            .filter(Error.student_id == student.id)
            .filter(Error.topic_id.isnot(None))
            .all()
        )
        counts = {}
        for row in weak_rows:
            counts[row[0]] = counts.get(row[0], 0) + 1
        sorted_weak = sorted(counts.items(), key=lambda x: -x[1])

        for tid, cnt in sorted_weak:
            if minutes_left < 15 or tid in used_topic_ids:
                continue
            topic = db.get(Topic, tid)
            if topic:
                used_topic_ids.add(tid)
                plan_items.append({
                    "type": "weak", "type_label": "Слабая тема",
                    "topic_id": topic.id, "topic_name": topic.name,
                    "minutes": 15, "reason": f"Ошибок: {cnt}",
                })
                minutes_left -= 15
            if minutes_left <= 0:
                break

    # 3. НОВЫЕ ТЕМЫ
    if minutes_left > 0:
        attempted_ids = (
            db.query(Task.topic_id)
            .join(Attempt, Attempt.task_id == Task.id)
            .filter(Attempt.student_id == student.id)
            .distinct()
            .all()
        )
        attempted_set = {a[0] for a in attempted_ids} | used_topic_ids

        new_topics = (
            db.query(Topic)
            .filter(~Topic.id.in_(attempted_set))
            .order_by(Topic.id)
            .limit(5)
            .all()
        )

        for topic in new_topics:
            if minutes_left < 20:
                break
            plan_items.append({
                "type": "new", "type_label": "Новая тема",
                "topic_id": topic.id, "topic_name": topic.name,
                "minutes": 20, "reason": "Ещё не проходил",
            })
            minutes_left -= 20

    return {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "student_name": student.name,
        "minutes_total": minutes_available,
        "minutes_planned": minutes_available - minutes_left,
        "items": plan_items,
    }


def get_week_plan(db: Session) -> dict:
    days = []
    names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for i in range(7):
        date = datetime.utcnow() + timedelta(days=i)
        days.append({
            "date": date.strftime("%Y-%m-%d"),
            "day_name": names[date.weekday()],
            "planned": 60,
        })
    return {"days": days}