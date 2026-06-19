import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { ACCESS_KEY, REFRESH_KEY } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const access = ref(localStorage.getItem(ACCESS_KEY) || '')
  const refresh = ref(localStorage.getItem(REFRESH_KEY) || '')
  const user = ref(null)

  const isAuthenticated = computed(() => !!access.value)

  function setTokens(a, r) {
    access.value = a || ''
    refresh.value = r || ''
    if (a) localStorage.setItem(ACCESS_KEY, a)
    else localStorage.removeItem(ACCESS_KEY)
    if (r) localStorage.setItem(REFRESH_KEY, r)
    else localStorage.removeItem(REFRESH_KEY)
  }

  function clear() {
    setTokens('', '')
    user.value = null
  }

  // F102 아이디 중복 확인
  async function checkUsername(username) {
    const { data } = await api.get('/accounts/check-username/', {
      params: { username },
    })
    return data // { username, available, message }
  }

  // F103 회원가입
  async function signup(payload) {
    const { data } = await api.post('/accounts/signup/', payload)
    setTokens(data.access, data.refresh)
    user.value = data.user
    return data
  }

  // F105 로그인
  async function login(credentials) {
    const { data } = await api.post('/accounts/login/', credentials)
    setTokens(data.access, data.refresh)
    user.value = data.user
    return data
  }

  // F107 로그아웃
  async function logout() {
    try {
      if (refresh.value) {
        await api.post('/accounts/logout/', { refresh: refresh.value })
      }
    } catch {
      // 서버 실패와 무관하게 로컬 토큰은 제거 (F107)
    } finally {
      clear()
    }
  }

  // F108 회원정보 조회
  async function fetchMe() {
    const { data } = await api.get('/accounts/me/')
    user.value = data
    return data
  }

  // F109 회원정보 수정
  async function updateMe(payload) {
    const { data } = await api.patch('/accounts/me/', payload)
    user.value = data
    return data
  }

  return {
    access,
    refresh,
    user,
    isAuthenticated,
    setTokens,
    clear,
    checkUsername,
    signup,
    login,
    logout,
    fetchMe,
    updateMe,
  }
})
