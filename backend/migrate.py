"""
Миграция БД: добавляет новые таблицы и колонки.
БЕЗОПАСНО: не удаляет данные, только дополняет.
Запуск: python migrate.py
"""
from sqlalchemy import inspect, text
from database import engine, init_db
import models  # важно: импорт подтягивает все модели


def column_exists(table_name: str, column_name: str) -> bool:
    """Проверяет, есть ли колонка в таблице."""
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return False
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def add_column_if_missing(table: str, column: str, column_type: str):
    """Добавляет колонку, если её нет."""
    if column_exists(table, column):
        print(f">> [{table}.{column}] уже существует")
        return
    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"))
        conn.commit()
    print(f">> [{table}.{column}] ДОБАВЛЕНА")


def migrate():
    print("=== МИГРАЦИЯ БД ===")
    print("")

    # 1. Создаём новые таблицы
    print(">> Создаю новые таблицы (если их нет)...")
    init_db()
    print(">> Таблицы готовы")
    print("")

    # 2. Добавляем новые колонки в существующие таблицы
    print(">> Добавляю новые колонки в topics...")
    add_column_if_missing("topics", "mastered_at", "DATETIME")
    add_column_if_missing("topics", "mastery_level", "REAL DEFAULT 0.0")
    add_column_if_missing("topics", "last_reviewed_at", "DATETIME")
    add_column_if_missing("topics", "next_review_at", "DATETIME")

    print("")
    print(">> Добавляю новые колонки в errors...")
    add_column_if_missing("errors", "error_type", "VARCHAR(50)")
    add_column_if_missing("errors", "severity", "INTEGER DEFAULT 1")
    add_column_if_missing("errors", "number_of_repeats", "INTEGER DEFAULT 1")
    add_column_if_missing("errors", "next_review_at", "DATETIME")

    print("")
    print("=== МИГРАЦИЯ ЗАВЕРШЕНА ===")


if __name__ == "__main__":
    migrate()