from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from profiles.models import Sector
from stocks.models import Stock

from . import feeds
from .models import NewsArticle, NewsScrap

User = get_user_model()


class _FakeRss:
    """Google News RSS 검색 응답 흉내."""

    status_code = 200
    content = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>삼성전자, HBM 공급 기대 확대 - 테스트뉴스</title>
      <link>https://example.com/hbm</link>
      <description><![CDATA[반도체 업황 회복 기대가 커지고 있다.]]></description>
      <pubDate>Sun, 21 Jun 2026 07:00:00 GMT</pubDate>
      <source url="https://example.com">테스트뉴스</source>
    </item>
    <item>
      <title>코스피 상승 마감 - 다른뉴스</title>
      <link>https://example.com/kospi</link>
      <description>외국인 매수세가 유입됐다.</description>
      <pubDate>Sun, 21 Jun 2026 06:00:00 GMT</pubDate>
      <source url="https://example.org">다른뉴스</source>
    </item>
  </channel>
</rss>""".encode("utf-8")

    def raise_for_status(self):
        return None


@override_settings(NEWS_ENABLED=True, NEWS_LIST_TTL_SECONDS=0)
class NewsListTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.semi = Sector.objects.get(code="SEMICONDUCTOR")
        self.stock = Stock.objects.create(
            code="900100", name="삼성전자테스트", market="KOSPI", sector=self.semi
        )

    @patch("news.feeds.requests.get")
    def test_list_is_public_and_upserts_articles(self, mock_get):
        mock_get.return_value = _FakeRss()

        res = self.client.get("/api/v1/news/")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 2)
        self.assertEqual(NewsArticle.objects.count(), 2)
        first = res.data["results"][0]
        self.assertEqual(first["url"], "https://example.com/hbm")
        self.assertEqual(first["source"], "테스트뉴스")
        self.assertFalse(first["is_scrapped"])

    @patch("news.feeds.requests.get")
    def test_list_by_stock_tags_articles(self, mock_get):
        mock_get.return_value = _FakeRss()

        res = self.client.get("/api/v1/news/", {"stock": "900100"})

        self.assertEqual(res.status_code, 200)
        self.assertTrue(NewsArticle.objects.filter(stock=self.stock).exists())
        self.assertEqual(res.data["results"][0]["stock_code"], "900100")

    def test_list_unknown_stock_returns_404(self):
        res = self.client.get("/api/v1/news/", {"stock": "000000"})
        self.assertEqual(res.status_code, 404)

    @patch("news.feeds.requests.get", side_effect=feeds.requests.RequestException("boom"))
    def test_list_falls_back_to_db_on_rss_failure(self, _mock_get):
        NewsArticle.objects.create(
            url="https://example.com/cached",
            title="캐시된 기사",
            stock=self.stock,
        )

        res = self.client.get("/api/v1/news/", {"stock": "900100"})

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["title"], "캐시된 기사")


@override_settings(NEWS_ENABLED=True, NEWS_LIST_TTL_SECONDS=0)
class NewsScrapTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("u", "u@e.com", "pw12345!")
        self.article = NewsArticle.objects.create(
            url="https://example.com/a", title="스크랩 대상 기사"
        )
        self.client.force_authenticate(self.user)

    def test_scrap_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/v1/news/scraps/").status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/v1/news/scraps/", {"article_id": self.article.id}
            ).status_code,
            401,
        )

    def test_add_list_and_remove_scrap(self):
        res = self.client.post(
            "/api/v1/news/scraps/", {"article_id": self.article.id}
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["is_scrapped"])
        self.assertEqual(NewsScrap.objects.filter(user=self.user).count(), 1)

        res = self.client.get("/api/v1/news/scraps/")
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], self.article.id)

        res = self.client.delete(f"/api/v1/news/scraps/{self.article.id}/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(NewsScrap.objects.filter(user=self.user).count(), 0)

    def test_add_scrap_is_idempotent(self):
        self.client.post("/api/v1/news/scraps/", {"article_id": self.article.id})
        res = self.client.post(
            "/api/v1/news/scraps/", {"article_id": self.article.id}
        )
        self.assertEqual(res.status_code, 200)  # 이미 존재 → 200
        self.assertEqual(NewsScrap.objects.filter(user=self.user).count(), 1)

    def test_remove_missing_scrap_returns_404(self):
        res = self.client.delete(f"/api/v1/news/scraps/{self.article.id}/")
        self.assertEqual(res.status_code, 404)

    def test_post_unknown_article_returns_404(self):
        res = self.client.post("/api/v1/news/scraps/", {"article_id": 999999})
        self.assertEqual(res.status_code, 404)

    @patch("news.feeds.requests.get")
    def test_list_marks_scrapped(self, mock_get):
        mock_get.return_value = _FakeRss()
        # 먼저 목록을 받아 기사가 업서트되게 한 뒤, 그 중 하나를 스크랩
        self.client.get("/api/v1/news/")
        article = NewsArticle.objects.get(url="https://example.com/hbm")
        self.client.post("/api/v1/news/scraps/", {"article_id": article.id})

        cache.clear()  # 스로틀 우회(재호출)
        res = self.client.get("/api/v1/news/")
        marked = {r["url"]: r["is_scrapped"] for r in res.data["results"]}
        self.assertTrue(marked["https://example.com/hbm"])
        self.assertFalse(marked["https://example.com/kospi"])
