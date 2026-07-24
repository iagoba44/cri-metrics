"""Script de demostracion con DATOS REALES del mercado.
Integra Vast.ai, CoinGecko, WhatToMine, Yahoo Finance.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, Base, engine
from app.services.ingestion import IngestionPipeline
from app.services.calculator import CRICalculator

def demo_real_data():
    print("=" * 70)
    print("DEMO CRI - DATOS REALES DEL MERCADO")
    print("=" * 70)
    print("\nFuentes:")
    print("  [GSPI] Vast.ai      - Precios spot GPU en vivo")
    print("  [UOR]  Vast.ai      - Ratio de ocupacion GPU")
    print("  [CFBR] CoinGecko    - Volatilidad mercado crypto")
    print("  [SHPD] WhatToMine   - Rentabilidad minera GPU")
    print("  [LTCR] Yahoo Finance- Volatilidad acciones IA")
    print("=" * 70)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("\n[1] INGESTA REAL desde fuentes externas...")
    pipeline = IngestionPipeline(db)
    total = pipeline.run_scheduled_ingestion(use_real_sources=True)
    print(f"    >> {total} registros ingestados desde datos reales")

    print("\n[2] CALCULO CRI con datos reales...")
    calculator = CRICalculator(db)
    risk_index, meta = calculator.calculate()

    print(f"\n{'='*70}")
    print(f"    CRI SCORE:    {risk_index.cri_score}")
    print(f"    RISK ZONE:    {risk_index.risk_zone}")
    print(f"    ALERTS:       {risk_index.alerts_triggered}")
    print(f"{'='*70}")

    print("\n[3] DESGLOSE POR KPI (datos reales):")
    print(f"    {'KPI':6s} | {'Raw':>8s} | {'Score':>6s} | {'Weight':>6s} | {'Contrib':>8s} | {'Source':20s}")
    print("    " + "-" * 65)
    for kpi, details in meta["component_details"].items():
        contrib = details["normalized_score"] * details["weight"]
        print(f"    {kpi:6s} | {details['raw_value']:8.2f} | {details['normalized_score']:6.2f} | "
              f"{details['weight']:6.2f} | {contrib:8.2f} | {details['freshness']:6s}")

    missing = meta.get("missing_kpis", [])
    if missing:
        print(f"\n[!] KPIs faltantes: {missing}")

    print("\n" + "=" * 70)
    print("INTERPRETACION DEL MERCADO IA (Julio 2026):")
    print("=" * 70)

    # Analisis automatico basado en valores reales
    gspi_raw = meta["component_details"].get("GSPI", {}).get("raw_value", 0)
    uor_raw = meta["component_details"].get("UOR", {}).get("raw_value", 0)
    shpd_raw = meta["component_details"].get("SHPD", {}).get("raw_value", 0)

    cri_val = float(risk_index.cri_score)
    if cri_val > 65:
        print("    [!] ALERTA CRITICA: El mercado de infraestructura IA presenta")
        print("        signos severos de sobreoferta y compresion de margenes.")
    elif cri_val > 30:
        print("    [!] RIESGO MODERADO: Presion en precios detectada.")
    else:
        print("    [OK] Mercado estable.")

    if gspi_raw > 50:
        print(f"    - GSPI {gspi_raw:.0f}%: Deflacion extrema en precios GPU spot.")
    if uor_raw > 80:
        print(f"    - UOR {uor_raw:.0f}%: Masiva infrautilizacion de capacidad GPU.")
    if shpd_raw > 70:
        print(f"    - SHPD {shpd_raw:.0f}%: Colapso en demanda de hardware minero/servidor.")

    print("=" * 70)

if __name__ == "__main__":
    demo_real_data()
