import sys
sys.path.insert(0, 'D:/Proyectos/METRICAS CRISS ia/cri_metrics')

from app.database import SessionLocal, engine, Base
from app.models import TelemetryRecord
from datetime import datetime, timezone

Base.metadata.create_all(bind=engine)
db = SessionLocal()

now = datetime.now(timezone.utc)
print(f"Now: {now}")

kpis = ["GSPI", "SHPD", "LTCR", "CFBR", "UOR"]
for kpi in kpis:
    latest = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.kpi_code == kpi)
        .order_by(TelemetryRecord.timestamp.desc())
        .first()
    )
    if latest:
        ts = latest.timestamp
        print(f"{kpi}: ts={ts}, type={type(ts)}")
        if ts:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            delta = (now - ts).total_seconds()
            print(f"  delta={delta:.1f}s")
    else:
        print(f"{kpi}: No data")

db.close()
print("Done")
