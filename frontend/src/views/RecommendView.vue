<script setup>
import { ref, onMounted } from 'vue'
import { useRecommendStore } from '@/stores/recommend'

const store = useRecommendStore()

const loading = ref(false)
const generating = ref(false)
const error = ref('')
const needProfile = ref(false)
const expandedCode = ref('')

function pct(rate) {
  if (rate == null) return '-'
  return (rate > 0 ? '+' : '') + (rate * 100).toFixed(2) + '%'
}
function priceText(p) {
  return p == null ? '-' : Number(p).toLocaleString('ko-KR') + '원'
}
function dirClass(d) {
  return d === 'UP' ? 'up' : d === 'DOWN' ? 'down' : ''
}
function toggleItem(code) {
  expandedCode.value = expandedCode.value === code ? '' : code
}
function articleMeta(article) {
  const parts = []
  if (article.source) parts.push(article.source)
  if (article.published_at) {
    const date = new Date(article.published_at)
    if (!Number.isNaN(date.getTime())) {
      parts.push(date.toLocaleString('ko-KR', { dateStyle: 'short', timeStyle: 'short' }))
    }
  }
  return parts.join(' · ')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    await store.fetchRecommendation()
  } catch {
    error.value = '추천을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

async function generate() {
  generating.value = true
  error.value = ''
  needProfile.value = false
  try {
    await store.generateRecommendation()
  } catch (e) {
    if (e.response?.status === 400 && e.response.data?.code === 'PROFILE_REQUIRED') {
      needProfile.value = true
    } else {
      error.value = '추천 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.'
    }
  } finally {
    generating.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container rec-page">
    <div class="page-head">
      <div>
        <p class="eyebrow">F300 AI 추천</p>
        <h1>맞춤 종목 추천</h1>
        <p class="muted sub">
          투자 성향(위험·기간·목적·관심산업)을 바탕으로 종목을 추천합니다.
        </p>
      </div>
      <button
        v-if="store.recommendation"
        class="btn btn-ghost"
        :disabled="generating"
        @click="generate"
      >
        {{ generating ? '생성 중...' : '다시 추천받기' }}
      </button>
    </div>

    <p v-if="loading" class="muted state">불러오는 중...</p>
    <p v-else-if="error" class="form-error">{{ error }}</p>

    <!-- 투자성향 필요 -->
    <div v-else-if="needProfile" class="card empty">
      <h2>투자 성향이 필요해요</h2>
      <p class="muted">추천을 받으려면 먼저 투자 성향 설문을 완료해 주세요.</p>
      <RouterLink to="/investment-profile" class="btn btn-primary">투자 성향 등록하기 →</RouterLink>
    </div>

    <!-- 추천 없음 -->
    <div v-else-if="!store.recommendation" class="card empty">
      <h2>아직 추천이 없어요</h2>
      <p class="muted">버튼을 누르면 내 투자 성향에 맞는 종목을 추천해 드려요.</p>
      <button class="btn btn-primary" :disabled="generating" @click="generate">
        {{ generating ? '생성 중...' : 'AI 추천 받기' }}
      </button>
    </div>

    <!-- 추천 결과 -->
    <template v-else>
      <div class="meta">
        <span class="badge">{{ store.recommendation.risk_type_display }}</span>
        <span class="muted source">
          추천 이유 · {{ store.recommendation.reason_source === 'gms' ? 'AI 생성' : '규칙 기반' }}
        </span>
      </div>

      <ol class="rec-list">
        <li
          v-for="item in store.recommendation.items"
          :key="item.stock.code"
          class="card rec-item"
          :class="{ expanded: expandedCode === item.stock.code }"
          @click="toggleItem(item.stock.code)"
        >
          <div class="ri-rank">{{ item.rank }}</div>
          <div class="ri-body">
            <div class="ri-top">
              <div class="ri-id">
                <p class="ri-name">{{ item.stock.name }}</p>
                <p class="ri-code">
                  {{ item.stock.code }} · {{ item.stock.market }} · {{ item.stock.sector || '미분류' }}
                </p>
              </div>
              <div class="ri-price">
                <span class="num">{{ priceText(item.stock.price) }}</span>
                <span class="num small" :class="dirClass(item.stock.change_direction)">
                  {{ pct(item.stock.change_rate) }}
                </span>
              </div>
            </div>
            <p class="ri-reason">{{ item.reason }}</p>
            <div class="ri-score">
              <div class="bar"><span :style="{ width: Math.min(item.score, 100) + '%' }"></span></div>
              <span class="score-val">{{ Math.round(item.score) }}점</span>
              <button class="news-toggle" type="button" @click.stop="toggleItem(item.stock.code)">
                {{ expandedCode === item.stock.code ? '뉴스 접기' : `뉴스 보기 ${item.news_articles?.length || 0}` }}
              </button>
            </div>

            <div v-if="expandedCode === item.stock.code" class="news-panel" @click.stop>
              <div v-if="item.news_articles?.length" class="news-list">
                <a
                  v-for="article in item.news_articles"
                  :key="article.url"
                  class="news-link"
                  :href="article.url"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span class="news-title">{{ article.title }}</span>
                  <span v-if="articleMeta(article)" class="news-meta">{{ articleMeta(article) }}</span>
                </a>
              </div>
              <p v-else class="muted news-empty">연결된 뉴스 기사가 없습니다.</p>
            </div>
          </div>
        </li>
      </ol>

      <p class="disclaimer muted">
        추천·점수는 투자 참고용이며, 투자 판단과 책임은 본인에게 있습니다.
      </p>
    </template>
  </div>
</template>

<style scoped>
.rec-page {
  padding: 38px 24px 64px;
}
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
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
.state {
  text-align: center;
  padding: 56px 0;
}

/* 빈 상태 */
.empty {
  text-align: center;
  padding: 52px 36px;
  max-width: 520px;
  margin: 0 auto;
}
.empty h2 {
  font-size: 21px;
  margin-bottom: 10px;
}
.empty .btn {
  margin-top: 22px;
}

/* 메타 */
.meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.badge {
  padding: 6px 13px;
  border-radius: 999px;
  background: rgba(231, 178, 60, 0.12);
  border: 1px solid rgba(231, 178, 60, 0.4);
  color: var(--gold);
  font-size: 13px;
  font-weight: 700;
}
.source {
  font-size: 13.5px;
}

/* 추천 리스트 */
.rec-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rec-item {
  display: flex;
  gap: 16px;
  padding: 18px 20px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.rec-item:hover,
.rec-item.expanded {
  border-color: rgba(231, 178, 60, 0.45);
  background: var(--surface-2);
}
.ri-rank {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: var(--surface-3);
  color: var(--gold);
  font-weight: 700;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ri-body {
  flex: 1;
  min-width: 0;
}
.ri-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.ri-name {
  font-size: 17px;
  font-weight: 700;
  margin: 0;
}
.ri-code {
  margin: 4px 0 0;
  font-size: 12.5px;
  color: var(--text-dim);
}
.ri-price {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.num {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.num.small {
  font-size: 13px;
}
.up {
  color: var(--up);
}
.down {
  color: var(--down);
}
.ri-reason {
  margin: 12px 0 14px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text);
}
.ri-score {
  display: flex;
  align-items: center;
  gap: 12px;
}
.bar {
  flex: 1;
  height: 7px;
  border-radius: 999px;
  background: var(--surface-3);
  overflow: hidden;
}
.bar > span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--gold);
}
.score-val {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--gold);
  width: 44px;
  text-align: right;
}
.news-toggle {
  flex-shrink: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  padding: 7px 10px;
  font-size: 12.5px;
  font-weight: 700;
}
.news-toggle:hover {
  color: var(--gold);
  border-color: rgba(231, 178, 60, 0.45);
}
.news-panel {
  margin-top: 14px;
  border-top: 1px solid var(--border);
  padding-top: 14px;
}
.news-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.news-link {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 11px 12px;
  border-radius: var(--radius-sm);
  background: var(--surface);
  border: 1px solid var(--border);
}
.news-link:hover {
  border-color: rgba(231, 178, 60, 0.45);
}
.news-title {
  min-width: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text);
  overflow-wrap: anywhere;
}
.news-meta {
  color: var(--text-muted);
  font-size: 12px;
  white-space: nowrap;
}
.news-empty {
  margin: 0;
  font-size: 13px;
}
.disclaimer {
  margin-top: 22px;
  font-size: 12.5px;
  text-align: center;
}

@media (max-width: 620px) {
  .ri-top {
    flex-direction: column;
  }
  .ri-price {
    text-align: left;
    flex-direction: row;
    gap: 10px;
  }
  .ri-score {
    flex-wrap: wrap;
  }
  .news-toggle {
    width: 100%;
  }
  .news-link {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  .news-meta {
    white-space: normal;
  }
}
</style>
