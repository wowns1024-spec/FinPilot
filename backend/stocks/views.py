from django.db.models import Case, IntegerField, Q, When
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.models import Sector

from . import services
from .models import Quote, Stock


class StockPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class StockListView(APIView):
    """F401 종목 목록 / F402 종목 검색. (인증 불필요)"""

    permission_classes = [AllowAny]

    def get(self, request):
        qs = Stock.objects.filter(is_active=True).select_related("sector")

        market = request.query_params.get("market")
        if market:
            qs = qs.filter(market=market.upper())

        sector = request.query_params.get("sector")
        if sector:
            qs = qs.filter(sector__code=sector)

        search = (request.query_params.get("search") or "").strip()
        if search:
            # F402: 코드 정확일치 우선 + 이름 부분일치
            qs = qs.filter(Q(code__iexact=search) | Q(name__icontains=search)).annotate(
                _exact=Case(
                    When(code__iexact=search, then=0),
                    default=1,
                    output_field=IntegerField(),
                )
            ).order_by("_exact", "name")
        else:
            ordering = request.query_params.get("ordering", "code")
            if ordering not in ("code", "name", "market"):
                ordering = "code"
            qs = qs.order_by(ordering)

        paginator = StockPagination()
        page = paginator.paginate_queryset(qs, request)
        # 페이지 종목만 시세 갱신(TTL 지난 것만). 실패해도 캐시값/None 으로 표시(F401 예외처리).
        services.ensure_fresh_prices(page)
        # 전일종가(일봉)까지 채워 등락률을 목록에서 바로 표시(상세 클릭 전에도). 종목당 하루 1회.
        services.ensure_daily_candles(page)
        quotes = {q.stock_id: q for q in Quote.objects.filter(stock__in=page)}
        items = [services.serialize_list_item(s, quotes.get(s.id)) for s in page]
        return paginator.get_paginated_response(items)


class StockDetailView(APIView):
    """F403~F407 종목 상세. 시세/뉴스 일부 실패에도 페이지가 깨지지 않는다. (인증 불필요)"""

    permission_classes = [AllowAny]

    def get(self, request, code):
        try:
            stock = Stock.objects.select_related("sector").get(code=code, is_active=True)
        except Stock.DoesNotExist:
            return Response(
                {"code": "RESOURCE_NOT_FOUND", "message": "종목을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        delayed = services.ensure_fresh_prices([stock])  # 현재가
        services.ensure_daily(stock)  # 전일종가·거래량·발행주식수
        quote = Quote.objects.filter(stock=stock).first()
        return Response(services.serialize_detail(stock, quote, delayed=delayed))


class SectorListView(APIView):
    """종목 목록 필터용 활성 섹터 목록. (인증 불필요)"""

    permission_classes = [AllowAny]

    def get(self, request):
        sectors = Sector.objects.filter(is_active=True)
        return Response(
            {"sectors": [{"code": s.code, "name": s.name} for s in sectors]}
        )
