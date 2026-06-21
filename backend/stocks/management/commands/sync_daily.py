"""일봉·발행주식수·현재가를 미리 캐시해 첫 종목 조회의 외부 호출 지연을 없앤다.

매 거래일 아침 한 번 실행하면(예: Windows 작업 스케줄러로 평일 08:30), 사용자의 첫
목록/상세 조회가 캐시만으로 즉시 응답한다. 전일종가·거래량은 하루 한 번만 바뀌므로 이
배치로 충분하고, 장중 현재가는 요청 시 30초 TTL 로 별도 갱신된다.

토스 캔들은 종목당 단건 호출 + 레이트리밋이 있어 한 번에 다 못 받을 수 있으므로,
유니버스가 다 채워질 때까지 몇 번 더 시도한다(요청 경로 밖이라 다소 걸려도 무방).

    python manage.py sync_daily
"""

import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from stocks import services
from stocks.models import Quote, Stock

_MAX_PASSES = 4  # 일봉 재시도 횟수(레이트리밋으로 빠진 종목 보충)


class Command(BaseCommand):
    help = "활성 종목의 일봉·발행주식수·현재가를 미리 캐시한다(첫 로드 가속)."

    def handle(self, *args, **options):
        stocks = list(Stock.objects.filter(is_active=True))
        if not stocks:
            self.stdout.write("활성 종목이 없습니다. 종목 시드를 먼저 적용하세요.")
            return

        today = timezone.localdate()
        # 전일종가·거래량(일봉). ensure_daily_candles 는 '오늘 미시도' 종목만 다시 부르므로,
        # 반복 호출하면 레이트리밋으로 빠졌던 종목이 점차 채워진다.
        marked = 0
        for _ in range(_MAX_PASSES):
            services.ensure_daily_candles(stocks)
            marked = Quote.objects.filter(stock__in=stocks, daily_as_of=today).count()
            if marked >= len(stocks):
                break
            time.sleep(0.5)  # 레이트리밋 완화

        services.ensure_shares_outstanding(stocks)  # 발행주식수(시총용) — 1배치
        ok = services.refresh_prices(stocks)        # 현재가 — 1배치

        with_change = Quote.objects.filter(stock__in=stocks).exclude(prev_close=None).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"동기화 완료 · 종목 {len(stocks)}개 · 일봉 시도완료 {marked}개 "
                f"(등락률 산출 {with_change}개) · 현재가 {'갱신' if ok else '실패(폴백 유지)'}"
            )
        )
