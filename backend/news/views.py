from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.models import Sector
from stocks.models import Stock

from . import services
from .models import NewsArticle, NewsScrap
from .serializers import NewsArticleSerializer


class NewsListView(APIView):
    """F501 뉴스 목록 / F502 검색 / F503 종목별 / F504 주요 뉴스. (인증 불필요)

    params: q(키워드), stock(종목코드), sector(산업코드), limit. 로그인 시 스크랩 여부 포함.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q")
        limit = request.query_params.get("limit")

        stock = None
        code = request.query_params.get("stock")
        if code:
            stock = Stock.objects.filter(code=code, is_active=True).first()
            if stock is None:
                return Response(
                    {"code": "RESOURCE_NOT_FOUND", "message": "종목을 찾을 수 없습니다."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        sector = None
        sector_code = request.query_params.get("sector")
        if sector_code and stock is None:
            sector = Sector.objects.filter(code=sector_code, is_active=True).first()

        articles = services.list_articles(
            query=query, stock=stock, sector=sector, limit=limit
        )
        scrapped_ids = services.scrapped_article_ids(request.user, articles)
        data = NewsArticleSerializer(
            articles, many=True, context={"scrapped_ids": scrapped_ids}
        ).data
        return Response({"count": len(data), "results": data})


class NewsScrapView(APIView):
    """F505 스크랩 목록(GET)·추가(POST). 인증 필요."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        scraps = (
            NewsScrap.objects.filter(user=request.user)
            .select_related("article", "article__stock")
        )
        articles = [s.article for s in scraps]
        scrapped_ids = {a.id for a in articles}
        data = NewsArticleSerializer(
            articles, many=True, context={"scrapped_ids": scrapped_ids}
        ).data
        return Response({"count": len(data), "results": data})

    def post(self, request):
        article_id = request.data.get("article_id")
        if not article_id:
            return Response(
                {"code": "INVALID_REQUEST", "message": "article_id 가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        article = NewsArticle.objects.filter(id=article_id).first()
        if article is None:
            return Response(
                {"code": "RESOURCE_NOT_FOUND", "message": "기사를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        _scrap, created = services.add_scrap(request.user, article)
        data = NewsArticleSerializer(article, context={"scrapped_ids": {article.id}}).data
        return Response(
            data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class NewsScrapDetailView(APIView):
    """F505 스크랩 삭제(기사 id 기준). 인증 필요."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, article_id):
        deleted = services.remove_scrap(request.user, article_id)
        if not deleted:
            return Response(
                {"code": "RESOURCE_NOT_FOUND", "message": "스크랩을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
