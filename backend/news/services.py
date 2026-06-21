import hashlib
import html
import json
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib import parse, request
from urllib.error import HTTPError, URLError

from django.conf import settings


SECTOR_KEYWORDS = {
    "semiconductor": {"label": "반도체", "query": "반도체 삼성전자 SK하이닉스"},
    "battery": {"label": "2차전지", "query": "2차전지 배터리 LG에너지솔루션"},
    "defense": {"label": "방산", "query": "방산 한화에어로스페이스 현대로템"},
    "ai": {"label": "AI", "query": "AI 인공지능 반도체"},
    "energy": {"label": "에너지", "query": "에너지 전력 원전"},
    "game": {"label": "게임", "query": "게임 크래프톤 엔씨소프트"},
    "bio": {"label": "바이오", "query": "바이오 제약 삼성바이오로직스 셀트리온"},
    "auto": {"label": "자동차", "query": "자동차 현대차 기아 전기차"},
    "finance": {"label": "금융", "query": "금융 은행 증권 보험"},
}

DEFAULT_NEWS_QUERY = "경제 금융 증권 주식"
TAG_RE = re.compile(r"<[^>]+>")


class NaverNewsAPIError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def clean_text(value):
    text = html.unescape(value or "")
    text = TAG_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_pub_date(value):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def publisher_from_link(link):
    try:
        host = parse.urlparse(link or "").netloc
    except ValueError:
        return ""
    return host.removeprefix("www.")


def infer_sector(title, summary, requested_sector=""):
    if requested_sector and requested_sector in SECTOR_KEYWORDS:
        return SECTOR_KEYWORDS[requested_sector]["label"]

    text = f"{title} {summary}".lower()
    for sector in SECTOR_KEYWORDS.values():
        label = sector["label"]
        words = sector["query"].lower().split()
        if label.lower() in text or any(word in text for word in words):
            return label
    return "경제"


def item_id(link):
    return hashlib.sha256((link or "").encode("utf-8")).hexdigest()[:16]


def normalize_news_item(item, sector=""):
    title = clean_text(item.get("title"))
    summary = clean_text(item.get("description"))
    link = item.get("link") or item.get("originallink") or ""
    original = item.get("originallink") or link
    published_at = parse_pub_date(item.get("pubDate"))

    return {
        "id": item_id(link),
        "title": title,
        "summary": summary,
        "publisher": publisher_from_link(original or link),
        "published_at": published_at.isoformat() if published_at else None,
        "link": link,
        "originallink": original,
        "sector": infer_sector(title, summary, sector),
    }


def naver_news_search(query="", sector="", sort="date", display=20, start=1):
    display = max(1, min(int(display or 20), 100))
    start = max(1, min(int(start or 1), 1000))
    sort = sort if sort in {"date", "sim"} else "date"

    sector_query = SECTOR_KEYWORDS.get(sector, {}).get("query", "")
    search_query = " ".join(
        part for part in [query.strip(), sector_query, DEFAULT_NEWS_QUERY] if part
    )
    if not search_query:
        search_query = DEFAULT_NEWS_QUERY

    if not settings.NAVER_CLIENT_ID or not settings.NAVER_CLIENT_SECRET:
        raise NaverNewsAPIError("네이버 API Client ID/Secret이 설정되지 않았습니다.", 503)

    params = parse.urlencode(
        {
            "query": search_query,
            "display": display,
            "start": start,
            "sort": sort,
        }
    )
    req = request.Request(
        f"{settings.NAVER_SEARCH_API_URL}?{params}",
        headers={
            "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = "네이버 뉴스 API 인증 또는 요청에 실패했습니다."
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            message = payload.get("errorMessage") or message
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        raise NaverNewsAPIError(message, exc.code) from exc
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise NaverNewsAPIError("네이버 뉴스 API 응답을 가져오지 못했습니다.", 502) from exc

    return {
        "items": [normalize_news_item(item, sector) for item in body.get("items", [])],
        "total": body.get("total", 0),
        "start": body.get("start", start),
        "display": body.get("display", display),
        "query": body.get("lastBuildDate") and search_query,
        "source": "naver",
    }


def categories():
    return [
        {"key": key, "label": value["label"], "query": value["query"]}
        for key, value in SECTOR_KEYWORDS.items()
    ]
