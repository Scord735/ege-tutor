from database import SessionLocal
from models import PlanPhase, DayPlan, DayPlanItem

db = SessionLocal()
print("Фаз:", db.query(PlanPhase).count())
print("Дней:", db.query(DayPlan).count())
print("Пунктов:", db.query(DayPlanItem).count())

# Первая фаза
p = db.query(PlanPhase).order_by(PlanPhase.order_index).first()
print(f"\nПервая фаза: {p.name}")
print(f"  {p.start_date.date()} → {p.end_date.date()}")

# Первый день
d = db.query(DayPlan).order_by(DayPlan.date).first()
print(f"\nПервый день: {d.date.date()}, режим {d.mode}")
print(f"  Минут: {d.minutes_planned}")
print(f"  Пунктов: {len(d.items)}")

db.close()