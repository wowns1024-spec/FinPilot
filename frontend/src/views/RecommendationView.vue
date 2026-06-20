<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const { recommendation, investmentProfile } = storeToRefs(auth)

const loading = ref(true)
const requesting = ref(false)
const needsProfile = ref(false)
const errorMessage = ref('')

const topItem = computed(() => recommendation.value?.items?.[0] || null)
const restItems = computed(() => recommendation.value?.items?.slice(1) || [])

const createdAt = computed(() => {
  if (!recommendation.value?.created_at) return ''
  return new Date(recommendation.value.created_at).toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
})

onMounted(async () => {
  try {
    await Promise.all([
      auth.fetchInvestmentProfile(),
      auth.fetchLatestRecommendation(),
    ])
    needsProfile.value = !investmentProfile.value
  } catch {
    errorMessage.value = '추천 정보를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
})

async function onRequest() {
  errorMessage.value = ''
  needsProfile.value = false
  requesting.value = true
  try {
    await auth.requestRecommendation()
  } catch (e) {
    if (e.response?.status === 409) {
      needsProfile.value = true
    } else {
      errorMessage.value = '추천 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.'
    }
  } finally {
    requesting.value = false
  }
}

function formatPrice(value) {
  return `${Number(value).toLocaleString('ko-KR')}원`
}
</script>

<template>
  <div class="recommend-page">
    <div class="container">
      <div class="page-head">
        <div>
          <p class="eyebrow">F300 AI 종목 추천</p>
          <h1>AI 종목 추천</h1>
          <p class="muted">
            투자성향과 관심 산업을 분석해 맞춤 종목과 추천 이유를 제공합니다.
          </p>
        </div>
        <button class="btn btn-primary" :disabled="requesting" @click="onRequest">
          {{ requesting ? '추천 생성 중...' : 'AI 종목 추천 받기' }}
        </button>
      </div>

      <div v-if="loading" class="empty-panel">
        <p class="muted">불러오는 중...</p>
      </div>

      <div v-else-if="needsProfile" class="empty-panel">
        <h2>투자 성향 설문이 필요합니다</h2>
        <p class="muted">
          추천 기준을 만들기 위해 투자 가능 자산, 위험 선호도, 관심 산업을 먼저 입력해 주세요.
        </p>
        <RouterLink to="/investment-profile" class="btn btn-primary">
          설문 작성하러 가기
        </RouterLink>
      </div>

      <div v-else-if="!recommendation" class="empty-panel">
        <h2>아직 추천 결과가 없습니다</h2>
        <p class="muted">버튼을 누르면 투자 성향을 바탕으로 추천 종목을 생성합니다.</p>
      </div>

      <template v-else>
        <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

        <div class="analysis-panel">
          <div>
            <span class="badge">{{ recommendation.used_ai ? 'GMS AI 사용' : '기본 추천 엔진' }}</span>
            <h2>추천 기준</h2>
            <p>{{ recommendation.analysis_summary }}</p>
          </div>
          <span class="muted">{{ createdAt }}</span>
        </div>

        <div class="recommend-grid">
          <section v-if="topItem" class="top-card">
            <div class="rank-label">1위 {{ topItem.stock_name }}</div>
            <div class="stock-meta">
              <span>{{ topItem.stock_code }}</span>
              <span>{{ topItem.sector }}</span>
            </div>
            <div class="price-row">
              <strong>{{ formatPrice(topItem.current_price) }}</strong>
              <div class="score-ring">
                <span>추천 점수</span>
                <b>{{ topItem.score }}점</b>
              </div>
            </div>

            <div class="reason-box">
              <h3>AI 추천 이유</h3>
              <p>{{ topItem.reason }}</p>
            </div>

            <div class="link-actions">
              <RouterLink :to="`/stocks?code=${topItem.stock_code}`" class="btn btn-ghost">
                종목 상세 보기
              </RouterLink>
              <RouterLink :to="topItem.news_url || '/news'" class="btn btn-ghost">
                관련 뉴스 보기
              </RouterLink>
            </div>
          </section>

          <aside class="rank-list">
            <h2>추천 목록</h2>
            <article
              v-for="item in restItems"
              :key="item.stock_code"
              class="rank-item"
            >
              <div>
                <span class="rank">{{ item.rank }}</span>
                <strong>{{ item.stock_name }}</strong>
                <p>{{ item.stock_code }} · {{ item.sector }}</p>
              </div>
              <div class="item-score">{{ item.score }}점</div>
            </article>
          </aside>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.recommend-page {
  padding: 40px 0 64px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  margin-bottom: 24px;
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
.empty-panel,
.analysis-panel,
.top-card,
.rank-list {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.empty-panel {
  padding: 48px;
  text-align: center;
}
.empty-panel h2 {
  font-size: 20px;
  margin-bottom: 10px;
}
.empty-panel .btn {
  margin-top: 16px;
}
.analysis-panel {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 22px;
  margin-bottom: 16px;
}
.analysis-panel h2 {
  font-size: 17px;
  margin: 8px 0 6px;
}
.analysis-panel p {
  color: var(--text-muted);
  margin: 0;
}
.badge {
  display: inline-flex;
  border: 1px solid rgba(231, 178, 60, 0.5);
  color: var(--gold);
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 700;
}
.recommend-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.7fr);
  gap: 16px;
}
.top-card {
  padding: 28px;
}
.rank-label {
  color: var(--gold);
  font-size: 20px;
  font-weight: 800;
}
.stock-meta {
  display: flex;
  gap: 8px;
  color: var(--text-muted);
  margin-top: 4px;
}
.price-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin: 28px 0;
}
.price-row strong {
  font-size: 30px;
}
.score-ring {
  width: 118px;
  height: 118px;
  border: 8px solid rgba(231, 178, 60, 0.8);
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.score-ring span {
  font-size: 11px;
  color: var(--text-muted);
}
.score-ring b {
  color: var(--gold);
  font-size: 23px;
}
.reason-box {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 18px;
}
.reason-box h3 {
  font-size: 15px;
  margin-bottom: 8px;
}
.reason-box p {
  color: var(--text-muted);
  margin: 0;
}
.link-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}
.rank-list {
  padding: 22px;
}
.rank-list h2 {
  font-size: 17px;
  margin-bottom: 14px;
}
.rank-item {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
}
.rank-item:last-child {
  border-bottom: none;
}
.rank {
  color: var(--gold);
  font-weight: 800;
  margin-right: 8px;
}
.rank-item p {
  color: var(--text-muted);
  margin: 3px 0 0;
  font-size: 13px;
}
.item-score {
  align-self: center;
  border: 1px solid rgba(231, 178, 60, 0.45);
  color: var(--gold);
  border-radius: 999px;
  padding: 6px 9px;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}
@media (max-width: 860px) {
  .page-head,
  .analysis-panel,
  .price-row,
  .link-actions {
    flex-direction: column;
    align-items: stretch;
  }
  .recommend-grid {
    grid-template-columns: 1fr;
  }
}
</style>
