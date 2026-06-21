"""SSAFY GMS API 클라이언트(F300 추천 이유 생성). 미설정/실패 시 호출측에서 템플릿 폴백.

GMS 프록시를 통해 OpenAI Responses API를 호출한다. 실제 호출 URL은
``{GMS_API_BASE}/api.openai.com/v1/responses`` 이며, 기존 OpenAI API와 같은
Authorization 헤더와 body를 사용한다.
"""

import requests
from django.conf import settings

_provider = None


class GmsError(Exception):
    """GMS 호출 실패."""


class GmsClient:
    def __init__(self):
        self.base = (getattr(settings, "GMS_API_BASE", "") or "").rstrip("/")
        self.key = getattr(settings, "GMS_API_KEY", "") or ""
        self.model = getattr(settings, "GMS_MODEL", "") or "gpt-4.1"

    def available(self):
        return bool(self.base and self.key)

    def _responses_url(self):
        if self.base.endswith("/v1/responses"):
            return self.base
        return f"{self.base}/api.openai.com/v1/responses"

    def _extract_text(self, data):
        text = data.get("output_text")
        if isinstance(text, str):
            return text.strip()

        for item in data.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

        raise GmsError("bad response: output text not found")

    def generate(self, prompt):
        if not self.available():
            raise GmsError("gms not configured")
        try:
            resp = requests.post(
                self._responses_url(),
                headers={
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": prompt,
                    "temperature": 0.7,
                    "max_output_tokens": 200,
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            raise GmsError(f"request failed: {exc}") from exc
        if resp.status_code != 200:
            raise GmsError(f"gms -> {resp.status_code}")
        try:
            return self._extract_text(resp.json())
        except (AttributeError, ValueError) as exc:
            raise GmsError(f"bad response: {exc}") from exc


def provider():
    global _provider
    if _provider is None:
        _provider = GmsClient()
    return _provider


def set_provider(p):
    """테스트/대체 구현 주입용 (None 이면 다음 호출에서 실제 클라이언트 재생성)."""
    global _provider
    _provider = p
