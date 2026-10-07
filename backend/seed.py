"""
Общий запуск заливки всех 4 предметов.
Запуск: python seed.py
Каждый предмет можно залить отдельно: python seed_math.py и т.д.
"""
import seed_math
import seed_rus
import seed_chem
import seed_phys


def main():
    print("=== ЗАЛИВКА ВСЕХ 4 ПРЕДМЕТОВ ===\n")
    seed_math.seed()
    seed_rus.seed()
    seed_chem.seed()
    seed_phys.seed()
    print("\n>> Готово.")


if __name__ == "__main__":
    main()