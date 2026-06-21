from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import NewsScrap
from .serializers import NewsScrapSerializer
from .services import NaverNewsAPIError, categories, naver_news_search


class NewsListView(APIView):
    """F501/F503/F504 뉴스 목록, 검색, 카테고리 필터."""

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "")
        sector = request.query_params.get("sector", "")
        sort = request.query_params.get("sort", "date")
        display = request.query_params.get("display", 20)
        start = request.query_params.get("start", 1)

        try:
            result = naver_news_search(
                query=query,
                sector=sector,
                sort=sort,
                display=display,
                start=start,
            )
        except NaverNewsAPIError as exc:
            return Response(
                {
                    "detail": exc.message,
                    "source": "naver",
                    "items": [],
                    "categories": categories(),
                },
                status=exc.status_code,
            )

        scrapped_links = set()
        if request.user.is_authenticated:
            scrapped_links = set(
                NewsScrap.objects.filter(user=request.user).values_list("link", flat=True)
            )
        for item in result["items"]:
            item["scrapped"] = item["link"] in scrapped_links

        result["categories"] = categories()
        return Response(result)


class NewsDetailView(APIView):
    """F502 뉴스 상세 조회. 외부 뉴스는 원문 URL 중심으로 제공한다."""

    permission_classes = [AllowAny]

    def get(self, request):
        url = request.query_params.get("url", "")
        title = request.query_params.get("title", "")
        summary = request.query_params.get("summary", "")
        if not url:
            return Response(
                {"detail": "뉴스 URL이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scrapped = False
        if request.user.is_authenticated:
            scrapped = NewsScrap.objects.filter(user=request.user, link=url).exists()

        return Response(
            {
                "title": title,
                "summary": summary,
                "link": url,
                "originallink": request.query_params.get("originallink", url),
                "publisher": request.query_params.get("publisher", ""),
                "published_at": request.query_params.get("published_at"),
                "sector": request.query_params.get("sector", "경제"),
                "scrapped": scrapped,
            }
        )


class NewsCategoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"categories": categories()})


class NewsScrapListCreateView(APIView):
    """F505/F506 뉴스 스크랩 등록 및 조회."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        scraps = NewsScrap.objects.filter(user=request.user)
        return Response({"items": NewsScrapSerializer(scraps, many=True).data})

    def post(self, request):
        serializer = NewsScrapSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        scrap = serializer.save()
        return Response(
            NewsScrapSerializer(scrap).data,
            status=status.HTTP_201_CREATED,
        )


class NewsScrapDeleteView(APIView):
    """F507 뉴스 스크랩 삭제."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = NewsScrap.objects.filter(user=request.user, pk=pk).delete()
        if not deleted:
            return Response(
                {"detail": "스크랩 뉴스를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
