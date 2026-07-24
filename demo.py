"""Script de demostración: seed de datos + cálculo CRI."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, Base, engine
from app.services.ingestion import IngestionPipeline
from app.services.calculator import CRICalculator

def seed_and_calculate():
    print("=" * 60)
    print("DEMO: Sistema CRI - Seed de datos y cálculo")
    print("=" * 60)

    # Crear tablas
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Seed de datos de ejemplo (simulando condiciones de mercado)
    print("\n[1] Ingestando telemetría de prueba...")
    records = [
        {"kpi_code": "GSPI", "raw_value": 35.0, "data_source": "SEC_EDGAR"},
        {"kpi_code": "SHPD", "raw_value": 18.5, "data_source": "B2B_SCRAPER"},
        {"kpi_code": "LTCR", "raw_value": 72.0, "data_source": "SEC_EDGAR"},
        {"kpi_code": "CFBR", "raw_value": 82.5, "data_source": "VAST_AI"},
        {"kpi_code": "UOR",  "raw_value": 45.0, "data_source": "RUNPOD"},
    ]

    pipeline = IngestionPipeline(db)
    inserted = pipeline.ingest_batch(records)
    print(f"    >> {inserted} registros ingestados")

    # Calcular CRI
    print("\n[2] Calculando Indice CRI...")
    calculator = CRICalculator(db)
    risk_index, meta = calculator.calculate()

    print(f"    >> CRI Score: {risk_index.cri_score}")
    print(f"    >> Risk Zone: {risk_index.risk_zone}")
    print(f"    >> Alerts:    {risk_index.alerts_triggered}")

    print("\n[3] Desglose por KPI:")
    for kpi, details in meta["component_details"].items():
        contrib = details["normalized_score"] * details["weight"]
        print(f"    {kpi:6s}: raw={details['raw_value']:6.2f} | score={details['normalized_score']:6.2f} | weight={details['weight']:.2f} | contrib={contrib:.2f}")

    print("\n" + "=" * 60)
    print("Demo completada. Usa la API para mas operaciones:")
    print("  uvicorn app.main:app --reload")
    print("=" * 60)

if __name__ == "__main__":
    seed_and_calculate()
