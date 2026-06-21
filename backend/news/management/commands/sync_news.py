"""F500 뉴스를 미리 수집해 NewsArticle 에 채운다(스로틀 무시·강제 갱신).

    python manage.py sync_news                # 주요 뉴스 + 활성 산업별
    python manage.py sync_news --stocks       # 위 + 활성 종목별
    python manage.py sync_news --code 005930  # 특정 종목만
"""

from django.core.cache import cache
from django.core.management.base import BaseCommand

from news import services
from news.services import _cache_key, build_query
from profiles.models import Sector
from stocks.models import Stock


class Command(BaseCommand):
    help = "주요·산업별·종목별 뉴스를 RSS 에서 수집해 NewsArticle 에 저장한다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stocks", action="store_true", help="활성 종목별 뉴스도 수집한다."
        )
        parser.add_argument(
            "--code",
            action="append",
            dest="codes",
            help="특정 종목코드만 수집(여러 번 지정 가능). --stocks 보다 우선.",
        )

    def _refresh(self, label, **kwargs):
        # 스로틀 캐시를 비워 강제로 외부를 다시 부른다.
        cache.delete(_cache_key(build_query(**kwargs)))
        n = len(services.list_articles(**kwargs))
        self.stdout.write(f"  · {label}: {n}건")
        return n

    def handle(self, *args, **options):
        codes = options.get("codes")
        if codes:
            stocks = list(Stock.objects.filter(is_active=True, code__in=codes))
            total = sum(self._refresh(s.name, stock=s) for s in stocks)
            self.stdout.write(self.style.SUCCESS(f"종목 뉴스 수집 완료 · 총 {total}건"))
            return

        total = self._refresh("주요 뉴스")
        for sector in Sector.objects.filter(is_active=True):
            total += self._refresh(sector.name, sector=sector)

        if options.get("stocks"):
            for stock in Stock.objects.filter(is_active=True).select_related("sector"):
                total += self._refresh(stock.name, stock=stock)

        self.stdout.write(self.style.SUCCESS(f"뉴스 수집 완료 · 총 {total}건"))
