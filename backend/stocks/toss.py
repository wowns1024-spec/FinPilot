"""토스증권 Open API 클라이언트.

OAuth2 client_credentials 토큰을 캐시·재사용하고(F408), 시세/종목정보를 조회한다.
외부 호출 실패는 TossError 로 올려 서비스 계층에서 폴백 처리한다.
"""

import requests
from django.conf import settings
from django.core.cache import cache

_TOKEN_CACHE_KEY = "toss:access_token"


class TossError(Exception):
    """토스 API 호출 실패."""


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


class TossClient:
    def __init__(self):
        self.base = settings.TOSS_API_BASE.rstrip("/")
        self.client_id = settings.TOSS_CLIENT_ID
        self.client_secret = settings.TOSS_CLIENT_SECRET

    # --- 토큰 관리 (F408) ---
    def _issue_token(self):
        # 자격증명 미설정 시 네트워크 호출 없이 즉시 실패(폴백 유도, 지연 방지)
        if not self.client_id or not self.client_secret:
            raise TossError("toss credentials not configured")
        try:
            resp = requests.post(
                f"{self.base}/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
        except requests.RequestException as exc:
            raise TossError(f"token request failed: {exc}") from exc
        if resp.status_code != 200:
            raise TossError(f"token issue failed ({resp.status_code})")
        data = resp.json()
        token = data["access_token"]
        ttl = max(int(data.get("expires_in", 86400)) - 60, 60)  # 만료 60초 전 갱신
        cache.set(_TOKEN_CACHE_KEY, token, ttl)
        return token

    def _token(self, force=False):
        if not force:
            cached = cache.get(_TOKEN_CACHE_KEY)
            if cached:
                return cached
        return self._issue_token()

    def _get(self, path, params=None, _retry=True):
        try:
            resp = requests.get(
                f"{self.base}{path}",
                params=params,
                headers={"Authorization": f"Bearer {self._token()}"},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise TossError(f"GET {path} failed: {exc}") from exc
        if resp.status_code == 401 and _retry:
            self._token(force=True)  # 만료/401 시 1회 재발급 후 재시도
            return self._get(path, params, _retry=False)
        if resp.status_code != 200:
            raise TossError(f"GET {path} -> {resp.status_code}")
        return resp.json().get("result")

    # --- Market Data / Stock Info ---
    def get_prices(self, symbols):
        """현재가 다건. {symbol: {lastPrice, currency, timestamp}}"""
        out = {}
        for chunk in _chunks(list(symbols), 200):
            for item in self._get("/api/v1/prices", {"symbols": ",".join(chunk)}) or []:
                out[item["symbol"]] = item
        return out

    def get_stocks(self, symbols):
        """종목 기본정보 다건. {symbol: {name, market, sharesOutstanding, ...}}"""
        out = {}
        for chunk in _chunks(list(symbols), 200):
            for item in self._get("/api/v1/stocks", {"symbols": ",".join(chunk)}) or []:
                out[item["symbol"]] = item
        return out

    def get_candles(self, symbol, interval="1d", count=2):
        """캔들(OHLCV) 최신순 리스트."""
        result = self._get(
            "/api/v1/candles",
            {"symbol": symbol, "interval": interval, "count": count},
        )
        return (result or {}).get("candles", [])
