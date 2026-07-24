"""Pipeline de ingesta de datos desde fuentes externas."""
from datetime import datetime
from decimal import Decimal
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import TelemetryRecord
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
                    timestamp=rec.get("timestamp", datetime.utcnow()),
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
            sources = [
                VastAIClient(),
                CoinGeckoClient(),
                WhatToMineScraper(),
                YahooFinanceClient(),
                BinanceClient(),
                LambdaLabsScraper(),
                FREDClient(),
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

        # Fase 2: Deduplicar y validar KPIs con multiples fuentes
        # SHPD: puede venir de WhatToMine y LambdaLabs. Promediamos.
        shpd_values = [r for r in all_records if r.get("kpi_code") == "SHPD"]
        if len(shpd_values) > 1:
            avg_shpd = sum(r["raw_value"] for r in shpd_values) / len(shpd_values)
            logger.info(f"[CROSS-VALIDATION] SHPD de {len(shpd_values)} fuentes: "
                        f"valores={[r['raw_value'] for r in shpd_values]}, promedio={avg_shpd:.2f}")
            # Reemplazar todos los SHPD con el promedio, marcando fuente combinada
            all_records = [r for r in all_records if r.get("kpi_code") != "SHPD"]
            all_records.append({
                "kpi_code": "SHPD",
                "raw_value": avg_shpd,
                "timestamp": datetime.utcnow(),
                "data_source": f"COMBINED({','.join(r['data_source'] for r in shpd_values)})",
            })
        
        # CFBR: puede venir de CoinGecko y Binance. Promediamos.
        cfbr_values = [r for r in all_records if r.get("kpi_code") == "CFBR"]
        if len(cfbr_values) > 1:
            avg_cfbr = sum(r["raw_value"] for r in cfbr_values) / len(cfbr_values)
            logger.info(f"[CROSS-VALIDATION] CFBR de {len(cfbr_values)} fuentes: "
                        f"valores={[r['raw_value'] for r in cfbr_values]}, promedio={avg_cfbr:.2f}")
            all_records = [r for r in all_records if r.get("kpi_code") != "CFBR"]
            all_records.append({
                "kpi_code": "CFBR",
                "raw_value": avg_cfbr,
                "timestamp": datetime.utcnow(),
                "data_source": f"COMBINED({','.join(r['data_source'] for r in cfbr_values)})",
            })

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
