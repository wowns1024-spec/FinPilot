"""시세 파생 지표(변동성·모멘텀·유동성)를 계산해 StockMetric 에 저장한다(F300 점수 입력).

토스 일봉을 종목당 단건으로 받으므로(+레이트리밋) 저동시성으로 호출하고, 빠진 종목은
몇 번 더 시도한다. 추천 품질을 위해 매 거래일 1회(예: 장 마감 후) 실행 권장.

    python manage.py compute_metrics
"""

import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from recommendations import metrics
from recommendations.models import StockMetric
from stocks.models import Stock

_MAX_PASSES = 4


class Command(BaseCommand):
    help = "활성 종목의 시세 파생 지표를 계산해 StockMetric 에 저장한다(F300)."

    def handle(self, *args, **options):
        stocks = list(Stock.objects.filter(is_active=True))
        if not stocks:
            self.stdout.write("활성 종목이 없습니다. 종목 시드를 먼저 적용하세요.")
            return

        today = timezone.localdate()
        for _ in range(_MAX_PASSES):
            done = set(
                StockMetric.objects.filter(stock__in=stocks, as_of=today).values_list(
                    "stock_id", flat=True
                )
            )
            todo = [s for s in stocks if s.id not in done]
            if not todo:
                break
            if metrics.compute_metrics(todo) == 0:
                break  # 진전 없음(데이터 없는 종목만 남음)
            time.sleep(0.5)  # 레이트리밋 완화

        have = StockMetric.objects.filter(stock__in=stocks, as_of=today).count()
        self.stdout.write(
            self.style.SUCCESS(f"지표 계산 완료 · 종목 {len(stocks)}개 중 {have}개 스냅샷 저장")
        )
