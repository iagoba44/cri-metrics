import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict

import numpy as np
from sqlalchemy.orm import Session

from app.models import TelemetryRecord, RiskIndex, TMISnapshot
from app.scenarios import get_zone

EVENTS = [
    {"day": -170, "name": "NVIDIA earnings beat", "cri_impact": -12, "kpi_impact": {"GSPI": -15, "UOR": -20}},
    {"day": -140, "name": "EU AI Act approved", "cri_impact": 8, "kpi_impact": {"LTCR": 25, "CFBR": 10}},
    {"day": -105, "name": "Crypto flash crash (ETH -30%)", "cri_impact": 18, "kpi_impact": {"CFBR": 40, "SHPD": 25}},
    {"day": -70, "name": "TSMC raises wafer prices", "cri_impact": 10, "kpi_impact": {"GSPI": 20, "SHPD": 15}},
    {"day": -35, "name": "Data center building boom", "cri_impact": -15, "kpi_impact": {"UOR": -30, "GSPI": -20}},
    {"day": -14, "name": "AI winter fears (analyst downgrade)", "cri_impact": 8, "kpi_impact": {"LTCR": 15, "CFBR": 12}},
]


def _active_event_name(day_idx: int, events: list) -> str:
    for evt in events:
        evt_idx = 180 + evt["day"]
        if evt_idx <= day_idx < evt_idx + 14:
            return evt["name"]
    return "SYNTHETIC_TREND"


class EnhancedBackfill:
    """Genera 6 meses de datos sinteticos realistas con tendencias y eventos de mercado."""

    def __init__(self, db: Session):
        self.db = db
        self.end_date = datetime.now(timezone.utc)
        self.start_date = self.end_date - timedelta(days=180)
        self.KPIS = ["GSPI", "SHPD", "LTCR", "CFBR", "UOR"]
        self.WEIGHTS = {"GSPI": 0.25, "SHPD": 0.15, "LTCR": 0.20, "CFBR": 0.20, "UOR": 0.20}

    def generate(self) -> Dict:
        days_ago = list(range(180, -1, -1))

        base_trend = []
        for d in days_ago:
            day_offset_from_start = 180 - d
            drift = 5 * np.sin(day_offset_from_start / 40)
            drift += day_offset_from_start * 0.02
            base = 48 + drift
            base_trend.append(base)

        for event in EVENTS:
            event_day_idx = 180 + event["day"]
            for i in range(max(0, event_day_idx), min(181, event_day_idx + 14)):
                decay = (14 - (i - event_day_idx)) / 14
                base_trend[i] += event["cri_impact"] * decay

        kpi_data = {kpi: [] for kpi in self.KPIS}
        for i, base in enumerate(base_trend):
            noise = np.random.normal(0, 3)
            kpi_data["GSPI"].append(max(5, min(95, base + noise * 1.2)))
            kpi_data["SHPD"].append(max(5, min(95, base + noise * 0.8)))
            kpi_data["LTCR"].append(max(5, min(95, base + noise * 1.5)))
            kpi_data["CFBR"].append(max(5, min(95, base + noise * 2.0)))
            kpi_data["UOR"].append(max(5, min(95, base + noise * 0.6 + 5)))

        for event in EVENTS:
            event_day_idx = 180 + event["day"]
            for i in range(max(0, event_day_idx), min(181, event_day_idx + 14)):
                decay = (14 - (i - event_day_idx)) / 14
                for kpi, impact in event["kpi_impact"].items():
                    kpi_data[kpi][i] += impact * decay
                    kpi_data[kpi][i] = max(5, min(95, kpi_data[kpi][i]))

        count_telemetry = 0
        count_cri = 0
        count_tmi = 0

        for i, (cri_base, d) in enumerate(zip(base_trend, days_ago)):
            ts = (self.end_date - timedelta(days=d)).replace(microsecond=0)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            source_name = f"ENHANCED_BACKFILL({_active_event_name(i, EVENTS)})"

            for kpi in self.KPIS:
                val = round(kpi_data[kpi][i], 2)
                record = TelemetryRecord(
                    record_id=uuid.uuid4(),
                    kpi_code=kpi,
                    timestamp=ts,
                    raw_value=Decimal(str(val)),
                    normalized_score=Decimal(str(val)),
                    data_source=source_name,
                    freshness_flag="BACKFILL",
                )
                self.db.add(record)
                count_telemetry += 1

            cri_score = round(sum(kpi_data[k][i] * self.WEIGHTS[k] for k in self.KPIS), 2)
            zone = get_zone(cri_score)

            risk = RiskIndex(
                index_id=uuid.uuid4(),
                timestamp=ts,
                cri_score=Decimal(str(cri_score)),
                risk_zone=zone,
                alerts_triggered="true" if cri_score > 65 else "false",
                component_scores=json.dumps({k: round(kpi_data[k][i], 2) for k in self.KPIS}),
            )
            self.db.add(risk)
            count_cri += 1

            tmi_score = round(cri_score + np.random.normal(0, 5), 2)
            tmi_score = max(0, min(100, tmi_score))
            tmi_zone = "COLD" if tmi_score <= 30 else "WARM" if tmi_score <= 70 else "HOT"

            tmi = TMISnapshot(
                snapshot_id=uuid.uuid4(),
                timestamp=ts,
                tmi_score=Decimal(str(tmi_score)),
                zone=tmi_zone,
                coverage_pct=Decimal("100"),
            )
            self.db.add(tmi)
            count_tmi += 1

            if i % 30 == 0:
                self.db.commit()

        self.db.commit()

        return {
            "telemetry_records": count_telemetry,
            "risk_indices": count_cri,
            "tmi_snapshots": count_tmi,
            "date_range": f"{base_trend[0]:.1f} -> {base_trend[-1]:.1f}",
            "cri_range": f"{min(base_trend):.1f} - {max(base_trend):.1f}",
            "events_applied": len(EVENTS),
        }
