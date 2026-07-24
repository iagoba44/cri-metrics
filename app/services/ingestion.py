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

        total = 0
        for source in sources:
            try:
                data = source.fetch()
                count = self.ingest_batch(data)
                total += count
                logger.info(f"Fuente {source.__class__.__name__}: {count} registros")
            except Exception as e:
                logger.error(f"Fallo en fuente {source.__class__.__name__}: {e}")

        return total
