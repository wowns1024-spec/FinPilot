from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import InvestmentProfile

User = get_user_model()

BASE = "/api/v1/investment-profile/"


def _payload(**override):
    data = {
        "available_asset": 3,
        "risk_type": "BALANCED",
        "investment_period": "SWING",
        "investment_goal": "GROWTH",
        "sectors": ["SEMICONDUCTOR", "AI"],
    }
    data.update(override)
    return data


class OptionsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="t", password="pw-123!finpick")
        self.client.force_authenticate(self.user)

    def test_options_returns_enums_and_sectors(self):
        res = self.client.get(BASE + "options/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["risk_type"]), 5)
        self.assertEqual(len(res.data["available_asset"]), 5)
        self.assertTrue(any(s["code"] == "SEMICONDUCTOR" for s in res.data["sectors"]))
        # 명세 기준 5단계: 균형형 (위험중립형 아님)
        labels = [o["label"] for o in res.data["risk_type"]]
        self.assertIn("균형형", labels)
        self.assertNotIn("위험중립형", labels)


class ProfileCrudTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="t", password="pw-123!finpick")
        self.client.force_authenticate(self.user)

    def test_get_before_create_404(self):
        res = self.client.get(BASE)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data["code"], "RESOURCE_NOT_FOUND")

    def test_create_then_single_profile_upsert(self):
        res = self.client.post(BASE, _payload(), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["risk_type_display"], "균형형")
        self.assertEqual(res.data["available_asset_display"], "5천만~1억 원")
        self.assertEqual(
            {s["code"] for s in res.data["sectors_detail"]}, {"SEMICONDUCTOR", "AI"}
        )
        # 재저장 = upsert → 200, 사용자당 1건 유지
        res2 = self.client.post(BASE, _payload(risk_type="AGGRESSIVE"), format="json")
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.data["risk_type"], "AGGRESSIVE")
        self.assertEqual(InvestmentProfile.objects.filter(user=self.user).count(), 1)

    def test_sectors_min_one_required(self):
        res = self.client.post(BASE, _payload(sectors=[]), format="json")
        self.assertEqual(res.status_code, 400)

    def test_unsupported_sector_dropped_known_kept(self):
        res = self.client.post(
            BASE, _payload(sectors=["SEMICONDUCTOR", "NOPE"]), format="json"
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(
            {s["code"] for s in res.data["sectors_detail"]}, {"SEMICONDUCTOR"}
        )

    def test_all_unsupported_sectors_400(self):
        res = self.client.post(BASE, _payload(sectors=["NOPE", "NADA"]), format="json")
        self.assertEqual(res.status_code, 400)

    def test_invalid_risk_type_400(self):
        res = self.client.post(BASE, _payload(risk_type="WAT"), format="json")
        self.assertEqual(res.status_code, 400)

    def test_invalid_asset_band_400(self):
        res = self.client.post(BASE, _payload(available_asset=9), format="json")
        self.assertEqual(res.status_code, 400)

    def test_patch_updates_field_keeps_rest(self):
        self.client.post(BASE, _payload(), format="json")
        res = self.client.patch(BASE, {"investment_goal": "DIVIDEND"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["investment_goal"], "DIVIDEND")
        self.assertEqual(res.data["risk_type"], "BALANCED")  # 유지

    def test_patch_without_profile_404(self):
        res = self.client.patch(BASE, {"investment_goal": "DIVIDEND"}, format="json")
        self.assertEqual(res.status_code, 404)

    def test_soft_delete_hides_profile(self):
        self.client.post(BASE, _payload(), format="json")
        res = self.client.delete(BASE)
        self.assertEqual(res.status_code, 200)
        # 행은 남고 비활성
        self.assertEqual(InvestmentProfile.objects.filter(user=self.user).count(), 1)
        self.assertFalse(InvestmentProfile.objects.get(user=self.user).is_active)
        # 조회 404, 등록상태 False
        self.assertEqual(self.client.get(BASE).status_code, 404)
        self.assertFalse(User.objects.get(pk=self.user.pk).has_investment_profile)

    def test_repost_after_delete_reactivates(self):
        self.client.post(BASE, _payload(), format="json")
        self.client.delete(BASE)
        res = self.client.post(BASE, _payload(risk_type="STABLE"), format="json")
        self.assertIn(res.status_code, (200, 201))
        self.assertEqual(self.client.get(BASE).status_code, 200)
        self.assertTrue(User.objects.get(pk=self.user.pk).has_investment_profile)

    def test_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(BASE + "options/").status_code, 401)
