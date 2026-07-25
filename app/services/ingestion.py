"""Pipeline de ingesta de datos desde fuentes externas."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import TelemetryRecord
from app.services.source_weights import compute_weighted_average, has_enough_confidence
import logging

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """Orquesta la ingesta de métricas desde múltiples fuentes."""

    def __init__(self, db: Session):
        self.db = db

    def ingest_batch(self, records: List[Dict]) -> int:
        """
        Ingesta un lote de registros crudos.
        records: list de dicts con {kpi_code, raw_value, timestamp, data_source}
        """
        inserted = 0
        for rec in records:
            try:
                telemetry = TelemetryRecord(
                    kpi_code=rec["kpi_code"],
                    timestamp=rec.get("timestamp", datetime.now(timezone.utc)),
                    raw_value=Decimal(str(rec["raw_value"])),
                    data_source=rec.get("data_source", "UNKNOWN"),
                )
                self.db.add(telemetry)
                inserted += 1
            except Exception as e:
                logger.error(f"Error ingestando registro {rec}: {e}")

        self.db.commit()
        logger.info(f"Ingestados {inserted} registros de telemetría")
        return inserted

    def run_scheduled_ingestion(self, use_real_sources: bool = True):
        """Ejecuta ingesta desde todas las fuentes configuradas.
        
        Args:
            use_real_sources: Si True, usa APIs reales (Vast.ai, CoinGecko, etc).
                              Si False, usa simuladores para testing.
        """
        if use_real_sources:
            from app.external.vast_ai_live import VastAIClient
            from app.external.coingecko import CoinGeckoClient
            from app.external.whattomine import WhatToMineScraper
            from app.external.yahoo_finance import YahooFinanceClient
            from app.external.binance import BinanceClient
            from app.external.lambdalabs import LambdaLabsScraper
            from app.external.fred_macro import FREDClient
            from app.external.nicehash import NiceHashClient
            from app.external.huggingface import HuggingFaceClient
            from app.external.defillama import DeFiLlamaClient
            sources = [
                VastAIClient(),
                CoinGeckoClient(),
                WhatToMineScraper(),
                YahooFinanceClient(),
                BinanceClient(),
                LambdaLabsScraper(),
                FREDClient(),
                NiceHashClient(),
                HuggingFaceClient(),
                DeFiLlamaClient(),
            ]
        else:
            from app.external.sec_edgar import SECDataSource
            from app.external.neoclouds import NeocloudDataSource
            from app.external.scrapers import B2BScraperDataSource
            sources = [
                SECDataSource(),
                NeocloudDataSource(),
                B2BScraperDataSource(),
            ]

        # Fase 1: Colectar todos los registros
        all_records = []
        source_stats = {}
        for source in sources:
            try:
                data = source.fetch()
                source_name = source.__class__.__name__
                source_stats[source_name] = len(data)
                for rec in data:
                    rec['_source_name'] = source_name
                all_records.extend(data)
                logger.info(f"Fuente {source_name}: {len(data)} registros")
            except Exception as e:
                logger.error(f"Fallo en fuente {source.__class__.__name__}: {e}")

        # Fase 2: Deduplicar con PONDERACIÓN de fuentes
        from collections import defaultdict
        kpi_groups = defaultdict(list)
        for r in all_records:
            kpi_groups[r["kpi_code"]].append(r)
        
        deduped_records = []
        for kpi, records in kpi_groups.items():
            if len(records) == 1:
                deduped_records.extend(records)
                continue
            
            # Promedio PONDERADO por confianza de fuente
            weighted_avg, used_sources, total_weight = compute_weighted_average(records)
            
            # Calcular std_dev para alertas
            values = [r["raw_value"] for r in records]
            simple_avg = sum(values) / len(values)
            std_dev = (sum((v - simple_avg) ** 2 for v in values) / len(values)) ** 0.5
            
            logger.info(f"[CROSS-VALIDATION] {kpi} de {len(records)} fuentes: "
                        f"valores={[round(v, 2) for v in values]}, "
                        f"ponderado={weighted_avg:.2f}, peso_total={total_weight}, "
                        f"std_dev={std_dev:.2f}, fuentes={used_sources}")
            
            # Si std_dev > 30, alertar fuerte discrepancia
            if std_dev > 30:
                logger.warning(f"[ALTA_VARIABILIDAD] {kpi}: std_dev={std_dev:.2f} entre fuentes. "
                               f"Fuentes: {[r['data_source'] for r in records]}")
            
            # Verificar confianza mínima
            if not has_enough_confidence(kpi, len(used_sources), total_weight):
                logger.warning(f"[CONFIANZA_BAJA] {kpi}: {len(used_sources)} fuentes, peso={total_weight}. "
                               f"Umbral no alcanzado. Resultado puede ser poco fiable.")
            
            deduped_records.append({
                "kpi_code": kpi,
                "raw_value": weighted_avg,
                "timestamp": datetime.now(timezone.utc),
                "data_source": f"WEIGHTED({','.join(used_sources)};w={total_weight})",
            })
        
        all_records = deduped_records

        # Fase 3: Validacion cruzada entre KPIs relacionados
        # GSPI y SHPD miden ambos precios GPU. Si divergen >50 puntos, alerta.
        gspi_rec = next((r for r in all_records if r.get("kpi_code") == "GSPI"), None)
        shpd_rec = next((r for r in all_records if r.get("kpi_code") == "SHPD"), None)
        if gspi_rec and shpd_rec:
            divergence = abs(gspi_rec["raw_value"] - shpd_rec["raw_value"])
            if divergence > 50:
                logger.warning(f"[DISCREPANCIA] GSPI={gspi_rec['raw_value']:.2f} vs SHPD={shpd_rec['raw_value']:.2f} "
                               f"(diferencia={divergence:.2f}). Mercado spot vs cloud diverge fuertemente.")

        # Fase 4: Ingestar
        # Limpiar campo interno _source_name
        for r in all_records:
            r.pop('_source_name', None)
        
        total = self.ingest_batch(all_records)
        logger.info(f"Total ingestado tras deduplicacion/validacion: {total} registros")
        return total
