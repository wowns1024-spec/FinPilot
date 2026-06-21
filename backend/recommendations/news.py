"""추천 이유 생성에 사용할 종목별 뉴스 요약 수집.

F500 뉴스 기능이 완성되기 전까지는 키 없는 RSS 검색 결과의 최신 헤드라인을 짧게
압축해 ``StockNewsSummary`` 에 저장한다. 실패해도 추천 생성은 계속되어야 하므로
호출측으로 예외를 전파하지 않는다.
"""

import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from email.utils import parsedate_to_datetime

import requests
from django.conf import settings
from django.utils import timezone

from .models import StockNewsSummary

logger = logging.getLogger(__name__)


class NewsError(Exception):
    """뉴스 요약 수집 실패."""


def _limit():
    return max(int(getattr(settings, "NEWS_SUMMARY_LIMIT", 5)), 1)


def _timeout():
    return max(int(getattr(settings, "NEWS_SUMMARY_TIMEOUT_SECONDS", 5)), 1)


def _enabled():
    return bool(getattr(settings, "NEWS_SUMMARY_ENABLED", True))


def _strip_html(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _published_at(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.astimezone(timezone.UTC)


def _query(stock):
    return f"{stock.name} {stock.code} 주식"


def fetch_news_items(stock):
    """RSS 검색으로 최신 뉴스 후보를 가져온다."""
    try:
        resp = requests.get(
            getattr(settings, "NEWS_RSS_BASE", "https://news.google.com/rss/search"),
            params={
                "q": _query(stock),
                "hl": "ko",
                "gl": "KR",
                "ceid": "KR:ko",
            },
            timeout=_timeout(),
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise NewsError(f"news request failed: {exc}") from exc

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        raise NewsError(f"bad news rss: {exc}") from exc

    items = []
    for node in root.findall("./channel/item"):
        title = _strip_html(node.findtext("title"))
        if not title:
            continue
        description = _strip_html(node.findtext("description"))
        source = node.find("source")
        items.append(
            {
                "title": title,
                "url": (node.findtext("link") or "").strip(),
                "description": description,
                "source": _strip_html(source.text if source is not None else ""),
                "source_url": (source.get("url") if source is not None else "") or "",
                "published_at": _published_at(node.findtext("pubDate")),
            }
        )
        if len(items) >= _limit():
            break
    return items


def summarize_items(stock, items):
    """뉴스 후보를 GMS 프롬프트에 넣을 짧은 요약 텍스트로 압축한다."""
    if not items:
        return ""
    lines = []
    for item in items[: _limit()]:
        title = item["title"]
        description = item.get("description") or ""
        if description and description != title:
            line = f"- {title}: {description[:120]}"
        else:
            line = f"- {title}"
        lines.append(line.rstrip())
    return f"{stock.name} 관련 최근 뉴스 헤드라인 요약:\n" + "\n".join(lines)


def articles_for_storage(items):
    """DB/응답에 저장할 뉴스 기사 링크 스냅샷."""
    out = []
    for item in items[: _limit()]:
        url = item.get("url") or ""
        title = item.get("title") or ""
        if not title or not url:
            continue
        published_at = item.get("published_at")
        out.append(
            {
                "title": title,
                "url": url,
                "source": item.get("source") or "",
                "source_url": item.get("source_url") or "",
                "published_at": published_at.isoformat() if published_at else None,
            }
        )
    return out


def refresh_news_summary(stock):
    """한 종목의 뉴스 요약을 강제 갱신한다. 성공 여부를 bool로 반환."""
    if not _enabled():
        return False
    try:
        items = fetch_news_items(stock)
    except NewsError as exc:
        logger.warning("News summary refresh failed for stock %s: %s", stock.code, exc)
        return False

    summary = summarize_items(stock, items)
    if not summary:
        return False

    as_of = None
    published = [item["published_at"] for item in items if item.get("published_at")]
    if published:
        as_of = max(published)

    StockNewsSummary.objects.update_or_create(
        stock=stock,
        defaults={
            "summary": summary,
            "articles": articles_for_storage(items),
            "source": "rss",
            "as_of": as_of,
        },
    )
    return True


def _is_stale(summary):
    if summary is None or not summary.summary or not summary.articles:
        return True
    ttl = timedelta(hours=int(getattr(settings, "NEWS_SUMMARY_TTL_HOURS", 6)))
    return timezone.now() - summary.updated_at > ttl


def ensure_news_summaries(stocks):
    """필요한 종목만 뉴스 요약을 갱신한다. 반환값은 갱신 성공 건수."""
    stocks = list(stocks)
    if not stocks or not _enabled():
        return 0

    existing = {
        item.stock_id: item for item in StockNewsSummary.objects.filter(stock__in=stocks)
    }
    updated = 0
    for stock in stocks:
        if not _is_stale(existing.get(stock.id)):
            continue
        if refresh_news_summary(stock):
            updated += 1
    return updated
