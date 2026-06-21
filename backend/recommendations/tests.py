from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from profiles.models import InvestmentProfile, Sector
from stocks import services as stock_services
from stocks.models import Stock

from . import gms, metrics, news, scoring
from .models import Recommendation, StockMetric, StockNewsSummary

User = get_user_model()


class _NoToss:
    """ensure_fresh_prices 가 외부를 부르지 않도록(테스트 결정성)."""

    def get_prices(self, symbols):
        return {}

    def get_candles(self, symbol, interval="1d", count=2):
        return []

    def get_stocks(self, symbols):
        return {}


class _FakeGms:
    def __init__(self, available=True):
        self._available = available
        self.calls = 0
        self.prompts = []

    def available(self):
        return self._available

    def generate(self, prompt):
        self.calls += 1
        self.prompts.append(prompt)
        return "GMS가 생성한 추천 이유입니다."


def _candles(close_seq, vol=1_000_000):
    # close_seq: 최신순(앞이 최근)
    return [{"closePrice": str(c), "volume": str(vol)} for c in close_seq]


class GmsClientTests(SimpleTestCase):
    @override_settings(
        GMS_API_BASE="https://gms.ssafy.io/gmsapi/",
        GMS_API_KEY="test-key",
        GMS_MODEL="gpt-4.1",
    )
    @patch("recommendations.gms.requests.post")
    def test_generate_uses_gms_openai_responses_endpoint(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"output_text": " 추천 이유입니다. "}

        text = gms.GmsClient().generate("테스트 프롬프트")

        self.assertEqual(text, "추천 이유입니다.")
        mock_post.assert_called_once()
        url = mock_post.call_args.args[0]
        kwargs = mock_post.call_args.kwargs
        self.assertEqual(
            url, "https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses"
        )
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["json"]["model"], "gpt-4.1")
        self.assertEqual(kwargs["json"]["input"], "테스트 프롬프트")
        self.assertEqual(kwargs["json"]["max_output_tokens"], 200)


class MetricsTests(APITestCase):
    def test_metrics_from_candles(self):
        result = metrics.metrics_from_candles(_candles([110, 105, 100]))
        self.assertIsNotNone(result)
        volatility, momentum, liquidity, n = result
        self.assertAlmostEqual(momentum, (110 - 100) / 100, places=4)  # +10%
        self.assertEqual(n, 3)
        self.assertGreater(volatility, 0)
        self.assertGreater(liquidity, 0)

    def test_too_few_candles_returns_none(self):
        self.assertIsNone(metrics.metrics_from_candles(_candles([100])))


class _FakeNewsResponse:
    status_code = 200
    content = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>삼성전자, HBM 공급 기대 확대 - 테스트뉴스</title>
      <link>https://example.com/hbm</link>
      <description><![CDATA[반도체 업황 회복 기대가 커지고 있다는 내용입니다.]]></description>
      <pubDate>Sun, 21 Jun 2026 07:00:00 GMT</pubDate>
      <source url="https://example.com">테스트뉴스</source>
    </item>
    <item>
      <title>삼성전자 실적 전망 개선 - 다른뉴스</title>
      <link>https://example.com/earnings</link>
      <description>메모리 수요 관련 기사입니다.</description>
      <pubDate>Sun, 21 Jun 2026 06:00:00 GMT</pubDate>
      <source url="https://example.org">다른뉴스</source>
    </item>
  </channel>
</rss>""".encode("utf-8")

    def raise_for_status(self):
        return None


class NewsSummaryTests(APITestCase):
    def setUp(self):
        self.semi = Sector.objects.get(code="SEMICONDUCTOR")
        self.stock = Stock.objects.create(
            code="900003", name="삼성전자테스트", market="KOSPI", sector=self.semi
        )

    @override_settings(NEWS_SUMMARY_ENABLED=True, NEWS_SUMMARY_LIMIT=2)
    @patch("recommendations.news.requests.get")
    def test_refresh_news_summary_from_rss(self, mock_get):
        mock_get.return_value = _FakeNewsResponse()

        self.assertTrue(news.refresh_news_summary(self.stock))

        summary = StockNewsSummary.objects.get(stock=self.stock)
        self.assertEqual(summary.source, "rss")
        self.assertIn("삼성전자테스트 관련 최근 뉴스 헤드라인 요약", summary.summary)
        self.assertIn("HBM 공급 기대", summary.summary)
        self.assertIn("실적 전망 개선", summary.summary)
        self.assertEqual(len(summary.articles), 2)
        self.assertEqual(summary.articles[0]["url"], "https://example.com/hbm")
        self.assertEqual(summary.articles[0]["source"], "테스트뉴스")


class ScoringTests(APITestCase):
    def setUp(self):
        self.semi = Sector.objects.get(code="SEMICONDUCTOR")
        self.bio = Sector.objects.get(code="BIO")
        self.user = User.objects.create_user("w", "w@e.com", "pw12345!")
        self.profile = InvestmentProfile.objects.create(
            user=self.user,
            available_asset=2,
            risk_type="BALANCED",
            investment_period="LONG",
            investment_goal="GROWTH",
        )
        self.profile.sectors.set([self.semi])

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(scoring.weights_for(self.profile).values()), 1.0, places=6)

    def test_sector_match_ranks_higher(self):
        s_match = Stock.objects.create(code="900001", name="반도체주", market="KOSPI", sector=self.semi)
        s_other = Stock.objects.create(code="900002", name="바이오주", market="KOSPI", sector=self.bio)
        scored = scoring.score_candidates(self.profile, [(s_other, None), (s_match, None)])
        self.assertEqual(scored[0][0].code, "900001")  # 관심산업 매치 종목이 상위


class RecommendationApiTests(APITestCase):
    def setUp(self):
        self.news_settings = override_settings(NEWS_SUMMARY_ENABLED=False)
        self.news_settings.enable()
        Stock.objects.all().delete()  # 시드 제거(결정적 테스트)
        self.semi = Sector.objects.get(code="SEMICONDUCTOR")
        self.bio = Sector.objects.get(code="BIO")
        self.s1 = Stock.objects.create(code="005930", name="삼성전자", market="KOSPI", sector=self.semi)
        self.s2 = Stock.objects.create(code="000660", name="SK하이닉스", market="KOSPI", sector=self.semi)
        self.s3 = Stock.objects.create(code="207940", name="삼성바이오", market="KOSPI", sector=self.bio)

        self.user = User.objects.create_user("u", "u@e.com", "pw12345!")
        self.profile = InvestmentProfile.objects.create(
            user=self.user,
            available_asset=3,
            risk_type="ACTIVE",
            investment_period="SWING",
            investment_goal="GROWTH",
        )
        self.profile.sectors.set([self.semi])

        stock_services.set_provider(_NoToss())
        gms.set_provider(_FakeGms(available=False))  # 기본: 템플릿
        self.client.force_authenticate(self.user)

    def tearDown(self):
        stock_services.set_provider(None)
        gms.set_provider(None)
        self.news_settings.disable()

    def test_post_creates_recommendation_template(self):
        res = self.client.post("/api/v1/recommendations/")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["reason_source"], "template")
        self.assertGreaterEqual(len(res.data["items"]), 1)
        self.assertIn(res.data["items"][0]["stock"]["code"], ("005930", "000660"))
        for item in res.data["items"]:
            self.assertTrue(item["reason"])

    def test_get_returns_active_and_404_when_none(self):
        self.assertEqual(self.client.get("/api/v1/recommendations/").status_code, 404)
        self.client.post("/api/v1/recommendations/")
        self.assertEqual(self.client.get("/api/v1/recommendations/").status_code, 200)

    def test_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post("/api/v1/recommendations/").status_code, 401)

    def test_post_without_profile_returns_400(self):
        self.profile.delete()
        res = self.client.post("/api/v1/recommendations/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "PROFILE_REQUIRED")

    def test_profile_change_invalidates_recommendation(self):
        self.client.post("/api/v1/recommendations/")
        self.assertEqual(Recommendation.objects.filter(user=self.user, is_active=True).count(), 1)
        res = self.client.patch(
            "/api/v1/investment-profile/", {"risk_type": "STABLE"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Recommendation.objects.filter(user=self.user, is_active=True).count(), 0)

    def test_gms_source_when_available(self):
        gms.set_provider(_FakeGms(available=True))
        res = self.client.post("/api/v1/recommendations/")
        self.assertEqual(res.data["reason_source"], "gms")
        self.assertEqual(res.data["items"][0]["reason"], "GMS가 생성한 추천 이유입니다.")

    def test_gms_prompt_includes_selection_result_and_news_summary(self):
        provider = _FakeGms(available=True)
        gms.set_provider(provider)
        StockMetric.objects.create(
            stock=self.s1, volatility=0.02, momentum=0.20, liquidity=1e9
        )
        StockMetric.objects.create(
            stock=self.s2, volatility=0.08, momentum=-0.05, liquidity=2e8
        )
        StockNewsSummary.objects.create(
            stock=self.s1,
            summary="HBM 수요 확대와 반도체 업황 회복 기대가 최근 뉴스에서 언급되었습니다.",
            articles=[
                {
                    "title": "삼성전자, HBM 공급 기대 확대 - 테스트뉴스",
                    "url": "https://example.com/hbm",
                    "source": "테스트뉴스",
                    "source_url": "https://example.com",
                    "published_at": "2026-06-21T07:00:00+00:00",
                }
            ],
        )

        res = self.client.post("/api/v1/recommendations/")

        self.assertEqual(res.data["reason_source"], "gms")
        self.assertGreater(provider.calls, 0)
        prompt = provider.prompts[0]
        self.assertIn("추천 선정 결과: 1위", prompt)
        self.assertIn("최종 점수", prompt)
        self.assertIn("점수 구성", prompt)
        self.assertIn("시세 지표", prompt)
        self.assertIn("최근 뉴스 요약", prompt)
        self.assertIn("HBM 수요 확대", prompt)
        first_item = res.data["items"][0]
        self.assertEqual(first_item["stock"]["code"], "005930")
        self.assertEqual(first_item["news_articles"][0]["url"], "https://example.com/hbm")

    @patch("recommendations.services.news.ensure_news_summaries")
    def test_post_refreshes_news_summaries_before_generating_reasons(self, mock_news):
        gms.set_provider(_FakeGms(available=True))

        self.client.post("/api/v1/recommendations/")

        mock_news.assert_called_once()
        stocks = mock_news.call_args.args[0]
        self.assertGreaterEqual(len(stocks), 1)
        self.assertTrue(all(isinstance(stock, Stock) for stock in stocks))

    def test_momentum_influences_rank(self):
        # 같은 관심산업 두 종목 중 모멘텀 높은 쪽이 상위
        StockMetric.objects.create(stock=self.s1, volatility=0.02, momentum=0.20, liquidity=1e9)
        StockMetric.objects.create(stock=self.s2, volatility=0.02, momentum=-0.05, liquidity=1e9)
        res = self.client.post("/api/v1/recommendations/")
        codes = [it["stock"]["code"] for it in res.data["items"]]
        self.assertLess(codes.index("005930"), codes.index("000660"))
