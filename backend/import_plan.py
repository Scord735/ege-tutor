from pathlib import Path

src = Path("/mnt/data/import_plan.py")
out = Path("/mnt/data/import_plan_fixed.py")

fixed = '''"""
Импорт плана ЕГЭ в БД.

Что делает:
- создаёт 32 фазы;
- создаёт все дни с 06.10.2026 по 31.05.2027;
- распределяет темы внутри каждой фазы по дням, а не берёт первые темы каждый день;
- не дублирует одну и ту же тему внутри одного дня;
- обычно даёт 1–2 разные темы на предмет;
- воскресенье оставляет LIGHT и добавляет темы для повторения;
- если у дня/предмета нет маппинга, использует fallback-темы из доступных тем фазы;
- проверяет, что все topic_id существуют в БД.

Запуск:
    python import_plan.py
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from database import SessionLocal, init_db
from models import PlanPhase, DayPlan, DayPlanItem, Topic


DAY_PATTERN = {
    0: ["math", "phys", "rus"],     # Пн
    1: ["math", "chem"],            # Вт
    2: ["phys", "math", "rus"],     # Ср
    3: ["math", "chem"],            # Чт
    4: ["phys", "math", "rus"],     # Пт
    5: ["rus", "math", "chem"],     # Сб
    6: [],                           # Вс — LIGHT / повторение
}

MINUTES_PER_SUBJECT = {
    "math": 20,
    "phys": 15,
    "rus": 15,
    "chem": 15,
}

SUBJECT_ORDER = ["math", "phys", "rus", "chem"]


def load_json(name):
    with open(name, "r", encoding="utf-8") as f:
        return json.load(f)


def choose_mapping_file():
    """
    Если рядом есть исправленный mapping — используем его.
    Иначе используем обычный plan_mapping.json.
    """
    corrected = Path("plan_mapping_corrected.json")
    normal = Path("plan_mapping.json")

    if corrected.exists():
        print(">> Используется: plan_mapping_corrected.json")
        return corrected

    if normal.exists():
        print(">> Используется: plan_mapping.json")
        return normal

    raise FileNotFoundError(
        "Не найден ни plan_mapping_corrected.json, ни plan_mapping.json"
    )


def get_topic_ids_for_subject_phase(mapping, subject_code, phase_topics):
    """Собирает уникальные валидные topic_id для предмета в фазе."""
    ids = []
    seen = set()

    subject_map = mapping.get(subject_code, {})

    for pdf_topic in phase_topics:
        for tid in subject_map.get(pdf_topic, []):
            if tid not in seen:
                seen.add(tid)
                ids.append(tid)

    return ids


def split_topics_for_day(topic_ids, day_index, count):
    """
    Распределяет темы по дням фазы.

    day_index = номер дня внутри фазы.
    count = сколько тем дать в этот день.

    Темы идут по кругу, поэтому:
    - первые темы не забиваются в каждый день;
    - внутри одного дня одинаковый topic_id не появляется дважды;
    - при коротком списке тем допускается повторение между разными днями.
    """
    if not topic_ids:
        return []

    if count <= 0:
        return []

    n = len(topic_ids)
    start = (day_index * count) % n

    result = []
    used = set()

    for offset in range(n):
        tid = topic_ids[(start + offset) % n]

        if tid in used:
            continue

        result.append(tid)
        used.add(tid)

        if len(result) >= count:
            break

    return result


def get_fallback_topics(all_subject_topics, day_index, count=2):
    """
    Fallback для дня, где нет обычных предметов/маппинга.
    Берём темы из разных предметов, если возможно.
    """
    result = []
    seen = set()

    subjects = [
        all_subject_topics.get(code, [])
        for code in SUBJECT_ORDER
    ]

    # Сначала стараемся взять по одной теме из разных предметов.
    for offset in range(len(SUBJECT_ORDER)):
        subject_topics = subjects[offset]

        if not subject_topics:
            continue

        tid = subject_topics[day_index % len(subject_topics)]

        if tid not in seen:
            result.append((SUBJECT_ORDER[offset], tid))
            seen.add(tid)

        if len(result) >= count:
            return result

    # Если разных предметов мало — добираем из всех доступных.
    flat = []
    for code in SUBJECT_ORDER:
        for tid in all_subject_topics.get(code, []):
            flat.append((code, tid))

    if flat:
        start = day_index % len(flat)

        for offset in range(len(flat)):
            code, tid = flat[(start + offset) % len(flat)]

            if tid in seen:
                continue

            result.append((code, tid))
            seen.add(tid)

            if len(result) >= count:
                break

    return result


def add_day_item(db, day, subject_code, tid, minutes, item_type="new", priority=3):
    item = DayPlanItem(
        day_plan_id=day.id,
        topic_id=tid,
        type=item_type,
        priority=priority,
        minutes_planned=minutes,
        source="calendar",
    )
    db.add(item)
    return item


def import_plan():
    print("=== ИМПОРТ ПЛАНА В БД ===")
    print("")

    init_db()
    db = SessionLocal()

    try:
        existing_phases = db.query(PlanPhase).count()

        if existing_phases > 0:
            print(f">> Найдено {existing_phases} фаз в БД.")
            answer = input(">> Удалить и перезалить? (y/N): ").strip().lower()

            if answer == "y":
                db.query(DayPlanItem).delete()
                db.query(DayPlan).delete()
                db.query(PlanPhase).delete()
                db.commit()
                print(">> Старые данные удалены.")
            else:
                print(">> Отмена.")
                return

        plan = load_json("plan_full.json")
        mapping_file = choose_mapping_file()
        mapping = load_json(mapping_file)

        phases = plan["phases"]

        print(f">> Загружено {len(phases)} фаз из plan_full.json")
        print(f">> Загружено маппингов по {len(mapping)} предметам")
        print("")

        valid_topic_ids = {t.id for t in db.query(Topic).all()}

        print(f">> Валидных topic_id в БД: {len(valid_topic_ids)}")
        print("")

        total_days = 0
        total_items = 0
        empty_days = []
        duplicate_days = []

        for phase_data in phases:
            start_date = datetime.strptime(
                phase_data["start_date"], "%Y-%m-%d"
            )
            end_date = datetime.strptime(
                phase_data["end_date"], "%Y-%m-%d"
            )

            phase = PlanPhase(
                name=phase_data["name"],
                start_date=start_date,
                end_date=end_date,
                description=phase_data.get("description", ""),
                order_index=phase_data["order"],
            )

            db.add(phase)
            db.flush()

            print(
                f">> [{phase_data['order']:2d}] "
                f"{phase_data['name']} "
                f"({phase_data['start_date']} → {phase_data['end_date']})"
            )

            # Собираем темы всей фазы заранее.
            phase_topic_ids = {}

            for subject_code in SUBJECT_ORDER:
                phase_subjects = phase_data.get("subjects", {}).get(
                    subject_code, []
                )

                ids = get_topic_ids_for_subject_phase(
                    mapping,
                    subject_code,
                    phase_subjects,
                )

                ids = [tid for tid in ids if tid in valid_topic_ids]
                phase_topic_ids[subject_code] = ids

            current = start_date
            day_index = 0

            while current <= end_date:
                is_sunday = current.weekday() == 6

                day = DayPlan(
                    date=current,
                    phase_id=phase.id,
                    mode="LIGHT" if is_sunday else "NORMAL",
                    minutes_planned=0,
                )

                db.add(day)
                db.flush()

                minutes_day = 0
                day_topic_ids = set()

                subjects_for_day = DAY_PATTERN.get(
                    current.weekday(), []
                )

                # Обычные дни: 1–2 разные темы на предмет.
                for subject_code in subjects_for_day:
                    topic_ids = phase_topic_ids.get(subject_code, [])

                    if not topic_ids:
                        continue

                    # При большом пуле тем даём 2, при маленьком — 1.
                    count = 2 if len(topic_ids) >= 2 else 1

                    selected = split_topics_for_day(
                        topic_ids,
                        day_index,
                        count,
                    )

                    if not selected:
                        continue

                    subject_minutes = MINUTES_PER_SUBJECT.get(
                        subject_code,
                        15,
                    )

                    # Сохраняем исходный дневной лимит времени на предмет,
                    # деля его между выбранными темами.
                    minutes_each = max(
                        1,
                        subject_minutes // len(selected),
                    )

                    for tid in selected:
                        if tid in day_topic_ids:
                            continue

                        add_day_item(
                            db=db,
                            day=day,
                            subject_code=subject_code,
                            tid=tid,
                            minutes=minutes_each,
                            item_type="new",
                            priority=3,
                        )

                        day_topic_ids.add(tid)
                        total_items += 1
                        minutes_day += minutes_each

                # Воскресенье: LIGHT / повторение.
                # Даже в воскресенье день не остаётся пустым.
                if is_sunday:
                    fallback = get_fallback_topics(
                        phase_topic_ids,
                        day_index,
                        count=3,
                    )

                    for subject_code, tid in fallback:
                        if tid in day_topic_ids:
                            continue

                        add_day_item(
                            db=db,
                            day=day,
                            subject_code=subject_code,
                            tid=tid,
                            minutes=10,
                            item_type="review",
                            priority=2,
                        )

                        day_topic_ids.add(tid)
                        total_items += 1
                        minutes_day += 10

                # Если обычный день оказался пустым —
                # обязательный fallback 2–3 темы.
                if not day_topic_ids:
                    fallback = get_fallback_topics(
                        phase_topic_ids,
                        day_index,
                        count=3,
                    )

                    for subject_code, tid in fallback:
                        if tid in day_topic_ids:
                            continue

                        add_day_item(
                            db=db,
                            day=day,
                            subject_code=subject_code,
                            tid=tid,
                            minutes=10,
                            item_type="new",
                            priority=2,
                        )

                        day_topic_ids.add(tid)
                        total_items += 1
                        minutes_day += 10

                if not day_topic_ids:
                    empty_days.append(
                        current.strftime("%Y-%m-%d")
                    )

                # Финальная защита от дублей внутри одного дня.
                if len(day_topic_ids) != len(
                    set(day_topic_ids)
                ):
                    duplicate_days.append(
                        current.strftime("%Y-%m-%d")
                    )

                day.minutes_planned = minutes_day

                total_days += 1
                current += timedelta(days=1)
                day_index += 1

        db.commit()

        print("")
        print(">> Проверка результата:")
        print(f"   • Фаз: {len(phases)}")
        print(f"   • Дней: {total_days}")
        print(f"   • Пунктов плана: {total_items}")
        print(f"   • Пустых дней: {len(empty_days)}")
        print(f"   • Дней с дублями: {len(duplicate_days)}")

        if empty_days:
            print("   [!] Пустые дни:")
            for date in empty_days[:20]:
                print(f"       - {date}")

        if duplicate_days:
            print("   [!] Дубли:")
            for date in duplicate_days[:20]:
                print(f"       - {date}")

        if total_days != 238:
            print(
                f"   [!] Ожидалось 238 дней, получено {total_days}"
            )
        else:
            print("   [OK] Все 238 дней созданы.")

        if not empty_days and not duplicate_days and total_days == 238:
            print("   [OK] Все дни заполнены без дублей.")

        print("")
        print("=== ИМПОРТ ЗАВЕРШЁН ===")

    except Exception as e:
        db.rollback()
        print(f">> [!] ОШИБКА: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import_plan()
'''

out.write_text(fixed, encoding="utf-8")
print(out)
print("lines:", len(fixed.splitlines()))