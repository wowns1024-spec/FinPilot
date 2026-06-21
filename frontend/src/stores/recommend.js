import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

// F300 맞춤 종목 추천. 점수·이유는 백엔드 규칙엔진(+GMS)이 산출, 프론트는 우리 API만 호출.
export const useRecommendStore = defineStore('recommend', () => {
  const recommendation = ref(null) // { id, reason_source, risk_type_display, created_at, items[] } or null

  // 활성 추천 조회 (없으면 404 → null)
  async function fetchRecommendation() {
    try {
      const { data } = await api.get('/recommendations/')
      recommendation.value = data
      return data
    } catch (e) {
      if (e.response?.status === 404) {
        recommendation.value = null
        return null
      }
      throw e
    }
  }

  // 추천 생성/재생성 (POST). 투자성향 미등록이면 400 PROFILE_REQUIRED → 호출측에서 처리
  async function generateRecommendation() {
    const { data } = await api.post('/recommendations/')
    recommendation.value = data
    return data
  }

  return { recommendation, fetchRecommendation, generateRecommendation }
})
