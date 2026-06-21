from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from profiles.models import Sector

from . import services
from .models import Quote, Stock
from .toss import TossError


class FakeProvider:
    """테스트용 토스 대체 구현."""

    def __init__(self, prices=None, candles=None, stocks=None, fail_prices=False, fail_candles=False):
        self._prices = prices or {}
        self._candles = candles or {}
        self._stocks = stocks or {}
        self.fail_prices = fail_prices
        self.fail_candles = fail_candles

    def get_prices(self, symbols):
        if self.fail_prices:
            raise TossError("boom")
        return {s: self._prices[s] for s in symbols if s in self._prices}

    def get_candles(self, symbol, interval="1d", count=2):
        if self.fail_candles:
            raise TossError("boom")
        return self._candles.get(symbol, [])

    def get_stocks(self, symbols):
        return {s: self._stocks[s] for s in symbols if s in self._stocks}


def _price(symbol, last):
    return {
        "symbol": symbol,
        "lastPrice": last,
        "currency": "KRW",
        "timestamp": "2026-03-25T09:30:00+09:00",
    }


@override_settings(TOSS_QUOTE_TTL_SECONDS=0)  # 매 요청 갱신하도록(결정적 테스트)
class StockApiTests(APITestCase):
    def setUp(self):
        Stock.objects.all().delete()  # 마이그레이션 시드 제거(결정적 테스트)
        self.sector = Sector.objects.get(code="SEMICONDUCTOR")  # 시드된 섹터 재사용
        self.s1 = Stock.objects.create(code="005930", name="삼성전자", market="KOSPI", sector=self.sector)
        self.s2 = Stock.objects.create(code="000660", name="SK하이닉스", market="KOSPI", sector=self.sector)
        services.set_provider(
            FakeProvider(
                prices={"005930": _price("005930", "72000"), "000660": _price("000660", "180000")},
                candles={
                    "005930": [
                        {"closePrice": "72000", "volume": "3521000"},
                        {"closePrice": "70000", "volume": "2984000"},
                    ]
                },
                stocks={"005930": {"symbol": "005930", "sharesOutstanding": "5919637922"}},
            )
        )

    def tearDown(self):
        services.set_provider(None)

    def test_list_returns_stocks_with_price_no_auth(self):
        res = self.client.get("/api/v1/stocks/")
        self.assertEqual(res.status_code, 200)  # AllowAny
        self.assertEqual(res.data["count"], 2)
        row = next(r for r in res.data["results"] if r["code"] == "005930")
        self.assertEqual(row["price"], "72000")
        self.assertEqual(row["sector"], "반도체")

    def test_list_includes_change_rate_without_detail_click(self):
        # 상세를 한 번도 열지 않아도 목록에서 등락률이 계산돼 내려와야 한다.
        res = self.client.get("/api/v1/stocks/")
        row = next(r for r in res.data["results"] if r["code"] == "005930")
        self.assertAlmostEqual(row["change_rate"], (72000 - 70000) / 70000, places=4)
        self.assertEqual(row["change_direction"], "UP")

    def test_filter_market_and_sector(self):
        self.assertEqual(self.client.get("/api/v1/stocks/?sector=SEMICONDUCTOR").data["count"], 2)
        self.assertEqual(self.client.get("/api/v1/stocks/?market=KOSDAQ").data["count"], 0)

    def test_search_by_code_and_name(self):
        r1 = self.client.get("/api/v1/stocks/?search=005930")
        self.assertEqual(r1.data["count"], 1)
        self.assertEqual(r1.data["results"][0]["code"], "005930")
        r2 = self.client.get("/api/v1/stocks/?search=하이닉스")
        self.assertEqual(r2.data["count"], 1)
        self.assertEqual(r2.data["results"][0]["code"], "000660")

    def test_detail_change_and_market_cap(self):
        res = self.client.get("/api/v1/stocks/005930/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["price"], "72000")
        self.assertEqual(res.data["prev_close"], "70000")
        self.assertAlmostEqual(res.data["change_rate"], (72000 - 70000) / 70000, places=4)
        self.assertEqual(res.data["change_direction"], "UP")
        self.assertEqual(res.data["volume"], "3521000")
        self.assertEqual(res.data["market_cap"], 72000 * 5919637922)
        self.assertTrue(res.data["market_cap_display"])

    def test_detail_unknown_code_404(self):
        res = self.client.get("/api/v1/stocks/999999/")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data["code"], "RESOURCE_NOT_FOUND")

    def test_detail_price_failure_is_delayed_not_500(self):
        services.refresh_prices([self.s1])  # 정상값 저장(작동하는 provider)
        services.set_provider(FakeProvider(fail_prices=True, fail_candles=True))
        res = self.client.get("/api/v1/stocks/005930/")
        self.assertEqual(res.status_code, 200)  # 500 아님 (부분 실패 허용)
        self.assertTrue(res.data["is_delayed"])
        self.assertEqual(res.data["price"], "72000")  # 마지막 정상값 폴백

    def test_list_price_failure_does_not_break(self):
        services.set_provider(FakeProvider(fail_prices=True))
        res = self.client.get("/api/v1/stocks/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 2)

    def test_empty_candles_marked_and_not_refetched_same_day(self):
        # 토스가 일봉을 주지 않는 종목도 '오늘 시도함'으로 기록해, 같은 날 재요청엔 외부 호출하지 않는다.
        calls = []

        class Counting(FakeProvider):
            def get_candles(self, symbol, interval="1d", count=2):
                calls.append(symbol)
                return super().get_candles(symbol, interval, count)

        services.set_provider(Counting())  # 캔들 데이터 없음(빈 응답)
        services.ensure_daily_candles([self.s1])
        services.ensure_daily_candles([self.s1])
        self.assertEqual(calls, ["005930"])  # 두 번째는 호출 생략
        self.assertEqual(Quote.objects.get(stock=self.s1).daily_as_of, timezone.localdate())

    def test_sectors_endpoint_public(self):
        res = self.client.get("/api/v1/stocks/sectors/")
        self.assertEqual(res.status_code, 200)
        codes = {s["code"] for s in res.data["sectors"]}
        self.assertIn("SEMICONDUCTOR", codes)
