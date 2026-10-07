import json
import re
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from database import get_db, init_db
from models import (
    Student, Subject, TaskGroup, Topic, Task, Attempt, Error,
    PlanPhase, DayPlan, DayPlanItem,
)
from schemas import StatsOut, StudentOut, StudentIn, SubjectOut
import ai_service

app = FastAPI(title="EGE-TUTOR API", version="0.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    print(">> База данных готова")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ege-tutor-backend"}


@app.get("/api/ping")
async def ping():
    return {"message": "pong", "version": "0.6.0"}


@app.get("/api/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    return StatsOut(
        students=db.query(Student).count(),
        subjects=db.query(Subject).count(),
        topics=db.query(Topic).count(),
        tasks=db.query(Task).count(),
        attempts=db.query(Attempt).count(),
        errors=db.query(Error).count(),
    )


@app.get("/api/student")
def get_student(db: Session = Depends(get_db)):
    student = db.query(Student).first()
    if not student:
        return {"student": None}
    return {"student": StudentOut.model_validate(student).model_dump()}


@app.post("/api/student")
def save_student(payload: StudentIn, db: Session = Depends(get_db)):
    student = db.query(Student).first()
    if student is None:
        student = Student(
            name=payload.name,
            grade=payload.grade,
            target_score=payload.target_score,
        )
        db.add(student)
    else:
        student.name = payload.name
        student.grade = payload.grade
        student.target_score = payload.target_score
    db.commit()
    db.refresh(student)
    return {"student": StudentOut.model_validate(student).model_dump()}


@app.get("/api/subjects", response_model=list[SubjectOut])
def get_subjects(db: Session = Depends(get_db)):
    subjects = (
        db.query(Subject)
        .options(joinedload(Subject.task_groups).joinedload(TaskGroup.topics))
        .order_by(Subject.id)
        .all()
    )
    return subjects


# ============================================================
# ИИ — ЭНДПОИНТЫ
# ============================================================

class AskRequest(BaseModel):
    prompt: str


@app.get("/api/ai/test")
async def ai_test():
    try:
        answer = await ai_service.ask_ai_simple(
            "Ответь одним словом: работает?",
            system="Ты краткий ассистент. Отвечай ровно одним словом без знаков препинания.",
        )
        return {"ok": True, "answer": answer.strip(), "model": ai_service.MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка ИИ: {str(e)}")


@app.post("/api/ai/ask")
async def ai_ask(payload: AskRequest):
    try:
        answer = await ai_service.ask_ai_simple(payload.prompt)
        return {"ok": True, "answer": answer, "model": ai_service.MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка ИИ: {str(e)}")


# ============================================================
# ИИ-УЧИТЕЛЬ ПО ТЕМЕ + ЖУРНАЛ ОШИБОК
# ============================================================

class TutorMessage(BaseModel):
    role: str
    content: str


class TutorRequest(BaseModel):
    subject: str
    task_number: int
    task_name: str
    topic: str
    topic_id: int | None = None
    messages: list[TutorMessage]


def build_tutor_system(subject: str, task_number: int, task_name: str, topic: str) -> str:
    return (
        "Ты — личный репетитор по подготовке к ЕГЭ 2026. Отвечай по-русски, дружелюбно и по делу.\n"
        f"Предмет: {subject}. Задание №{task_number}: {task_name}. Тема: {topic}.\n\n"
        "Правила работы:\n"
        "1. Работай только в рамках этой темы.\n"
        "2. Давай ОДНО задание за раз и жди ответа ученика. Полное условие пиши в сообщении.\n"
        "3. Сложность растёт от 1 до 5: 1 — в одно действие, 5 — очень сложное (уровень ЕГЭ).\n"
        "   Каждое задание помечай: «Задание k из 5».\n"
        "4. Когда ученик отвечает — проверь. Если верно: коротко похвали и предложи следующее.\n"
        "   Если неверно: НЕ давай сразу правильный ответ, найди конкретную ошибку,\n"
        "   объясни её и предложи пересчитать. После двух неудачных попыток покажи полное решение.\n"
        "5. После 5 верных заданий скажи, что тема пройдена, и перечисли слабые места, если они были.\n"
        "6. Формулы пиши обычным текстом и значками Unicode (², √, π, ≤), без LaTeX.\n"
        "7. Пиши коротко: без длинных вступлений.\n"
        "8. СЛУЖЕБНАЯ СТРОКА. После КАЖДОЙ проверки ответа ученика на задание (и только тогда)\n"
        "   в самом конце сообщения добавь одну строку строго такого вида (ученик её не увидит):\n"
        '   <<RESULT {"correct": true, "question": "полное условие проверяемого задания", '
        '"user_answer": "ответ ученика", "correct_answer": "правильный ответ", '
        '"error": "кратко, в чём ошибка (пусто, если верно)"}>>\n'
        "   Значение correct — true или false. Если ученик не отвечал на задание "
        "(просил подсказку, теорию, задал вопрос) — эту строку НЕ добавляй."
    )


RESULT_RE = re.compile(r"<<\s*RESULT\s*(\{.*?\})\s*>>", re.DOTALL)
DANGLING_RE = re.compile(r"<<\s*RESULT.*$", re.DOTALL)


def extract_result(answer: str):
    result = None
    m = RESULT_RE.search(answer)
    if m:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict):
                result = data
        except json.JSONDecodeError:
            result = None
    clean = RESULT_RE.sub("", answer)
    clean = DANGLING_RE.sub("", clean)
    return clean.strip(), result


def to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes", "да", "верно")


def save_result(db: Session, topic_id: int | None, data: dict) -> str | None:
    if not topic_id:
        return None
    topic = db.get(Topic, topic_id)
    question = str(data.get("question") or "").strip()
    if topic is None or not question:
        return None

    student = db.query(Student).first()
    if student is None:
        student = Student(name="Ученик")
        db.add(student)
        db.flush()

    correct = to_bool(data.get("correct"))
    task = db.query(Task).filter_by(topic_id=topic.id, question=question).first()
    if task is None:
        task = Task(
            topic_id=topic.id,
            question=question,
            answer=str(data.get("correct_answer") or ""),
        )
        db.add(task)
        db.flush()

    db.add(Attempt(
        student_id=student.id,
        task_id=task.id,
        user_answer=str(data.get("user_answer") or ""),
        is_correct=correct,
    ))
    if not correct:
        db.add(Error(
            student_id=student.id,
            topic_id=topic.id,
            task_id=task.id,
            description=str(data.get("error") or "").strip() or "Ответ неверный",
        ))
    db.commit()
    return "correct" if correct else "error"


@app.post("/api/ai/tutor")
async def ai_tutor(payload: TutorRequest, db: Session = Depends(get_db)):
    history = [
        {"role": m.role, "content": m.content}
        for m in payload.messages[-24:]
        if m.role in ("user", "assistant") and m.content.strip()
    ]
    if not history:
        raise HTTPException(status_code=400, detail="Пустая история сообщений")

    system = build_tutor_system(
        payload.subject, payload.task_number, payload.task_name, payload.topic
    )
    messages = [{"role": "system", "content": system}] + history

    try:
        raw = await ai_service.ask_ai(messages, temperature=0.5, max_tokens=1500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка ИИ: {str(e)}")

    answer, result = extract_result(raw)

    recorded = None
    if result:
        try:
            recorded = save_result(db, payload.topic_id, result)
        except Exception as e:
            db.rollback()
            print(f">> Не удалось записать результат: {e}")

    return {
        "ok": True,
        "answer": answer,
        "recorded": recorded,
        "model": ai_service.MODEL,
    }


@app.get("/api/errors")
def get_errors(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(Error).order_by(Error.created_at.desc(), Error.id.desc()).limit(limit).all()

    errors = []
    for e in rows:
        task = db.get(Task, e.task_id) if e.task_id else None
        topic = db.get(Topic, e.topic_id) if e.topic_id else None
        tg = db.get(TaskGroup, topic.task_group_id) if topic else None
        subject = db.get(Subject, tg.subject_id) if tg else None

        user_answer = None
        if task:
            att = (
                db.query(Attempt)
                .filter_by(task_id=task.id, is_correct=False)
                .order_by(Attempt.id.desc())
                .first()
            )
            user_answer = att.user_answer if att else None

        errors.append({
            "id": e.id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "subject": subject.name if subject else None,
            "task_number": tg.task_number if tg else None,
            "task_name": tg.name if tg else None,
            "topic": topic.name if topic else None,
            "question": task.question if task else None,
            "user_answer": user_answer,
            "correct_answer": task.answer if task else None,
            "description": e.description,
        })

    err_counts = (
        db.query(Error.topic_id, func.count(Error.id))
        .filter(Error.topic_id.isnot(None))
        .group_by(Error.topic_id)
        .order_by(func.count(Error.id).desc())
        .limit(10)
        .all()
    )
    weak = []
    for topic_id, err_n in err_counts:
        topic = db.get(Topic, topic_id)
        tg = db.get(TaskGroup, topic.task_group_id) if topic else None
        subject = db.get(Subject, tg.subject_id) if tg else None
        attempts_n = (
            db.query(func.count(Attempt.id))
            .join(Task, Attempt.task_id == Task.id)
            .filter(Task.topic_id == topic_id)
            .scalar()
        ) or 0
        weak.append({
            "topic": topic.name if topic else "—",
            "subject": subject.name if subject else None,
            "task_number": tg.task_number if tg else None,
            "errors": err_n,
            "attempts": max(attempts_n, err_n),
        })

    return {"errors": errors, "weak_topics": weak}


# ============================================================
# ПЛАНИРОВЩИК (старый — генерирует на лету)
# ============================================================

import planner_engine


@app.get("/api/planner/today")
def planner_today(minutes: int = 60, db: Session = Depends(get_db)):
    return planner_engine.get_today_plan(db, minutes_available=minutes)


@app.get("/api/planner/week")
def planner_week(db: Session = Depends(get_db)):
    return planner_engine.get_week_plan(db)


# ============================================================
# ПЛАН ИЗ PDF — эндпоинты (по фазам и дням)
# ============================================================

@app.get("/api/plan/phases")
def get_phases(db: Session = Depends(get_db)):
    """Все 32 фазы плана."""
    phases = db.query(PlanPhase).order_by(PlanPhase.order_index).all()
    return [
        {
            "id": p.id,
            "order": p.order_index,
            "name": p.name,
            "start_date": p.start_date.strftime("%Y-%m-%d"),
            "end_date": p.end_date.strftime("%Y-%m-%d"),
            "description": p.description,
        }
        for p in phases
    ]


@app.get("/api/plan/today")
def get_plan_today(db: Session = Depends(get_db)):
    """План на сегодня (или на ближайший день из БД)."""
    today = datetime.utcnow().date()
    day_start = datetime(today.year, today.month, today.day)

    day = (
        db.query(DayPlan)
        .filter(DayPlan.date >= day_start)
        .order_by(DayPlan.date)
        .first()
    )

    if not day:
        return {"error": "План не найден. Запусти import_plan.py"}

    items = []
    for item in day.items:
        topic = db.get(Topic, item.topic_id)
        if not topic:
            continue

        tg = db.get(TaskGroup, topic.task_group_id)
        subject = db.get(Subject, tg.subject_id) if tg else None

        items.append({
            "id": item.id,
            "topic_id": topic.id,
            "topic_name": topic.name,
            "task_group_name": tg.name if tg else None,
            "task_number": tg.task_number if tg else None,
            "subject": subject.name if subject else None,
            "subject_code": subject.code if subject else None,
            "type": item.type,
            "priority": item.priority,
            "minutes": item.minutes_planned,
            "is_completed": item.is_completed,
        })

    phase = db.get(PlanPhase, day.phase_id) if day.phase_id else None

    return {
        "date": day.date.strftime("%Y-%m-%d"),
        "phase": phase.name if phase else None,
        "mode": day.mode,
        "minutes_planned": day.minutes_planned,
        "minutes_done": day.minutes_done,
        "is_completed": day.is_completed,
        "items": items,
    }


@app.get("/api/plan/date/{date_str}")
def get_plan_by_date(date_str: str, db: Session = Depends(get_db)):
    """План на конкретную дату. date_str = '2026-10-06'."""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Формат даты: YYYY-MM-DD")

    day = db.query(DayPlan).filter(
        DayPlan.date >= target,
        DayPlan.date < target + timedelta(days=1),
    ).first()

    if not day:
        raise HTTPException(status_code=404, detail="День не найден в плане")

    items = []
    for item in day.items:
        topic = db.get(Topic, item.topic_id)
        if not topic:
            continue
        tg = db.get(TaskGroup, topic.task_group_id)
        subject = db.get(Subject, tg.subject_id) if tg else None
        items.append({
            "id": item.id,
            "topic_id": topic.id,
            "topic_name": topic.name,
            "task_group_name": tg.name if tg else None,
            "task_number": tg.task_number if tg else None,
            "subject": subject.name if subject else None,
            "subject_code": subject.code if subject else None,
            "minutes": item.minutes_planned,
            "is_completed": item.is_completed,
        })

    phase = db.get(PlanPhase, day.phase_id) if day.phase_id else None

    return {
        "date": day.date.strftime("%Y-%m-%d"),
        "phase": phase.name if phase else None,
        "mode": day.mode,
        "items": items,
    }

# ============================================================
# ОБЩИЙ ЧАТ С ИИ (видит ошибки, слабые темы, профиль)
# ============================================================

class GlobalChatRequest(BaseModel):
    messages: list[TutorMessage]
    topic_id: int | None = None


def build_global_system(db: Session, topic_id: int | None) -> str:
    """Собирает контекст ученика для системного промпта."""
    student = db.query(Student).first()
    student_info = "Ученик пока не заполнил профиль."
    if student:
        student_info = (
            f"Ученик: {student.name}. "
            f"Класс: {student.grade or '—'}. "
            f"Цель: {student.target_score or '—'} баллов. "
            f"Текущий уровень: {student.current_level or 0}/100."
        )

    # Последняя активная тема
    topic_info = "Ученик пока не выбрал тему."
    if topic_id:
        topic = db.get(Topic, topic_id)
        if topic:
            tg = db.get(TaskGroup, topic.task_group_id)
            subject = db.get(Subject, tg.subject_id) if tg else None
            topic_info = (
                f"Сейчас ученик работает над темой: «{topic.name}». "
                f"Предмет: {subject.name if subject else '—'}. "
                f"Задание №{tg.task_number if tg else '—'}: {tg.name if tg else '—'}."
            )

    # Топ-10 ошибок за последние 7 дней
    from datetime import timedelta as _td
    week_ago = datetime.utcnow() - _td(days=7)
    recent_errors = (
        db.query(Error)
        .filter(Error.created_at >= week_ago)
        .order_by(Error.created_at.desc())
        .limit(10)
        .all()
    )

    errors_text = "Ошибок за последнюю неделю нет."
    if recent_errors:
        lines = []
        for e in recent_errors:
            topic = db.get(Topic, e.topic_id) if e.topic_id else None
            tg = db.get(TaskGroup, topic.task_group_id) if topic else None
            subject = db.get(Subject, tg.subject_id) if tg else None
            where = f"{subject.name if subject else '—'} / {topic.name if topic else '—'}"
            desc = e.description or "—"
            lines.append(f"  • {where} — {desc}")
        errors_text = "Ошибки за последнюю неделю:\n" + "\n".join(lines)

    # Слабые темы (топ-5 по ошибкам)
    weak_rows = (
        db.query(Error.topic_id, func.count(Error.id))
        .filter(Error.topic_id.isnot(None))
        .group_by(Error.topic_id)
        .order_by(func.count(Error.id).desc())
        .limit(5)
        .all()
    )

    weak_text = "Слабых тем пока нет."
    if weak_rows:
        lines = []
        for tid, cnt in weak_rows:
            topic = db.get(Topic, tid)
            tg = db.get(TaskGroup, topic.task_group_id) if topic else None
            subject = db.get(Subject, tg.subject_id) if tg else None
            lines.append(
                f"  • {subject.name if subject else '—'} / "
                f"{topic.name if topic else '—'} — {cnt} ошибок"
            )
        weak_text = "Слабые темы (много ошибок):\n" + "\n".join(lines)

    # Статистика
    stats_text = (
        f"Всего попыток: {db.query(Attempt).count()}. "
        f"Всего ошибок: {db.query(Error).count()}. "
        f"Пройдено тем: {db.query(Topic).filter(Topic.mastered_at.isnot(None)).count()}."
    )

    return (
        "Ты — личный ИИ-наставник по подготовке к ЕГЭ 2026. Отвечай по-русски, дружелюбно, кратко и по делу.\n\n"
        "ТЫ ЗНАЕШЬ ПРО УЧЕНИКА СЛЕДУЮЩЕЕ:\n"
        f"{student_info}\n\n"
        f"КОНТЕКСТ ТЕМЫ:\n{topic_info}\n\n"
        f"{errors_text}\n\n"
        f"{weak_text}\n\n"
        f"СТАТИСТИКА:\n{stats_text}\n\n"
        "ПРАВИЛА:\n"
        "1. Учитывай ошибки ученика в ответах. Если он спрашивает про тему, где у него много ошибок — обрати на это внимание.\n"
        "2. Если ученик просит совета по подготовке — опирайся на его слабые темы.\n"
        "3. Если ученик задаёт вопрос по теме, которую недавно решал — используй этот контекст.\n"
        "4. Будь как репетитор: объясняй понятно, без воды, но по-человечески.\n"
        "5. Формулы пиши обычным текстом и значками Unicode (², √, π, ≤), без LaTeX.\n"
        "6. Если не хватает информации — задай уточняющий вопрос.\n"
        "7. Не выдумывай факты про ученика, которых нет в контексте выше."
    )


@app.post("/api/ai/global-chat")
async def ai_global_chat(payload: GlobalChatRequest, db: Session = Depends(get_db)):
    """Общий чат с ИИ — видит ошибки, слабые темы, последнюю тему."""
    history = [
        {"role": m.role, "content": m.content}
        for m in payload.messages[-20:]
        if m.role in ("user", "assistant") and m.content.strip()
    ]
    if not history:
        raise HTTPException(status_code=400, detail="Пустая история сообщений")

    system = build_global_system(db, payload.topic_id)
    messages = [{"role": "system", "content": system}] + history

    try:
        raw = await ai_service.ask_ai(messages, temperature=0.6, max_tokens=1500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка ИИ: {str(e)}")

    return {
        "ok": True,
        "answer": raw,
        "model": ai_service.MODEL,
    }

    # ============================================================
# ГЛАВНАЯ — «Что делать сейчас?»
# ============================================================

@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """Сводка для главной: план дня + прогресс."""
    today = datetime.utcnow().date()
    day_start = datetime(today.year, today.month, today.day)

    # Ближайший день плана
    day = (
        db.query(DayPlan)
        .filter(DayPlan.date >= day_start)
        .order_by(DayPlan.date)
        .first()
    )

    if not day:
        return {"error": "План не найден"}

    # Считаем прогресс дня
    total = len(day.items)
    done = sum(1 for it in day.items if it.is_completed)
    minutes_total = sum(it.minutes_planned for it in day.items)
    minutes_done = sum(it.minutes_done for it in day.items if it.is_completed)

    phase = db.get(PlanPhase, day.phase_id) if day.phase_id else None
    student = db.query(Student).first()

    return {
        "date": day.date.strftime("%Y-%m-%d"),
        "date_human": day.date.strftime("%d.%m.%Y"),
        "phase": phase.name if phase else None,
        "mode": day.mode,
        "student_name": student.name if student else "Ученик",
        "items_total": total,
        "items_done": done,
        "percent": int(done / total * 100) if total else 0,
        "minutes_total": minutes_total,
        "minutes_done": minutes_done,
        "minutes_left": minutes_total - minutes_done,
    }

# ============================================================
# ПРОФИЛЬ — прогресс по предметам
# ============================================================

@app.get("/api/profile-stats")
def get_profile_stats(db: Session = Depends(get_db)):
    """Прогресс по каждому предмету + общая статистика."""
    subjects = db.query(Subject).all()

    by_subject = []
    total_topics_all = 0
    total_done_all = 0

    for subj in subjects:
        topics = []
        for tg in subj.task_groups:
            for t in tg.topics:
                topics.append(t)

        total_topics = len(topics)

        # Пройденные = есть mastered_at
        done = sum(1 for t in topics if t.mastered_at is not None)

        # Ошибки по этому предмету
        topic_ids = [t.id for t in topics]
        errors_count = 0
        attempts_count = 0
        if topic_ids:
            errors_count = (
                db.query(Error)
                .filter(Error.topic_id.in_(topic_ids))
                .count()
            )
            attempts_count = (
                db.query(Attempt)
                .join(Task, Attempt.task_id == Task.id)
                .filter(Task.topic_id.in_(topic_ids))
                .count()
            )

        percent = int(done / total_topics * 100) if total_topics else 0

        by_subject.append({
            "code": subj.code,
            "name": subj.name,
            "total": total_topics,
            "done": done,
            "percent": percent,
            "errors": errors_count,
            "attempts": attempts_count,
        })

        total_topics_all += total_topics
        total_done_all += done

    # Общий прогресс
    total_percent = int(total_done_all / total_topics_all * 100) if total_topics_all else 0

    # Общие ошибки и попытки
    total_errors = db.query(Error).count()
    total_attempts = db.query(Attempt).count()

    # Слабые темы (топ-5)
    weak_rows = (
        db.query(Error.topic_id, func.count(Error.id))
        .filter(Error.topic_id.isnot(None))
        .group_by(Error.topic_id)
        .order_by(func.count(Error.id).desc())
        .limit(5)
        .all()
    )
    weak = []
    for tid, cnt in weak_rows:
        topic = db.get(Topic, tid)
        if not topic:
            continue
        tg = db.get(TaskGroup, topic.task_group_id)
        subject = db.get(Subject, tg.subject_id) if tg else None
        weak.append({
            "topic": topic.name,
            "subject": subject.name if subject else "—",
            "errors": cnt,
        })

    return {
        "by_subject": by_subject,
        "total_topics": total_topics_all,
        "total_done": total_done_all,
        "total_percent": total_percent,
        "total_errors": total_errors,
        "total_attempts": total_attempts,
        "weak_topics": weak,
    }