<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'

const route = useRoute()
const router = useRouter()

const query = ref('')
const stocks = ref([])
const selected = ref(null)
const loading = ref(true)
const detailLoading = ref(false)
const errorMessage = ref('')
const tossStatus = ref({
  configured: false,
  message: '토스증권 API 설정 상태를 확인 중입니다.',
})

const selectedSymbol = computed(() => selected.value?.symbol || '')
const tossConfigured = computed(() => !!tossStatus.value.configured)

onMounted(async () => {
  query.value = typeof route.query.q === 'string' ? route.query.q : ''
  await fetchStocks()
  const code = typeof route.query.code === 'string' ? route.query.code : ''
  if (code) await selectStock(code)
  else if (stocks.value.length) await selectStock(stocks.value[0].symbol)
})

watch(
  () => route.query.code,
  async (code) => {
    if (typeof code === 'string' && code && code !== selectedSymbol.value) {
      await selectStock(code)
    }
  },
)

async function fetchStocks() {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await api.get('/stocks/', {
      params: { q: query.value, limit: 50 },
    })
    stocks.value = data.items || []
    tossStatus.value = data.toss_status || {
      configured: !!data.toss_configured,
      message: data.toss_configured
        ? '토스증권 API 인증 설정이 준비되었습니다.'
        : '토스증권 API 설정을 확인해야 합니다.',
    }
    await hydrateStockRows()
  } catch {
    errorMessage.value = '종목 목록을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

async function hydrateStockRows() {
  const visibleRows = stocks.value.slice(0, 20)
  const details = await Promise.allSettled(
    visibleRows.map((stock) => api.get(`/stocks/${stock.symbol}/`)),
  )

  details.forEach((result) => {
    if (result.status !== 'fulfilled') return
    mergeStockDetail(result.value.data)
  })
}

function mergeStockDetail(detail) {
  if (!detail?.symbol) return
  const hasLiveValue =
    detail.data_source === 'toss' ||
    Number(detail.current_price) > 0 ||
    Number(detail.change_rate) !== 0
  if (!hasLiveValue) return

  stocks.value = stocks.value.map((stock) =>
    stock.symbol === detail.symbol ? { ...stock, ...detail } : stock,
  )
}

async function onSearch() {
  router.replace({ name: 'stocks', query: query.value ? { q: query.value } : {} })
  await fetchStocks()
  if (stocks.value.length) await selectStock(stocks.value[0].symbol, false)
  else selected.value = null
}

async function selectStock(symbol, updateUrl = true) {
  detailLoading.value = true
  try {
    const { data } = await api.get(`/stocks/${symbol}/`)
    selected.value = data
    mergeStockDetail(data)
    if (updateUrl) {
      router.replace({
        name: 'stocks',
        query: { ...route.query, code: symbol },
      })
    }
  } finally {
    detailLoading.value = false
  }
}

function formatPrice(value, currency = 'KRW') {
  const number = Number(value)
  if (!Number.isFinite(number)) return '-'
  return currency === 'USD'
    ? `$${number.toLocaleString('en-US')}`
    : `${number.toLocaleString('ko-KR')}원`
}

function formatMarketCap(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '-'
  if (number >= 1_0000_0000_0000) {
    return `${(number / 1_0000_0000_0000).toFixed(1)}조원`
  }
  if (number >= 1_0000_0000) {
    return `${Math.round(number / 1_0000_0000).toLocaleString('ko-KR')}억원`
  }
  return `${number.toLocaleString('ko-KR')}원`
}

function formatRate(value) {
  if (value === null || value === undefined || value === '') return '-'
  const number = Number(value)
  if (!Number.isFinite(number)) return '-'
  return `${number > 0 ? '+' : ''}${number.toFixed(2)}%`
}
</script>

<template>
  <div class="stocks-page">
    <div class="container">
      <div class="page-head">
        <div>
          <p class="eyebrow">F400 종목 조회</p>
          <h1>종목 조회</h1>
          <p class="muted">
            종목명과 종목코드로 검색하고 현재가, 등락률, 시가총액, 산업군을 확인합니다.
          </p>
        </div>
        <span class="source-pill" :class="{ live: tossConfigured }">
          {{ tossConfigured ? '토스 API 연동' : '기본 데이터' }}
        </span>
      </div>

      <p v-if="!tossConfigured" class="status-note">{{ tossStatus.message }}</p>

      <form class="search-bar" @submit.prevent="onSearch">
        <input
          v-model="query"
          class="input"
          type="search"
          placeholder="종목명 또는 종목코드를 입력하세요"
        />
        <button class="btn btn-primary" type="submit">검색</button>
      </form>

      <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

      <div class="stock-layout">
        <section class="list-panel">
          <div class="table-head">
            <span>종목명</span>
            <span>현재가</span>
            <span>등락률</span>
            <span>산업군</span>
          </div>

          <p v-if="loading" class="muted empty">불러오는 중...</p>
          <p v-else-if="!stocks.length" class="muted empty">검색 결과가 없습니다.</p>

          <button
            v-for="stock in stocks"
            v-else
            :key="stock.symbol"
            type="button"
            class="stock-row"
            :class="{ active: selectedSymbol === stock.symbol }"
            @click="selectStock(stock.symbol)"
          >
            <span>
              <strong>{{ stock.name }}</strong>
              <small>{{ stock.symbol }} · {{ stock.market }}</small>
            </span>
            <span>{{ formatPrice(stock.current_price, stock.currency) }}</span>
            <span :class="Number(stock.change_rate) >= 0 ? 'up' : 'down'">
              {{ formatRate(stock.change_rate) }}
            </span>
            <span>{{ stock.sector }}</span>
          </button>
        </section>

        <aside class="detail-panel">
          <p v-if="detailLoading" class="muted">상세 정보를 불러오는 중...</p>
          <template v-else-if="selected">
            <div class="detail-top">
              <div>
                <h2>{{ selected.name }}</h2>
                <p class="muted">{{ selected.symbol }} · {{ selected.market }}</p>
              </div>
              <span :class="Number(selected.change_rate) >= 0 ? 'up' : 'down'">
                {{ formatRate(selected.change_rate) }}
              </span>
            </div>

            <div class="price-block">
              <span>현재가</span>
              <strong>{{ formatPrice(selected.current_price, selected.currency) }}</strong>
            </div>

            <dl class="detail-list">
              <div>
                <dt>시가총액</dt>
                <dd>{{ formatMarketCap(selected.market_cap) }}</dd>
              </div>
              <div>
                <dt>산업군</dt>
                <dd>{{ selected.sector }}</dd>
              </div>
              <div>
                <dt>데이터</dt>
                <dd>{{ selected.data_source === 'toss' ? '토스증권 API' : '기본 데이터' }}</dd>
              </div>
            </dl>

            <div class="news-box">
              <h3>관련 뉴스</h3>
              <RouterLink
                v-for="news in selected.related_news"
                :key="news.title"
                :to="news.url"
              >
                {{ news.title }}
              </RouterLink>
            </div>
          </template>
          <p v-else class="muted">종목을 선택해 주세요.</p>
        </aside>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stocks-page {
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
.source-pill {
  border: 1px solid var(--border);
  color: var(--text-muted);
  border-radius: 999px;
  padding: 7px 11px;
  font-size: 12.5px;
  font-weight: 700;
}
.source-pill.live {
  color: var(--gold);
  border-color: rgba(231, 178, 60, 0.5);
}
.status-note {
  border: 1px solid rgba(231, 178, 60, 0.35);
  background: rgba(231, 178, 60, 0.08);
  color: var(--text-muted);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  margin: 0 0 16px;
}
.search-bar {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  margin-bottom: 16px;
}
.stock-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  align-items: start;
}
.list-panel,
.detail-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.list-panel {
  overflow: hidden;
}
.table-head,
.stock-row {
  display: grid;
  grid-template-columns: 1.35fr 1fr 0.8fr 0.9fr;
  gap: 12px;
  align-items: center;
}
.table-head {
  padding: 14px 18px;
  color: var(--text-dim);
  font-size: 12px;
  font-weight: 700;
  border-bottom: 1px solid var(--border);
}
.stock-row {
  width: 100%;
  min-height: 62px;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  padding: 12px 18px;
  text-align: left;
}
.stock-row:last-child {
  border-bottom: none;
}
.stock-row:hover,
.stock-row.active {
  background: var(--surface-2);
}
.stock-row strong {
  display: block;
}
.stock-row small {
  color: var(--text-muted);
}
.up {
  color: var(--up);
  font-weight: 700;
}
.down {
  color: var(--down);
  font-weight: 700;
}
.empty {
  padding: 24px 18px;
}
.detail-panel {
  padding: 22px;
}
.detail-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 22px;
}
.detail-top h2 {
  font-size: 22px;
}
.detail-top .muted {
  margin: 4px 0 0;
}
.price-block {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 18px;
  margin-bottom: 16px;
}
.price-block span {
  color: var(--text-muted);
  font-size: 13px;
}
.price-block strong {
  display: block;
  font-size: 28px;
  margin-top: 4px;
}
.detail-list {
  margin: 0;
}
.detail-list div {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.detail-list dt {
  color: var(--text-muted);
}
.detail-list dd {
  margin: 0;
  font-weight: 600;
  text-align: right;
}
.news-box {
  margin-top: 20px;
}
.news-box h3 {
  font-size: 15px;
  margin-bottom: 10px;
}
.news-box a {
  display: block;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}
@media (max-width: 900px) {
  .page-head,
  .search-bar {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
  .stock-layout {
    grid-template-columns: 1fr;
  }
  .table-head {
    display: none;
  }
  .stock-row {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
