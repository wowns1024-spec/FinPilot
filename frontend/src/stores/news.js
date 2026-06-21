import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

// F500 뉴스. 목록/검색/종목별/주요는 공개(AllowAny), 스크랩은 로그인 필요.
export const useNewsStore = defineStore('news', () => {
  const scraps = ref([]) // 마이페이지 스크랩 목록

  // F501 목록 / F502 검색 / F503 종목별 / F504 주요 (params: q, stock, sector, limit)
  async function fetchNews(params = {}) {
    const { data } = await api.get('/news/', { params })
    return data.results // [{ id, title, summary, source, url, published_at, stock_code, is_scrapped }]
  }

  // F505 스크랩 목록
  async function fetchScraps() {
    const { data } = await api.get('/news/scraps/')
    scraps.value = data.results
    return scraps.value
  }

  // F505 스크랩 추가 (멱등)
  async function addScrap(articleId) {
    const { data } = await api.post('/news/scraps/', { article_id: articleId })
    return data
  }

  // F505 스크랩 삭제 (기사 id 기준)
  async function removeScrap(articleId) {
    await api.delete(`/news/scraps/${articleId}/`)
    scraps.value = scraps.value.filter((a) => a.id !== articleId)
  }

  return { scraps, fetchNews, fetchScraps, addScrap, removeScrap }
})
