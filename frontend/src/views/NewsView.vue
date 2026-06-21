<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const query = ref('')
const sector = ref('')
const sort = ref('date')
const news = ref([])
const categories = ref([])
const scraps = ref([])
const selected = ref(null)
const loading = ref(false)
const scrapLoading = ref(false)
const errorMessage = ref('')
const source = ref('')

const isAuthenticated = computed(() => auth.isAuthenticated)

onMounted(async () => {
  await fetchNews()
  if (isAuthenticated.value) await fetchScraps()
})

async function fetchNews() {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await api.get('/news/', {
      params: {
        q: query.value,
        sector: sector.value,
        sort: sort.value,
        display: 20,
      },
    })
    news.value = data.items || []
    categories.value = data.categories || []
    source.value = data.source || ''
    selected.value = news.value[0] || null
  } catch (error) {
    news.value = []
    selected.value = null
    errorMessage.value =
      error.response?.data?.detail || '뉴스를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

async function fetchScraps() {
  try {
    const { data } = await api.get('/news/scraps/')
    scraps.value = data.items || []
    const links = new Set(scraps.value.map((item) => item.link))
    news.value = news.value.map((item) => ({ ...item, scrapped: links.has(item.link) }))
    if (selected.value) selected.value.scrapped = links.has(selected.value.link)
  } catch {
    scraps.value = []
  }
}

async function onSearch() {
  await fetchNews()
  if (isAuthenticated.value) await fetchScraps()
}

async function selectSector(key) {
  sector.value = sector.value === key ? '' : key
  await onSearch()
}

function selectNews(item) {
  selected.value = item
}

async function toggleScrap(item) {
  if (!isAuthenticated.value) {
    errorMessage.value = '로그인 후 뉴스 스크랩을 사용할 수 있습니다.'
    return
  }
  scrapLoading.value = true
  try {
    const existing = scraps.value.find((scrap) => scrap.link === item.link)
    if (existing) {
      await api.delete(`/news/scraps/${existing.id}/`)
    } else {
      await api.post('/news/scraps/', {
        title: item.title,
        summary: item.summary,
        publisher: item.publisher,
        published_at: item.published_at,
        link: item.link,
        originallink: item.originallink || item.link,
        sector: item.sector,
      })
    }
    await fetchScraps()
  } finally {
    scrapLoading.value = false
  }
}

function isScrapped(item) {
  return scraps.value.some((scrap) => scrap.link === item?.link) || !!item?.scrapped
}

function openOriginal(item) {
  const url = item?.originallink || item?.link
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="news-page">
    <div class="container">
      <div class="page-head">
        <div>
          <p class="eyebrow">F500 뉴스 서비스</p>
          <h1>뉴스</h1>
          <p class="muted">경제, 종목, 섹터 관련 뉴스를 검색하고 관심 뉴스를 스크랩합니다.</p>
        </div>
        <span class="source-pill" :class="{ live: source === 'naver' }">
          {{ source === 'naver' ? '네이버 API 연동' : '네이버 API 확인 필요' }}
        </span>
      </div>

      <form class="search-bar" @submit.prevent="onSearch">
        <input
          v-model="query"
          class="input"
          type="search"
          placeholder="키워드, 종목명, 섹터를 입력하세요"
        />
        <select v-model="sort" class="input select">
          <option value="date">최신순</option>
          <option value="sim">관련도순</option>
        </select>
        <button class="btn btn-primary" type="submit">검색</button>
      </form>

      <div class="sector-tabs">
        <button
          type="button"
          class="sector-chip"
          :class="{ active: !sector }"
          @click="selectSector('')"
        >
          전체
        </button>
        <button
          v-for="item in categories"
          :key="item.key"
          type="button"
          class="sector-chip"
          :class="{ active: sector === item.key }"
          @click="selectSector(item.key)"
        >
          {{ item.label }}
        </button>
      </div>

      <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

      <div class="news-layout">
        <section class="list-panel">
          <p v-if="loading" class="muted empty">뉴스를 불러오는 중...</p>
          <p v-else-if="!news.length" class="muted empty">뉴스 검색 결과가 없습니다.</p>

          <button
            v-for="item in news"
            v-else
            :key="item.id"
            type="button"
            class="news-row"
            :class="{ active: selected?.id === item.id }"
            @click="selectNews(item)"
          >
            <span class="row-top">
              <strong>{{ item.title }}</strong>
              <span class="sector-label">{{ item.sector }}</span>
            </span>
            <span class="summary">{{ item.summary }}</span>
            <span class="meta">
              {{ item.publisher || '언론사' }} · {{ formatDate(item.published_at) }}
            </span>
          </button>
        </section>

        <aside class="detail-stack">
          <section class="detail-panel">
            <template v-if="selected">
              <div class="detail-top">
                <span class="sector-label">{{ selected.sector }}</span>
                <span class="muted">{{ formatDate(selected.published_at) }}</span>
              </div>
              <h2>{{ selected.title }}</h2>
              <p class="muted publisher">{{ selected.publisher || '언론사 정보 없음' }}</p>
              <p class="summary-detail">{{ selected.summary }}</p>

              <div class="detail-actions">
                <button class="btn btn-primary" type="button" @click="openOriginal(selected)">
                  원문 보기
                </button>
                <button
                  class="btn btn-ghost"
                  type="button"
                  :disabled="scrapLoading"
                  @click="toggleScrap(selected)"
                >
                  {{ isScrapped(selected) ? '스크랩 해제' : '스크랩' }}
                </button>
              </div>
            </template>
            <p v-else class="muted">뉴스를 선택해 주세요.</p>
          </section>

          <section class="scrap-panel">
            <div class="panel-head">
              <h3>내 스크랩</h3>
              <button
                v-if="isAuthenticated"
                type="button"
                class="text-button"
                @click="fetchScraps"
              >
                새로고침
              </button>
            </div>
            <p v-if="!isAuthenticated" class="muted empty-small">
              로그인하면 관심 뉴스를 저장할 수 있습니다.
            </p>
            <p v-else-if="!scraps.length" class="muted empty-small">스크랩한 뉴스가 없습니다.</p>
            <button
              v-for="item in scraps"
              v-else
              :key="item.id"
              type="button"
              class="scrap-row"
              @click="selected = item"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ item.sector }} · {{ formatDate(item.published_at) }}</span>
            </button>
          </section>
        </aside>
      </div>
    </div>
  </div>
</template>

<style scoped>
.news-page {
  padding: 40px 0 64px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  margin-bottom: 22px;
}
.eyebrow {
  color: var(--gold);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}
.page-head h1 {
  font-size: 28px;
}
.page-head .muted {
  margin: 8px 0 0;
}
.source-pill,
.sector-chip,
.sector-label {
  border: 1px solid var(--border);
  border-radius: 999px;
  font-weight: 700;
}
.source-pill {
  color: var(--text-muted);
  padding: 7px 11px;
  font-size: 12.5px;
}
.source-pill.live {
  color: var(--gold);
  border-color: rgba(231, 178, 60, 0.5);
}
.search-bar {
  display: grid;
  grid-template-columns: 1fr 140px auto;
  gap: 10px;
  margin-bottom: 14px;
}
.select {
  appearance: none;
}
.sector-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.sector-chip {
  background: transparent;
  color: var(--text-muted);
  padding: 8px 12px;
}
.sector-chip.active,
.sector-chip:hover {
  color: var(--gold);
  border-color: rgba(231, 178, 60, 0.55);
  background: rgba(231, 178, 60, 0.08);
}
.news-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
  align-items: start;
}
.list-panel,
.detail-panel,
.scrap-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.list-panel {
  overflow: hidden;
}
.news-row {
  width: 100%;
  display: grid;
  gap: 8px;
  background: transparent;
  color: var(--text);
  border: none;
  border-bottom: 1px solid var(--border);
  padding: 17px 18px;
  text-align: left;
}
.news-row:last-child {
  border-bottom: none;
}
.news-row:hover,
.news-row.active {
  background: var(--surface-2);
}
.row-top,
.detail-top,
.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}
.row-top strong {
  line-height: 1.35;
}
.sector-label {
  color: var(--gold);
  border-color: rgba(231, 178, 60, 0.42);
  padding: 4px 8px;
  font-size: 12px;
  white-space: nowrap;
}
.summary {
  color: var(--text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.meta {
  color: var(--text-dim);
  font-size: 13px;
}
.detail-stack {
  display: grid;
  gap: 16px;
}
.detail-panel,
.scrap-panel {
  padding: 22px;
}
.detail-panel h2 {
  margin-top: 16px;
  font-size: 22px;
  line-height: 1.35;
}
.publisher {
  margin: 8px 0 0;
}
.summary-detail {
  color: var(--text-muted);
  margin: 20px 0;
}
.detail-actions {
  display: flex;
  gap: 8px;
}
.panel-head h3 {
  font-size: 16px;
}
.text-button {
  background: transparent;
  border: none;
  color: var(--gold);
  font-weight: 700;
}
.scrap-row {
  width: 100%;
  display: grid;
  gap: 4px;
  text-align: left;
  color: var(--text);
  background: transparent;
  border: none;
  border-top: 1px solid var(--border);
  padding: 12px 0;
}
.scrap-row strong {
  font-size: 14px;
}
.scrap-row span,
.empty-small {
  color: var(--text-muted);
  font-size: 13px;
}
.empty {
  padding: 28px 18px;
}
.empty-small {
  margin: 14px 0 0;
}
@media (max-width: 900px) {
  .page-head {
    flex-direction: column;
  }
  .search-bar,
  .news-layout {
    grid-template-columns: 1fr;
  }
}
</style>
