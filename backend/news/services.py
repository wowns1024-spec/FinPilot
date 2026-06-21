"""F500 뉴스 오케스트레이션: RSS 수집(스로틀)→업서트→폴백 조회, 스크랩 처리."""

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

from . import feeds
from .models import NewsArticle, NewsScrap

logger = logging.getLogger(__name__)


def _enabled():
    return bool(getattr(settings, "NEWS_ENABLED", True))


def _limit(limit=None):
    if limit:
        return max(min(int(limit), 50), 1)
    return max(int(getattr(settings, "NEWS_LIST_LIMIT", 20)), 1)


def _ttl():
    return max(int(getattr(settings, "NEWS_LIST_TTL_SECONDS", 600)), 0)


def _top_query():
    return getattr(settings, "NEWS_TOP_QUERY", "증시 OR 코스피 OR 코스닥 OR 주식시장")


def build_query(query=None, stock=None, sector=None):
    """채널별 RSS 검색어. 종목>산업>키워드>주요 순으로 우선 적용."""
    if stock is not None:
        return f"{stock.name} {stock.code} 주가"
    if sector is not None:
        return f"{sector.name} 관련주 증시"
    query = (query or "").strip()
    if query:
        return query
    return _top_query()


def _cache_key(rss_query):
    digest = hashlib.md5(rss_query.encode("utf-8")).hexdigest()
    return f"news:rss:{digest}"


def _store(items, stock=None, sector=None):
    """RSS 후보를 URL 기준으로 업서트하고, 피드 순서대로 NewsArticle 리스트 반환."""
    stored = []
    for item in items:
        defaults = {
            "title": item["title"][:500],
            "summary": item.get("summary", ""),
            "source": (item.get("source") or "")[:200],
            "source_url": item.get("source_url") or "",
            "published_at": item.get("published_at"),
        }
        if stock is not None:
            defaults["stock"] = stock
        if sector is not None:
            defaults["sector"] = sector
        article, _ = NewsArticle.objects.update_or_create(
            url=item["url"], defaults=defaults
        )
        stored.append(article)
    return stored


def _stored_fallback(query=None, stock=None, sector=None, limit=20):
    """RSS 실패/스로틀 시 DB 에 보관된 기사로 폴백."""
    qs = NewsArticle.objects.all()
    if stock is not None:
        qs = qs.filter(stock=stock)
    elif sector is not None:
        qs = qs.filter(sector=sector)
    elif (query or "").strip():
        qs = qs.filter(title__icontains=query.strip())
    return list(qs[:limit])


def list_articles(query=None, stock=None, sector=None, limit=None):
    """뉴스 목록(F501)·검색(F502)·종목별(F503)·주요(F504) 공통.

    스로틀 윈도(`NEWS_LIST_TTL_SECONDS`) 안이면 외부를 부르지 않고 DB 캐시를 쓴다.
    RSS 가 실패해도 마지막으로 저장된 기사로 폴백해 화면이 깨지지 않게 한다.
    """
    limit = _limit(limit)
    rss_query = build_query(query, stock, sector)
    articles = []

    if _enabled() and not cache.get(_cache_key(rss_query)):
        try:
            items = feeds.fetch_feed(rss_query, limit)
        except feeds.FeedError as exc:
            logger.warning("News feed failed for %r: %s", rss_query, exc)
            items = None
        if items is not None:
            articles = _store(items, stock=stock, sector=sector)
            cache.set(_cache_key(rss_query), True, _ttl())

    if not articles:
        articles = _stored_fallback(query=query, stock=stock, sector=sector, limit=limit)
    return articles[:limit]


def scrapped_article_ids(user, articles):
    """주어진 기사들 중 사용자가 스크랩한 기사 id 집합."""
    if not getattr(user, "is_authenticated", False) or not articles:
        return set()
    ids = [a.id for a in articles]
    return set(
        NewsScrap.objects.filter(user=user, article_id__in=ids).values_list(
            "article_id", flat=True
        )
    )


def add_scrap(user, article):
    """스크랩 추가(멱등). (scrap, created) 반환."""
    return NewsScrap.objects.get_or_create(user=user, article=article)


def remove_scrap(user, article_id):
    """스크랩 삭제. 삭제된 건수 반환."""
    deleted, _ = NewsScrap.objects.filter(user=user, article_id=article_id).delete()
    return deleted
