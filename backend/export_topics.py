"""
Экспорт всех тем из БД в JSON.
Запуск: python export_topics.py
Результат: topics_export.json
"""
import json
from database import SessionLocal
from models import Subject


def export():
    db = SessionLocal()
    result = {}
    try:
        for subject in db.query(Subject).all():
            topics = []
            for tg in subject.task_groups:
                for t in tg.topics:
                    topics.append({
                        "id": t.id,
                        "name": t.name,
                        "task_group": tg.name,
                        "task_number": tg.task_number,
                    })
            result[subject.code] = {
                "name": subject.name,
                "count": len(topics),
                "topics": topics,
            }
            print(f">> [{subject.code}] {subject.name}: {len(topics)} тем")
    finally:
        db.close()

    with open("topics_export.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(">> Результат: topics_export.json")


if __name__ == "__main__":
    export()