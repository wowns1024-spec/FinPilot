"""추천용 뉴스 요약을 미리 수집한다.

    python manage.py sync_news_summaries
    python manage.py sync_news_summaries --code 005930 --code 000660
"""

from django.core.management.base import BaseCommand

from recommendations import news
from stocks.models import Stock


class Command(BaseCommand):
    help = "활성 종목의 최신 뉴스 요약을 RSS에서 수집해 StockNewsSummary 에 저장한다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--code",
            action="append",
            dest="codes",
            help="특정 종목코드만 갱신한다. 여러 번 지정 가능.",
        )

    def handle(self, *args, **options):
        qs = Stock.objects.filter(is_active=True).select_related("sector")
        codes = options.get("codes")
        if codes:
            qs = qs.filter(code__in=codes)
        stocks = list(qs)
        if not stocks:
            self.stdout.write("갱신할 종목이 없습니다.")
            return

        updated = 0
        for stock in stocks:
            if news.refresh_news_summary(stock):
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"뉴스 요약 갱신 완료 · 대상 {len(stocks)}개 중 {updated}개 저장"
            )
        )
