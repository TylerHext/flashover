"""Debug script to check activities and polylines."""

import sys
sys.path.insert(0, '/Users/tylerhext/repositories/flashover/backend')

from app.database import SessionLocal
from app.models import Activity

db = SessionLocal()

# Check total activities
total = db.query(Activity).count()
print(f"Total activities: {total}")

# Check activities with polylines
with_polyline = db.query(Activity).filter(Activity.polyline.isnot(None)).count()
print(f"Activities with polylines: {with_polyline}")

# Check activities with empty/null polylines
without_polyline = db.query(Activity).filter(Activity.polyline.is_(None)).count()
print(f"Activities without polylines: {without_polyline}")

# Sample a few activities
print("\n--- Sample Activities ---")
activities = db.query(Activity).limit(5).all()
for act in activities:
    has_polyline = "YES" if act.polyline else "NO"
    polyline_len = len(act.polyline) if act.polyline else 0
    print(f"ID: {act.id}, Type: {act.type}, Polyline: {has_polyline} (len={polyline_len})")
    if act.polyline:
        print(f"  First 100 chars: {act.polyline[:100]}")

db.close()
