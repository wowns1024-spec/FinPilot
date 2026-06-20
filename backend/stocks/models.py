from django.db import models


class Stock(models.Model):
    """종목 마스터 (F400 유니버스).

    토스 Open API 에는 '종목 목록/검색' 엔드포인트가 없어(심볼을 알아야 조회 가능),
    목록·검색·추천 후보군의 기준이 되는 종목 집합을 우리가 직접 보유한다.
    """

    class Market(models.TextChoices):
        KOSPI = "KOSPI", "KOSPI"
        KOSDAQ = "KOSDAQ", "KOSDAQ"

    code = models.CharField(max_length=20, unique=True)  # 예: "005930"
    name = models.CharField(max_length=100)
    market = models.CharField(max_length=10, choices=Market.choices)
    # 사용자 관심산업(F200)과 같은 분류 체계를 공유한다(F300 관심산업 매치율).
    sector = models.ForeignKey(
        "profiles.Sector",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stocks",
    )
    shares_outstanding = models.BigIntegerField(null=True, blank=True)  # 시총 계산용, 토스에서 채움
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.name}({self.code})"


class Quote(models.Model):
    """종목 시세 캐시 (F404~F406).

    마지막 정상값을 저장해 외부 API 장애 시 폴백(지연표시)으로 쓴다.
    """

    stock = models.OneToOneField(Stock, on_delete=models.CASCADE, related_name="quote")
    last_price = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    prev_close = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    volume = models.DecimalField(max_digits=24, decimal_places=4, null=True, blank=True)
    as_of = models.DateTimeField(null=True, blank=True)  # 토스 시세 기준시각
    daily_as_of = models.DateField(null=True, blank=True)  # prev_close/volume 갱신 일자
    updated_at = models.DateTimeField(auto_now=True)  # 우리 갱신 시각(TTL 판단)

    def __str__(self):
        return f"{self.stock.code} @ {self.last_price}"

    @property
    def change_rate(self):
        """전일종가 대비 등락률(소수). 데이터 없으면 None."""
        if self.last_price is None or not self.prev_close:
            return None
        return (self.last_price - self.prev_close) / self.prev_close
