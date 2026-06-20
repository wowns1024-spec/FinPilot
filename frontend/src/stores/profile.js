import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

// F200 투자성향 (명세 §5.2). 사용자당 활성 프로필 1건, 선호 직접 입력.
export const useProfileStore = defineStore('profile', () => {
  const options = ref(null) // 설문 선택지 {available_asset, risk_type, investment_period, investment_goal, sectors}
  const profile = ref(null) // 현재 활성 프로필 or null

  // F201 설문 선택지 조회
  async function fetchOptions() {
    const { data } = await api.get('/investment-profile/options/')
    options.value = data
    return data
  }

  // F208 내 투자성향 조회 (미등록이면 404 → null)
  async function fetchProfile() {
    try {
      const { data } = await api.get('/investment-profile/')
      profile.value = data
      return data
    } catch (e) {
      if (e.response?.status === 404) {
        profile.value = null
        return null
      }
      throw e
    }
  }

  // F207 저장 (upsert: 신규 등록·수정 공통)
  async function saveProfile(payload) {
    const { data } = await api.post('/investment-profile/', payload)
    profile.value = data
    return data
  }

  // F210 삭제 (soft 비활성화)
  async function deleteProfile() {
    await api.delete('/investment-profile/')
    profile.value = null
  }

  return { options, profile, fetchOptions, fetchProfile, saveProfile, deleteProfile }
})
