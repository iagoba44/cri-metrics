"""RSS Feeder para CRI Metrics.
Ingesta noticias desde feeds directos sin rate limits.
Fuentes: Reuters Technology, Hacker News (hnrss.org), y opcionalmente Bloomberg.
"""
import logging
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Feeds configurables
DEFAULT_FEEDS = [
    {"name": "Reuters Technology", "url": "https://www.reutersagency.com/feed/?taxonomy=sectors&amp;post_type=reuters-best"},
    {"name": "Hacker News AI", "url": "https://hnrss.org/newest?q=artificial+intelligence+OR+GPU+OR+data+center"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
]

class RSSFeeder:
    """Cliente RSS para ingestar noticias técnicas y macro."""

    def __init__(self, feeds: Optional[List[Dict]] = None):
        self.feeds = feeds or DEFAULT_FEEDS

    def fetch_all(self, max_per_feed: int = 10) -> List[Dict]:
        """
        Recupera entradas de todos los feeds configurados.
        Retorna lista de dicts con title, summary, link, source, published.
        """
        all_entries = []
        for feed_cfg in self.feeds:
            try:
                entries = self._fetch_feed(feed_cfg, max_per_feed)
                all_entries.extend(entries)
                logger.info(f"[RSS] {feed_cfg['name']}: {len(entries)} entradas")
            except Exception as e:
                logger.warning(f"[RSS] Falló {feed_cfg['name']}: {e}")
        return all_entries

    def _fetch_feed(self, feed_cfg: Dict, limit: int) -> List[Dict]:
        url = feed_cfg["url"]
        # Usar feedparser para RSS
        parsed = feedparser.parse(url)
        entries = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        for entry in parsed.entries[:limit]:
            published = self._parse_date(entry)
            if published and published < cutoff:
                continue
            entries.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "link": entry.get("link", ""),
                "source": feed_cfg["name"],
                "published": published.isoformat() if published else None,
            })
        return entries

    def _parse_date(self, entry) -> Optional[datetime]:
        """Extrae fecha de publicación del entry RSS."""
        try:
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
        return None

    def fetch_hn_frontpage(self, limit: int = 30) -> List[Dict]:
        """
        Fallback: usa la API REST de Hacker News para top stories.
        Filtra por palabras clave IA/GPU/data center.
        """
        try:
            top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15).json()[:limit]
            results = []
            keywords = {"ai", "artificial intelligence", "gpu", "data center", "nvidia", "ml", "inference", "training"}
            for item_id in top_ids:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=10).json()
                if not item or not item.get("title"):
                    continue
                title_lower = item["title"].lower()
                if any(kw in title_lower for kw in keywords):
                    results.append({
                        "title": item["title"],
                        "summary": item.get("text", ""),
                        "link": f"https://news.ycombinator.com/item?id={item_id}",
                        "source": "HackerNews",
                        "published": datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc).isoformat(),
                    })
            return results
        except Exception as e:
            logger.error(f"[RSS] HN fallback falló: {e}")
            return []
