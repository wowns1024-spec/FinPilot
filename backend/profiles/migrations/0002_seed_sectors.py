from django.db import migrations

# (order, code, name) — 관심 산업 초기 목록 (F206). 운영 중 admin 에서 가감 가능.
SECTORS = [
    (1, "SEMICONDUCTOR", "반도체"),
    (2, "SECONDARY_BATTERY", "2차전지"),
    (3, "DEFENSE", "방산"),
    (4, "AI", "AI"),
    (5, "ENERGY", "에너지"),
    (6, "GAME", "게임"),
    (7, "BIO", "바이오"),
    (8, "AUTOMOBILE", "자동차"),
    (9, "FINANCE", "금융"),
    (10, "INTERNET_PLATFORM", "인터넷·플랫폼"),
]


def seed(apps, schema_editor):
    Sector = apps.get_model("profiles", "Sector")
    for order, code, name in SECTORS:
        Sector.objects.update_or_create(
            code=code, defaults={"name": name, "order": order, "is_active": True}
        )


def unseed(apps, schema_editor):
    Sector = apps.get_model("profiles", "Sector")
    Sector.objects.filter(code__in=[c for _, c, _ in SECTORS]).delete()


class Migration(migrations.Migration):
    dependencies = [("profiles", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
