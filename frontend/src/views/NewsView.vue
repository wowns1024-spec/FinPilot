<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useNewsStore } from '@/stores/news'
import { useStocksStore } from '@/stores/stocks'
import { useAuthStore } from '@/stores/auth'
import { timeAgo } from '@/utils/datetime'

const router = useRouter()
const newsStore = useNewsStore()
const stocksStore = useStocksStore()
const auth = useAuthStore()
const { isAuthenticated } = storeToRefs(auth)

const items = ref([])
const sectors = ref([])
const loading = ref(false)
const error = ''
const errorMsg = ref('')
const search = ref('')
const activeSector = ref('') // '' = 주요 뉴스
const pending = ref(null) // 스크랩 토글 진행 중 기사 id

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = {}
    if (search.value.trim()) params.q = search.value.trim()
    else if (activeSector.value) params.sector = activeSector.value
    items.value = await newsStore.fetchNews(params)
  } catch {
    errorMsg.value = '뉴스를 불러오지 못했습니다.'
    items.value = []
  } finally {
    loading.value = false
  }
}

function selectSector(code) {
  if (activeSector.value === code) return
  activeSector.value = code
  search.value = ''
  load()
}

function onSearch() {
  activeSector.value = ''
  load()
}

async function toggleScrap(item) {
  if (!isAuthenticated.value) {
    router.push({ name: 'login', query: { redirect: '/news' } })
    return
  }
  if (pending.value === item.id) return
  pending.value = item.id
  try {
    if (item.is_scrapped) {
      await newsStore.removeScrap(item.id)
      item.is_scrapped = false
    } else {
      await newsStore.addScrap(item.id)
      item.is_scrapped = true
    }
  } catch {
    /* 무시: 상태 유지 */
  } finally {
    pending.value = null
  }
}

onMounted(async () => {
  try {
    sectors.value = await stocksStore.fetchSectors()
  } catch {
    sectors.value = []
  }
  await load()
})
</script>

<template>
  <div class="container news-page">
    <div class="page-head">
      <p class="eyebrow">F500 뉴스</p>
      <h1>금융 뉴스</h1>
      <p class="muted sub">시장과 종목 관련 최신 뉴스를 한눈에 확인하고 스크랩하세요.</p>
    </div>

    <form class="search-bar" @submit.prevent="onSearch">
      <input
        v-model="search"
        class="input"
        type="text"
        placeholder="키워드로 뉴스 검색 (예: 반도체, 금리)"
      />
      <button type="submit" class="btn btn-primary">검색</button>
    </form>

    <div class="chips">
      <button
        type="button"
        class="chip"
        :class="{ active: activeSector === '' && !search.trim() }"
        @click="selectSector('')"
      >
        주요 뉴스
      </button>
      <button
        v-for="s in sectors"
        :key="s.code"
        type="button"
        class="chip"
        :class="{ active: activeSector === s.code }"
        @click="selectSector(s.code)"
      >
        {{ s.name }}
      </button>
    </div>

    <p v-if="loading" class="muted state">불러오는 중...</p>
    <p v-else-if="errorMsg" class="form-error state">{{ errorMsg }}</p>
    <p v-else-if="!items.length" class="muted state">표시할 뉴스가 없습니다.</p>

    <ul v-else class="news-list">
      <li v-for="item in items" :key="item.id" class="card news-card">
        <div class="nc-main">
          <a :href="item.url" target="_blank" rel="noopener noreferrer" class="nc-title">
            {{ item.title }}
          </a>
          <p v-if="item.summary" class="nc-summary">{{ item.summary }}</p>
          <p class="nc-meta">
            <span v-if="item.source" class="nc-source">{{ item.source }}</span>
            <span v-if="item.published_at" class="nc-time">{{ timeAgo(item.published_at) }}</span>
            <span v-if="item.stock_name" class="nc-tag">{{ item.stock_name }}</span>
          </p>
        </div>
        <button
          type="button"
          class="scrap-btn"
          :class="{ on: item.is_scrapped }"
          :disabled="pending === item.id"
          :title="item.is_scrapped ? '스크랩 취소' : '스크랩'"
          @click="toggleScrap(item)"
        >
          {{ item.is_scrapped ? '★' : '☆' }}
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.news-page {
  padding: 38px 24px 64px;
}
.page-head {
  margin-bottom: 18px;
}
.eyebrow {
  font-size: 13px;
  font-weight: 600;
  color: var(--gold);
  margin: 0 0 6px;
}
.page-head h1 {
  font-size: 30px;
}
.sub {
  margin: 10px 0 0;
  font-size: 14.5px;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.search-bar .input {
  flex: 1;
  height: 44px;
}
.search-bar .btn {
  flex-shrink: 0;
  width: 68px;
  height: 44px;
  padding: 0;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 22px;
}
.chip {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-muted);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}
.chip:hover {
  color: var(--text);
}
.chip.active {
  background: var(--gold);
  border-color: var(--gold);
  color: var(--gold-ink);
  font-weight: 700;
}

.news-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.news-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 20px;
}
.nc-main {
  flex: 1;
  min-width: 0;
}
.nc-title {
  display: inline-block;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--text);
}
.nc-title:hover {
  color: var(--gold);
}
.nc-summary {
  margin: 8px 0 0;
  font-size: 13.5px;
  color: var(--text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.nc-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin: 12px 0 0;
  font-size: 12.5px;
  color: var(--text-dim);
}
.nc-source {
  font-weight: 600;
  color: var(--text-muted);
}
.nc-tag {
  background: var(--surface-3);
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  color: var(--text-muted);
}
.scrap-btn {
  flex-shrink: 0;
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 22px;
  line-height: 1;
  padding: 2px 4px;
  transition: color 0.12s, transform 0.12s;
}
.scrap-btn:hover {
  transform: scale(1.15);
  color: var(--gold);
}
.scrap-btn.on {
  color: var(--gold);
}
.scrap-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.state {
  text-align: center;
  padding: 56px 0;
}
</style>
