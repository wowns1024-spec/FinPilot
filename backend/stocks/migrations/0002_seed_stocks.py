from django.db import migrations

# (code, name, market, sector_code) — MVP 유니버스. 섹터코드는 profiles.Sector 와 일치.
# 주의: 종목코드/섹터 매핑은 검증 후 admin·시드로 가감 가능. (이름·발행주식수는 sync 시 토스값으로 보정)
STOCKS = [
    # 반도체
    ("005930", "삼성전자", "KOSPI", "SEMICONDUCTOR"),
    ("000660", "SK하이닉스", "KOSPI", "SEMICONDUCTOR"),
    ("042700", "한미반도체", "KOSDAQ", "SEMICONDUCTOR"),
    ("000990", "DB하이텍", "KOSPI", "SEMICONDUCTOR"),
    ("058470", "리노공업", "KOSDAQ", "SEMICONDUCTOR"),
    # 2차전지
    ("373220", "LG에너지솔루션", "KOSPI", "SECONDARY_BATTERY"),
    ("006400", "삼성SDI", "KOSPI", "SECONDARY_BATTERY"),
    ("247540", "에코프로비엠", "KOSDAQ", "SECONDARY_BATTERY"),
    ("086520", "에코프로", "KOSDAQ", "SECONDARY_BATTERY"),
    ("003670", "포스코퓨처엠", "KOSPI", "SECONDARY_BATTERY"),
    # 방산
    ("012450", "한화에어로스페이스", "KOSPI", "DEFENSE"),
    ("047810", "한국항공우주", "KOSPI", "DEFENSE"),
    ("079550", "LIG넥스원", "KOSPI", "DEFENSE"),
    ("064350", "현대로템", "KOSPI", "DEFENSE"),
    # AI
    ("018260", "삼성에스디에스", "KOSPI", "AI"),
    ("012510", "더존비즈온", "KOSDAQ", "AI"),
    # 에너지
    ("015760", "한국전력", "KOSPI", "ENERGY"),
    ("096770", "SK이노베이션", "KOSPI", "ENERGY"),
    ("010950", "S-Oil", "KOSPI", "ENERGY"),
    # 게임
    ("036570", "엔씨소프트", "KOSPI", "GAME"),
    ("251270", "넷마블", "KOSPI", "GAME"),
    ("263750", "펄어비스", "KOSDAQ", "GAME"),
    ("259960", "크래프톤", "KOSPI", "GAME"),
    # 바이오
    ("207940", "삼성바이오로직스", "KOSPI", "BIO"),
    ("068270", "셀트리온", "KOSPI", "BIO"),
    ("196170", "알테오젠", "KOSDAQ", "BIO"),
    ("326030", "SK바이오팜", "KOSPI", "BIO"),
    # 자동차
    ("005380", "현대차", "KOSPI", "AUTOMOBILE"),
    ("000270", "기아", "KOSPI", "AUTOMOBILE"),
    ("012330", "현대모비스", "KOSPI", "AUTOMOBILE"),
    ("161390", "한국타이어앤테크놀로지", "KOSPI", "AUTOMOBILE"),
    # 금융
    ("105560", "KB금융", "KOSPI", "FINANCE"),
    ("055550", "신한지주", "KOSPI", "FINANCE"),
    ("086790", "하나금융지주", "KOSPI", "FINANCE"),
    ("316140", "우리금융지주", "KOSPI", "FINANCE"),
    # 인터넷·플랫폼
    ("035420", "NAVER", "KOSPI", "INTERNET_PLATFORM"),
    ("035720", "카카오", "KOSPI", "INTERNET_PLATFORM"),
]


def seed(apps, schema_editor):
    Stock = apps.get_model("stocks", "Stock")
    Sector = apps.get_model("profiles", "Sector")
    sectors = {s.code: s for s in Sector.objects.all()}
    for code, name, market, sector_code in STOCKS:
        Stock.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "market": market,
                "sector": sectors.get(sector_code),
                "is_active": True,
            },
        )


def unseed(apps, schema_editor):
    Stock = apps.get_model("stocks", "Stock")
    Stock.objects.filter(code__in=[c for c, _, _, _ in STOCKS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stocks", "0001_initial"),
        ("profiles", "0002_seed_sectors"),  # 섹터가 먼저 시드돼야 FK 연결 가능
    ]
    operations = [migrations.RunPython(seed, unseed)]
