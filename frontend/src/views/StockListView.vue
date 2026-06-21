<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useStocksStore } from '@/stores/stocks'
import { useNewsStore } from '@/stores/news'
import { timeAgo } from '@/utils/datetime'

const route = useRoute()
const store = useStocksStore()
const newsStore = useNewsStore()

const stockNews = ref([])
const newsLoading = ref(false)

const items = ref([])
const listLoading = ref(false)
const listError = ref('')
const search = ref('')

const selectedCode = ref(null)
const detail = ref(null)
const detailLoading = ref(false)

// 목록 가격이 전부 비어 있으면 외부 시세 미연동 상태로 본다.
const noLiveData = computed(
  () => items.value.length > 0 && items.value.every((s) => s.price == null),
)

async function loadList() {
  listLoading.value = true
  listError.value = ''
  try {
    const params = { page_size: 100, ordering: 'code' }
    if (search.value.trim()) params.search = search.value.trim()
    const data = await store.fetchStocks(params)
    items.value = data.results
  } catch {
    listError.value = '종목을 불러오지 못했습니다.'
    items.value = []
  } finally {
    listLoading.value = false
  }
}

async function loadDetail(code) {
  detailLoading.value = true
  try {
    detail.value = await store.fetchStock(code)
  } catch {
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

async function loadNews(code) {
  newsLoading.value = true
  stockNews.value = []
  try {
    stockNews.value = await newsStore.fetchNews({ stock: code, limit: 5 })
  } catch {
    stockNews.value = []
  } finally {
    newsLoading.value = false
  }
}

function selectStock(code) {
  if (code === selectedCode.value) return
  selectedCode.value = code
  loadDetail(code)
  loadNews(code)
}

async function onSearch() {
  await loadList()
  if (items.value.length && !items.value.some((s) => s.code === selectedCode.value)) {
    selectStock(items.value[0].code)
  }
}

onMounted(async () => {
  await loadList()
  const initial = route.params.code || items.value[0]?.code
  if (initial) selectStock(initial)
})

function dirClass(d) {
  return d === 'UP' ? 'up' : d === 'DOWN' ? 'down' : ''
}
function pct(rate) {
  if (rate == null) return '-'
  return (rate > 0 ? '+' : '') + (rate * 100).toFixed(2) + '%'
}
function priceText(p) {
  return p == null ? '-' : Number(p).toLocaleString('ko-KR') + '원'
}
function marketCapText(v) {
  if (v == null) return '-'
  if (v >= 1e12) return (v / 1e12).toFixed(1) + '조원'
  if (v >= 1e8) return Math.round(v / 1e8).toLocaleString('ko-KR') + '억원'
  return Number(v).toLocaleString('ko-KR') + '원'
}
const dataTier = computed(() => {
  if (!detail.value || detail.value.price == null) return '기본 데이터'
  return detail.value.is_delayed ? '지연 데이터' : '실시간'
})
</script>

<template>
  <div class="container stocks-page">
    <div class="page-head">
      <div>
        <p class="eyebrow">F400 종목 조회</p>
        <h1>종목 조회</h1>
        <p class="muted sub">
          종목명과 종목코드로 검색하고 현재가, 등락률, 시가총액, 산업군을 확인합니다.
        </p>
        <p v-if="noLiveData" class="notice">토스증권 API 설정을 확인해야 합니다.</p>
      </div>
      <span class="data-badge">{{ noLiveData ? '기본 데이터' : '실시간' }}</span>
    </div>

    <form class="search-bar" @submit.prevent="onSearch">
      <input
        v-model="search"
        class="input"
        type="text"
        placeholder="종목명 또는 종목코드를 입력하세요"
      />
      <button type="submit" class="btn btn-primary">검색</button>
    </form>

    <div class="layout">
      <!-- 종목 목록 -->
      <div class="card list-card">
        <div class="list-head">
          <span>종목명</span>
          <span class="num">현재가</span>
          <span class="num">등락률</span>
          <span>산업군</span>
        </div>

        <p v-if="listLoading" class="muted state">불러오는 중...</p>
        <p v-else-if="listError" class="form-error state">{{ listError }}</p>
        <p v-else-if="!items.length" class="muted state">검색 결과가 없습니다.</p>

        <div v-else class="list-body">
          <button
            v-for="s in items"
            :key="s.code"
            type="button"
            class="srow"
            :class="{ active: s.code === selectedCode }"
            @click="selectStock(s.code)"
          >
            <span class="name">
              <span class="nm">{{ s.name }}</span>
              <span class="cd">{{ s.code }} · {{ s.market }}</span>
            </span>
            <span class="num">{{ priceText(s.price) }}</span>
            <span class="num" :class="dirClass(s.change_direction)">{{ pct(s.change_rate) }}</span>
            <span class="muted sector">{{ s.sector || '-' }}</span>
          </button>
        </div>
      </div>

      <!-- 상세 패널 -->
      <aside class="card panel">
        <template v-if="detail">
          <div class="p-head">
            <div>
              <p class="p-name">{{ detail.name }}</p>
              <p class="p-code">{{ detail.code }} · {{ detail.market }}</p>
            </div>
            <span class="p-change" :class="dirClass(detail.change_direction)">
              {{ pct(detail.change_rate) }}
            </span>
          </div>

          <div class="price-box">
            <span class="pb-label">현재가</span>
            <span class="pb-price">{{ priceText(detail.price) }}</span>
          </div>

          <dl class="p-list">
            <div><dt>시가총액</dt><dd>{{ marketCapText(detail.market_cap) }}</dd></div>
            <div><dt>산업군</dt><dd>{{ detail.sector }}</dd></div>
            <div><dt>데이터</dt><dd>{{ dataTier }}</dd></div>
          </dl>

          <div class="p-news">
            <p class="p-news-title">관련 뉴스</p>
            <div v-if="newsLoading" class="news-item muted">불러오는 중...</div>
            <div v-else-if="!stockNews.length" class="news-item muted">관련 뉴스가 없습니다.</div>
            <a
              v-for="n in stockNews"
              v-else
              :key="n.id"
              :href="n.url"
              target="_blank"
              rel="noopener noreferrer"
              class="news-item news-link"
            >
              <span class="news-link-title">{{ n.title }}</span>
              <span class="news-link-meta">
                <span v-if="n.source">{{ n.source }}</span>
                <span v-if="n.published_at">· {{ timeAgo(n.published_at) }}</span>
              </span>
            </a>
          </div>
        </template>
        <p v-else class="muted state">종목을 선택하세요.</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.stocks-page {
  padding: 38px 24px 64px;
}
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
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
.notice {
  margin: 18px 0 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}
.data-badge {
  flex-shrink: 0;
  margin-top: 0;
  padding: 7px 14px;
  border-radius: 999px;
  background: transparent;
  border: 1px solid var(--border);
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-muted);
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.search-bar .input {
  flex: 1;
  height: 44px;
  background: var(--surface-2);
}
.search-bar .btn {
  flex-shrink: 0;
  width: 68px;
  height: 44px;
  padding: 0;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  align-items: start;
}

/* 목록 */
.list-card {
  padding: 0;
  overflow: hidden;
}
.list-head,
.srow {
  display: grid;
  grid-template-columns: minmax(210px, 1.35fr) minmax(112px, 0.7fr) minmax(92px, 0.6fr) minmax(128px, 0.85fr);
  align-items: center;
  column-gap: 18px;
  padding: 0 18px;
}
.list-head {
  height: 46px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-muted);
}
.list-head > span,
.srow > span {
  min-width: 0;
}
.list-head .num {
  text-align: right;
}
.list-body {
  max-height: 540px;
  overflow-y: auto;
}
.srow {
  width: 100%;
  min-height: 62px;
  text-align: left;
  background: none;
  border: none;
  padding-top: 11px;
  padding-bottom: 11px;
  border-bottom: 1px solid var(--border);
  color: var(--text); /* 버튼은 색 상속이 안 돼 명시(종목명·현재가가 검게 나오던 문제) */
  transition: background 0.12s;
}
.srow:last-child {
  border-bottom: none;
}
.srow:hover {
  background: var(--surface-2);
}
.srow.active {
  background: #1d222a;
}
.name {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.nm {
  font-weight: 600;
  font-size: 14.5px;
  line-height: 1.25;
}
.nm,
.cd,
.sector {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cd {
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.25;
}
.num {
  justify-self: end;
  text-align: right;
  font-size: 14px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.sector {
  font-size: 13.5px;
  font-weight: 700;
  justify-self: start;
}
.up {
  color: var(--up);
  font-weight: 600;
}
.down {
  color: var(--down);
  font-weight: 600;
}
.state {
  text-align: center;
  padding: 48px 0;
}

/* 상세 패널 */
.panel {
  position: sticky;
  top: 84px;
  padding: 24px 22px 22px;
}
.p-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.p-name {
  font-size: 22px;
  line-height: 1.2;
  font-weight: 700;
  margin: 0;
}
.p-code {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-dim);
}
.p-change {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-muted);
}
.price-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 20px 18px;
  margin: 22px 0 20px;
}
.pb-label {
  font-size: 13px;
  color: var(--text-muted);
}
.pb-price {
  font-size: 29px;
  line-height: 1.25;
  font-weight: 700;
}
.p-list {
  margin: 0;
}
.p-list > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 0;
  border-bottom: 1px solid var(--border);
}
.p-list dt {
  color: var(--text-muted);
  font-size: 14px;
}
.p-list dd {
  margin: 0;
  font-weight: 600;
  text-align: right;
}
.p-news {
  margin-top: 18px;
}
.p-news-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0 0 10px;
}
.news-item {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  font-size: 13.5px;
}
.news-link {
  display: block;
  margin-bottom: 8px;
  transition: border-color 0.12s;
}
.news-link:last-child {
  margin-bottom: 0;
}
.news-link:hover {
  border-color: var(--gold);
}
.news-link-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
  color: var(--text);
}
.news-link-meta {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-dim);
}

@media (max-width: 860px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .panel {
    position: static;
  }
}
</style>
