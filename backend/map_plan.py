"""
ИИ-сопоставление тем PDF с нашими Topic.id из БД.
Запуск: python map_plan.py
Результат: plan_mapping.json

Версия 3 (исправлены отступы):
- задержка 25 сек между предметами
- пропуск уже обработанных
- сохранение прогресса
- жёсткий JSON-формат
"""
import asyncio
import json
from pathlib import Path

from database import SessionLocal
from models import Subject, TaskGroup, Topic
import ai_service


SUBJECT_MAP = {
    "math": "Математика (профиль)",
    "phys": "Физика",
    "rus": "Русский язык",
    "chem": "Химия",
}

PDF_TO_SUBJECT = {
    "math": "math",
    "phys": "phys",
    "rus": "rus",
    "chem": "chem",
}

DELAY_BETWEEN_SUBJECTS = 25
MAPPING_FILE = "plan_mapping.json"


def load_plan():
    with open("plan_full.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_topics_from_db():
    db = SessionLocal()
    result = {}
    try:
        for code in SUBJECT_MAP:
            subject = db.query(Subject).filter_by(code=code).first()
            if not subject:
                print(f">> [!] Предмет {code} не найден в БД")
                result[code] = []
                continue

            topics = []
            for tg in subject.task_groups:
                for t in tg.topics:
                    topics.append({
                        "id": t.id,
                        "name": t.name,
                        "task_group": tg.name,
                    })
            result[code] = topics
            print(f">> [{code}] загружено {len(topics)} тем из БД")
    finally:
        db.close()
    return result


def collect_pdf_topics(plan, subject_code):
    topics = set()
    for phase in plan["phases"]:
        subject_key = PDF_TO_SUBJECT.get(subject_code, subject_code)
        for t in phase["subjects"].get(subject_key, []):
            topics.add(t)
    return sorted(topics)


def extract_json_from_answer(answer: str) -> str:
    """Достаёт JSON из ответа ИИ, даже если модель болтала."""
    s = answer.strip()

    if "```json" in s:
        s = s.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in s:
        s = s.split("```", 1)[1].split("```", 1)[0].strip()

    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start:end+1]

    return s


async def map_subject(subject_code, pdf_topics, db_topics):
    """Один запрос к ИИ на предмет. Возвращает {pdf_topic: [ids]}."""

    db_lines = []
    for t in db_topics:
        db_lines.append(f"[{t['id']}] {t['name']}  (раздел: {t['task_group']})")
    db_text = "\n".join(db_lines)

    pdf_text = "\n".join(f"- {t}" for t in pdf_topics)

    subject_name = SUBJECT_MAP[subject_code]

    system = (
        "Ты — эксперт по ЕГЭ. Сопоставляешь темы учебного плана с темами из базы данных. "
        "СТРОГИЕ ПРАВИЛА:\n"
        "1. Отвечай ТОЛЬКО валидным JSON. Никаких пояснений, reasoning, markdown.\n"
        "2. Используй ТОЛЬКО те ID, что даны в списке БД. Не придумывай.\n"
        "3. Одна PDF-тема может соответствовать НЕСКОЛЬКИМ ID из БД.\n"
        "4. Если сомневаешься — добавляй ID (лучше больше, чем меньше).\n"
        "5. Если PDF-тема вообще не находит соответствия — верни [].\n"
        "Формат ответа: {\"pdf_тема\": [id1, id2, ...]}"
    )

    user = f"""Предмет: {subject_name}

PDF-темы (из учебного плана) — {len(pdf_topics)} штук:
{pdf_text}

Темы в БД — {len(db_topics)} штук, каждая с ID:
{db_text}

Задача: для КАЖДОЙ PDF-темы найди ВСЕ подходящие ID из БД.
Например: PDF-тема "Н и НН" должна получить несколько ID — все темы про Н/НН.
Верни JSON: {{"pdf_тема": [id1, id2, ...]}}
Только JSON, без markdown и пояснений."""

    print(f">> Отправляю запрос к ИИ ({len(pdf_topics)} PDF-тем × {len(db_topics)} тем БД)...")

    answer = await ai_service.ask_ai(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=4000,
    )

    clean = extract_json_from_answer(answer)

    try:
        data = json.loads(clean)
        return data
    except json.JSONDecodeError:
        print(f">> [!] Ошибка JSON. Первые 800 символов ответа:")
        print(answer[:800])
        raise


def load_existing_mapping():
    p = Path(MAPPING_FILE)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_mapping(data):
    Path(MAPPING_FILE).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def main():
    print("=== ИИ-СОПОСТАВЛЕНИЕ ТЕМ ===")
    print("")

    plan = load_plan()
    print(f">> Загружено {len(plan['phases'])} фаз из plan_full.json")
    print("")

    db_topics = load_topics_from_db()
    print("")

    existing = load_existing_mapping()
    if existing:
        print(f">> Найден существующий mapping: {list(existing.keys())}")
        print("")

    result = dict(existing)

    for code in ["math", "phys", "rus", "chem"]:
        if code in result and result[code]:
            print(f">> [{code}] уже сопоставлен — пропускаю")
            continue

        pdf_topics = collect_pdf_topics(plan, code)
        if not pdf_topics:
            print(f">> [{code}] нет PDF-тем — пропускаю")
            continue

        db_for_subject = db_topics.get(code, [])
        if not db_for_subject:
            print(f">> [{code}] нет тем в БД — пропускаю")
            continue

        if result:
            print(f">> Пауза {DELAY_BETWEEN_SUBJECTS} сек перед {code}...")
            await asyncio.sleep(DELAY_BETWEEN_SUBJECTS)

        print(f"--- {SUBJECT_MAP[code]} ---")
        try:
            mapping = await map_subject(code, pdf_topics, db_for_subject)
            result[code] = mapping
            save_mapping(result)
            print(f">> [{code}] сопоставлено {len(mapping)} из {len(pdf_topics)} PDF-тем")
            for pdf_t, ids in mapping.items():
                print(f"   • {pdf_t} → {ids}")
        except Exception as e:
            print(f">> [!] Не удалось сопоставить {code}: {e}")
        print("")

    print(f">> Результат сохранён в {MAPPING_FILE}")
    print("=== ГОТОВО ===")


if __name__ == "__main__":
    asyncio.run(main())