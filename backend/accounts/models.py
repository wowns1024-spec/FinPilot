from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """서비스 사용자 모델 (F100).

    명세서 §8 기준 핵심 필드(username, email, password, date_joined)는
    AbstractUser 가 제공한다. 가입 시 생년월일을 추가로 수집하고,
    이메일은 중복을 허용하지 않는다. 투자성향 등록 여부는 investments 앱의
    InvestmentProfile(F200) 관계로 판단한다.
    """

    email = models.EmailField("email address", unique=True)
    birth_date = models.DateField("생년월일", null=True, blank=True)

    @property
    def has_investment_profile(self) -> bool:
        """투자성향(F200) 등록 여부."""
        return hasattr(self, "investment_profile")
