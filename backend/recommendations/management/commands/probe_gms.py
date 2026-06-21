"""SSAFY GMS API 연결 확인용 명령.

    python manage.py probe_gms --prompt "테스트 문장을 한 줄로 답해줘"
"""

from django.core.management.base import BaseCommand, CommandError

from recommendations import gms


class Command(BaseCommand):
    help = "backend/.env 의 GMS 설정으로 SSAFY GMS API 호출을 확인한다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--prompt",
            default="한국어로 한 문장만 답해주세요. GMS 연결 테스트입니다.",
            help="GMS에 보낼 테스트 프롬프트",
        )

    def handle(self, *args, **options):
        client = gms.GmsClient()
        if not client.available():
            raise CommandError("GMS_API_KEY 를 backend/.env 에 설정하세요.")

        try:
            text = client.generate(options["prompt"])
        except gms.GmsError as exc:
            raise CommandError(f"GMS 호출 실패: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("GMS 호출 성공"))
        self.stdout.write(text)
