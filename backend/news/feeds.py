"""F500 뉴스 수집 — Google News RSS 검색을 파싱해 기사 후보를 만든다.

키 없이 쓸 수 있는 RSS 라서 네트워크·파싱 상태에 따라 실패할 수 있다. 호출측이 폴백할
수 있도록 실패는 ``FeedError`` 로 올린다(빈 결과 ``[]`` 와 구분).
"""

import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests
from django.conf import settings
from django.utils import timezone


class FeedError(Exception):
    """RSS 수집/파싱 실패."""


def _timeout():
    return max(int(getattr(settings, "NEWS_LIST_TIMEOUT_SECONDS", 5)), 1)


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
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.astimezone(timezone.UTC)


def fetch_feed(query, limit):
    """RSS 검색으로 최신 뉴스 후보 ``[{title,url,summary,source,source_url,published_at}]`` 반환."""
    limit = max(int(limit), 1)
    try:
        resp = requests.get(
            getattr(settings, "NEWS_RSS_BASE", "https://news.google.com/rss/search"),
            params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"},
            timeout=_timeout(),
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise FeedError(f"news request failed: {exc}") from exc

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        raise FeedError(f"bad news rss: {exc}") from exc

    items = []
    for node in root.findall("./channel/item"):
        title = _strip_html(node.findtext("title"))
        url = (node.findtext("link") or "").strip()
        if not title or not url:
            continue
        source = node.find("source")
        items.append(
            {
                "title": title,
                "url": url,
                "summary": _strip_html(node.findtext("description")),
                "source": _strip_html(source.text if source is not None else ""),
                "source_url": (source.get("url") if source is not None else "") or "",
                "published_at": _published_at(node.findtext("pubDate")),
            }
        )
        if len(items) >= limit:
            break
    return items
