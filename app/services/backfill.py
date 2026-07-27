"""Backfill Historico: Ingestion por lotes de 180 dias de telemetria.
Recupera datos historicos de todas las fuentes con API historica:
- Yahoo Finance (NVDA, AMD, SMCI, DELL, INTC) -> LTCR
- CoinGecko (BTC, ETH, AI tokens) -> CFBR, AI Tokens
- arXiv API -> arXiv velocity
- HN Algolia -> HN Activity
- WhatToMine -> SHPD (solo datos actuales, interpolado hacia atras)
"""
import logging
import time
import uuid
import yfinance as yf
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BACKFILL_DAYS = 180  # 6 meses
CHUNK_SIZE = 5  # Dormir cada N inserts para no sobrecargar APIs


class HistoricalBackfill:
    """Pipeline de ingesta historica batch."""

    def __init__(self, db: Session):
        self.db = db
        self.end_date = datetime.now(timezone.utc)
        self.start_date = self.end_date - timedelta(days=BACKFILL_DAYS)

    def run_full(self) -> Dict:
        """Ejecuta backfill completo de todas las fuentes. Retorna resumen."""
        results = {}

        # 1. Yahoo Finance (LTCR + SHPD proxy)
        try:
            results["yfinance"] = self._backfill_yahoo()
            logger.info(f"[Backfill] Yahoo Finance: {results['yfinance']} records")
        except Exception as e:
            logger.error(f"[Backfill] Yahoo Finance fallo: {e}")
            results["yfinance"] = {"error": str(e)}

        # 2. CoinGecko (CFBR + AI Tokens)
        try:
            results["coingecko"] = self._backfill_coingecko()
            logger.info(f"[Backfill] CoinGecko: {results['coingecko']} records")
        except Exception as e:
            logger.error(f"[Backfill] CoinGecko fallo: {e}")
            results["coingecko"] = {"error": str(e)}

        # 3. arXiv (velocity)
        try:
            results["arxiv"] = self._backfill_arxiv()
            logger.info(f"[Backfill] arXiv: {results['arxiv']} records")
        except Exception as e:
            logger.error(f"[Backfill] arXiv fallo: {e}")
            results["arxiv"] = {"error": str(e)}

        # 4. HN Algolia (activity)
        try:
            results["hn"] = self._backfill_hn()
            logger.info(f"[Backfill] HN: {results['hn']} records")
        except Exception as e:
            logger.error(f"[Backfill] HN fallo: {e}")
            results["hn"] = {"error": str(e)}

        # 5. Generar CRI historico (risk_indices)
        try:
            cri_count = self._generate_historical_cri()
            results["cri_indices"] = cri_count
            logger.info(f"[Backfill] CRI historico: {cri_count} indices generados")
        except Exception as e:
            logger.error(f"[Backfill] CRI historico fallo: {e}")
            results["cri_indices"] = {"error": str(e)}

        # Calcular total
        total = sum(
            r if isinstance(r, int) else 0 for r in results.values()
        )
        results["total"] = total
        logger.info(f"[Backfill] TOTAL: {total} registros ingestados para {BACKFILL_DAYS} dias")
        return results

    def _backfill_yahoo(self) -> int:
        """Yahoo Finance 180 dias de precios/volatilidad."""
        from app.models import TelemetryRecord

        tickers = ["NVDA", "AMD", "INTC"]
        count = 0

        for ticker in tickers:
            try:
                # Usar download que es mas fiable que Ticker
                data = yf.download(ticker, start=self.start_date.strftime("%Y-%m-%d"), 
                                   end=self.end_date.strftime("%Y-%m-%d"), progress=False)
                if data.empty:
                    logger.warning(f"[Backfill] Yahoo {ticker}: sin datos")
                    continue

                for idx, row in data.iterrows():
                    if count % CHUNK_SIZE == 0:
                        time.sleep(0.1)

                    ts = idx.to_pydatetime().replace(tzinfo=timezone.utc)
                    close = float(row["Close"])
                    vol = float(row["Close"].pct_change() or 0.0)

                    record = TelemetryRecord(
                        record_id=uuid.uuid4(),
                        kpi_code="LTCR",
                        timestamp=ts,
                        raw_value=Decimal(str(abs(vol) * 100)),
                        normalized_score=Decimal(str(min(100.0, abs(vol) * 1000))),
                        data_source=f"Yahoo({ticker})",
                        freshness_flag="BACKFILL",
                    )
                    self.db.add(record)
                    count += 1
                self.db.commit()
                logger.info(f"[Backfill] Yahoo {ticker}: {len(data)} rows")
            except Exception as e:
                logger.warning(f"[Backfill] Yahoo {ticker}: {e}")
                self.db.rollback()

        return count

    def _backfill_coingecko(self) -> int:
        """CoinGecko API historica para BTC y ETH como proxy CFBR."""
        from app.models import TelemetryRecord
        import requests

        count = 0
        coins = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "NEAR": "near",
            "RENDER": "render-token",
            "FET": "fetch-ai",
            "TAO": "bittensor",
        }

        for label, coingecko_id in coins.items():
            try:
                url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart/range"
                params = {
                    "vs_currency": "usd",
                    "from": int(self.start_date.timestamp()),
                    "to": int(self.end_date.timestamp()),
                }
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.warning(f"[Backfill] CoinGecko {label}: {resp.status_code}")
                    continue
                data = resp.json()
                prices = data.get("prices", [])
                if not prices:
                    continue

                for i, (ts_ms, price) in enumerate(prices):
                    if count % CHUNK_SIZE == 0:
                        time.sleep(0.15)

                    ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                    kpi = "CFBR" if label in ("BTC", "ETH") else "UOR"
                    raw = Decimal(str(price))

                    record = TelemetryRecord(
                        record_id=uuid.uuid4(),
                        kpi_code=kpi,
                        timestamp=ts,
                        raw_value=raw,
                        normalized_score=Decimal(str(min(100, max(0, price / 100000)))),
                        data_source=f"CoinGecko({label})",
                        freshness_flag="BACKFILL",
                    )
                    self.db.add(record)
                    count += 1
                self.db.commit()
            except Exception as e:
                logger.warning(f"[Backfill] CoinGecko {label}: {e}")
                self.db.rollback()

        return count

    def _backfill_arxiv(self) -> int:
        """arXiv API historica: conteo diario de papers ML."""
        from app.models import TelemetryRecord
        import requests

        count = 0
        queries = ["AI infrastructure", "GPU computing", "data center", "machine learning"]
        current = self.start_date

        while current < self.end_date:
            for query in queries:
                try:
                    url = "http://export.arxiv.org/api/query"
                    params = {
                        "search_query": f"all:{query}",
                        "start": 0,
                        "max_results": 5,
                        "sortBy": "submittedDate",
                        "sortOrder": "descending",
                    }
                    resp = requests.get(url, params=params, timeout=15)
                    if resp.status_code != 200:
                        continue

                    # Contar papers como proxy de velocidad
                    paper_count = resp.text.count("</entry>") if "<entry>" in resp.text else 0
                    score = min(100, paper_count * 20)

                    record = TelemetryRecord(
                        record_id=uuid.uuid4(),
                        kpi_code="SHPD",
                        timestamp=current,
                        raw_value=Decimal(str(paper_count)),
                        normalized_score=Decimal(str(score)),
                        data_source=f"arXiv({query})",
                        freshness_flag="BACKFILL",
                    )
                    self.db.add(record)
                    count += 1
                    time.sleep(0.1)
                except Exception as e:
                    logger.debug(f"[Backfill] arXiv {query}: {e}")

            self.db.commit()
            current += timedelta(days=7)  # Muestrear semanalmente
        return count

    def _backfill_hn(self) -> int:
        """HN Algolia: conteo de menciones IA/GPU/data center en el tiempo."""
        from app.models import TelemetryRecord
        import requests

        count = 0
        queries = ["GPU", "NVIDIA", "data center", "AI infrastructure"]
        current = self.start_date

        while current < self.end_date:
            for query in queries:
                try:
                    ts_start = int(current.timestamp())
                    next_week = current + timedelta(days=7)
                    ts_end = int(next_week.timestamp())
                    url = f"http://hn.algolia.com/api/v1/search_by_date"
                    params = {
                        "query": query,
                        "tags": "story",
                        "numericFilters": f"created_at_i>={ts_start},created_at_i<={ts_end}",
                        "hitsPerPage": 0,
                    }
                    resp = requests.get(url, params=params, timeout=10)
                    if resp.status_code != 200:
                        continue
                    nb_hits = resp.json().get("nbHits", 0)
                    score = min(100, nb_hits)

                    record = TelemetryRecord(
                        record_id=uuid.uuid4(),
                        kpi_code="SHPD",
                        timestamp=current,
                        raw_value=Decimal(str(nb_hits)),
                        normalized_score=Decimal(str(score)),
                        data_source=f"HN({query})",
                        freshness_flag="BACKFILL",
                    )
                    self.db.add(record)
                    count += 1
                    time.sleep(0.15)
                except Exception as e:
                    logger.debug(f"[Backfill] HN {query}: {e}")

            self.db.commit()
            current += timedelta(days=7)
        return count

    def _generate_historical_cri(self) -> int:
        """Genera risk_indices historicos (uno por dia) a partir de telemetry_records."""
        from app.models import TelemetryRecord, RiskIndex
        from app.scenarios import get_zone
        import json

        KPIS = ["GSPI", "SHPD", "LTCR", "CFBR", "UOR"]
        WEIGHTS = {"GSPI": 0.25, "SHPD": 0.15, "LTCR": 0.20, "CFBR": 0.20, "UOR": 0.20}
        DEFAULT = 50.0

        all_kpi_records = {}
        for kpi in KPIS:
            records = (
                self.db.query(TelemetryRecord)
                .filter(TelemetryRecord.kpi_code == kpi, TelemetryRecord.timestamp >= self.start_date.replace(tzinfo=None),
                        TelemetryRecord.timestamp <= (self.end_date + timedelta(days=1)).replace(tzinfo=None))
                .order_by(TelemetryRecord.timestamp.asc())
                .all()
            )
            all_kpi_records[kpi] = records

        count = 0
        current = self.start_date.replace(tzinfo=None)
        naive_end = self.end_date.replace(tzinfo=None)
        last_known = {kpi: None for kpi in KPIS}
        pointers = {kpi: 0 for kpi in KPIS}

        while current <= naive_end:
            day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            current += timedelta(days=1)

            kpi_values = {}
            for kpi in KPIS:
                records = all_kpi_records[kpi]
                p = pointers[kpi]
                while p < len(records) and records[p].timestamp < day_end:
                    p += 1
                if p > pointers[kpi]:
                    latest_in_window = records[p - 1]
                    ns = latest_in_window.normalized_score
                    if ns is not None:
                        val = float(ns)
                        last_known[kpi] = val
                    elif last_known[kpi] is not None:
                        val = last_known[kpi]
                    else:
                        val = DEFAULT
                    pointers[kpi] = p
                else:
                    if last_known[kpi] is not None:
                        val = last_known[kpi]
                    else:
                        val = DEFAULT
                kpi_values[kpi] = min(100.0, max(0.0, val))

            cri_score = sum(kpi_values[k] * WEIGHTS[k] for k in KPIS)
            cri_score = round(min(100.0, max(0.0, cri_score)), 2)
            zone = get_zone(cri_score)

            record = RiskIndex(
                index_id=uuid.uuid4(),
                timestamp=day_start,
                cri_score=Decimal(str(cri_score)),
                risk_zone=zone,
                alerts_triggered="false",
                component_scores=json.dumps(kpi_values),
            )
            self.db.add(record)
            count += 1

            if count % 30 == 0:
                self.db.commit()

        self.db.commit()
        return count
