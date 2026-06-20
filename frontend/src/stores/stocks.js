import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

// F400 종목 조회. 토스 시세는 백엔드가 캐시·폴백 처리하므로 프론트는 우리 API만 호출.
export const useStocksStore = defineStore('stocks', () => {
  const sectors = ref([])

  // F401 목록 / F402 검색 (params: page, page_size, search, market, sector, ordering)
  async function fetchStocks(params = {}) {
    const { data } = await api.get('/stocks/', { params })
    return data // { count, next, previous, results }
  }

  // F403~F407 상세
  async function fetchStock(code) {
    const { data } = await api.get(`/stocks/${code}/`)
    return data
  }

  // 목록 필터용 섹터 목록
  async function fetchSectors() {
    const { data } = await api.get('/stocks/sectors/')
    sectors.value = data.sectors
    return sectors.value
  }

  return { sectors, fetchStocks, fetchStock, fetchSectors }
})
