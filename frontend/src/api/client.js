import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'

export const ACCESS_KEY = 'finpick_access'
export const REFRESH_KEY = 'finpick_refresh'

const api = axios.create({ baseURL: BASE_URL })

// 요청마다 Access Token 자동 첨부 (NF101)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 인증 만료 시 강제 로그아웃 처리를 외부(스토어/라우터)에서 주입
let onAuthExpired = () => {}
export function setAuthExpiredHandler(fn) {
  onAuthExpired = fn
}

// 401 발생 시 Refresh Token 으로 1회 재발급 후 재시도 (F106)
let refreshing = null

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const { response, config } = error
    const refresh = localStorage.getItem(REFRESH_KEY)
    const isRefreshCall = config?.url?.includes('/accounts/token/refresh/')

    if (response?.status === 401 && refresh && !config._retried && !isRefreshCall) {
      config._retried = true
      try {
        if (!refreshing) {
          refreshing = axios
            .post(`${BASE_URL}/accounts/token/refresh/`, { refresh })
            .finally(() => {
              refreshing = null
            })
        }
        const { data } = await refreshing
        localStorage.setItem(ACCESS_KEY, data.access)
        if (data.refresh) localStorage.setItem(REFRESH_KEY, data.refresh)
        config.headers.Authorization = `Bearer ${data.access}`
        return api(config)
      } catch (e) {
        onAuthExpired()
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  },
)

export default api
