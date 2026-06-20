<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useProfileStore } from '@/stores/profile'

const store = useProfileStore()
const { options, profile } = storeToRefs(store)

// 단일 선택 4문항 (선택지는 /options/ 에서 동적 수신)
const SELECTS = [
  { key: 'available_asset', label: '투자 가능 자산' },
  { key: 'risk_type', label: '위험 선호도' },
  { key: 'investment_period', label: '투자 기간' },
  { key: 'investment_goal', label: '투자 목적' },
]

// 일부 보기에 대한 보조 설명 (값 코드 기준). 없는 항목은 라벨만 표시.
const OPTION_DESC = {
  risk_type: {
    STABLE: '원금 손실을 원하지 않고 예금 수준의 안정성을 추구',
    STABLE_SEEKING: '원금 보존을 우선하되 약간의 손실 위험은 감수',
    BALANCED: '기대수익과 위험을 균형 있게 고려',
    ACTIVE: '높은 수익을 위해 원금 손실 위험을 적극 수용',
    AGGRESSIVE: '최대 수익을 노리고 큰 손실 위험까지 감수',
  },
  investment_period: {
    SHORT: '수일~수주 안에 사고파는 단기 매매',
    SWING: '수주~수개월 추세를 따라가는 매매',
    LONG: '수개월~수년 길게 보유하는 장기 투자',
  },
}

const loading = ref(true)
const mode = ref('form') // 'form' | 'view'
const submitting = ref(false)
const deleting = ref(false)
const formError = ref('')

const form = reactive({
  available_asset: null,
  risk_type: '',
  investment_period: '',
  investment_goal: '',
  sectors: [],
})

const isPicked = (key) => form[key] !== null && form[key] !== ''
const valid = computed(
  () => SELECTS.every((s) => isPicked(s.key)) && form.sectors.length >= 1,
)
const answered = computed(
  () => SELECTS.filter((s) => isPicked(s.key)).length + (form.sectors.length ? 1 : 0),
)
const progressPct = computed(() =>
  Math.round((answered.value / (SELECTS.length + 1)) * 100),
)

onMounted(async () => {
  try {
    const [, prof] = await Promise.all([store.fetchOptions(), store.fetchProfile()])
    mode.value = prof ? 'view' : 'form'
  } catch {
    formError.value = '불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'
  } finally {
    loading.value = false
  }
})

function toggleSector(code) {
  const i = form.sectors.indexOf(code)
  if (i === -1) form.sectors.push(code)
  else form.sectors.splice(i, 1)
}

function resetForm() {
  form.available_asset = null
  form.risk_type = ''
  form.investment_period = ''
  form.investment_goal = ''
  form.sectors = []
}

function prefillFromProfile() {
  if (!profile.value) return
  form.available_asset = profile.value.available_asset
  form.risk_type = profile.value.risk_type
  form.investment_period = profile.value.investment_period
  form.investment_goal = profile.value.investment_goal
  form.sectors = profile.value.sectors_detail.map((s) => s.code)
}

function startEdit() {
  prefillFromProfile()
  formError.value = ''
  mode.value = 'form'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function cancelEdit() {
  mode.value = 'view'
}

function firstError(data) {
  if (!data || typeof data !== 'object') return ''
  const v = Object.values(data)[0]
  return Array.isArray(v) ? v[0] : String(v)
}

async function onSubmit() {
  if (!valid.value || submitting.value) return
  formError.value = ''
  submitting.value = true
  try {
    await store.saveProfile({
      available_asset: form.available_asset,
      risk_type: form.risk_type,
      investment_period: form.investment_period,
      investment_goal: form.investment_goal,
      sectors: [...form.sectors],
    })
    mode.value = 'view'
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) {
    formError.value =
      firstError(e.response?.data) || '저장에 실패했습니다. 잠시 후 다시 시도해 주세요.'
  } finally {
    submitting.value = false
  }
}

async function onDelete() {
  if (!window.confirm('투자 성향을 삭제할까요? 추천을 받으려면 다시 설문해야 해요.')) return
  deleting.value = true
  formError.value = ''
  try {
    await store.deleteProfile()
    resetForm()
    mode.value = 'form'
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch {
    formError.value = '삭제에 실패했습니다.'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="container survey-page">
    <p v-if="loading" class="muted loading">불러오는 중...</p>

    <!-- 결과 (F208) -->
    <div v-else-if="mode === 'view' && profile" class="card result-card">
      <p class="result-eyebrow">나의 투자 성향</p>
      <h1 class="result-risk text-gold">{{ profile.risk_type_display }}</h1>

      <dl class="summary">
        <div class="summary-row">
          <dt>투자 가능 자산</dt>
          <dd>{{ profile.available_asset_display }}</dd>
        </div>
        <div class="summary-row">
          <dt>투자 기간</dt>
          <dd>{{ profile.investment_period_display }}</dd>
        </div>
        <div class="summary-row">
          <dt>투자 목적</dt>
          <dd>{{ profile.investment_goal_display }}</dd>
        </div>
        <div class="summary-row">
          <dt>관심 산업</dt>
          <dd class="tags">
            <span v-for="s in profile.sectors_detail" :key="s.code" class="tag">
              {{ s.name }}
            </span>
          </dd>
        </div>
      </dl>

      <p v-if="formError" class="form-error">{{ formError }}</p>

      <div class="result-actions">
        <button class="btn btn-ghost" :disabled="deleting" @click="onDelete">
          {{ deleting ? '삭제 중...' : '삭제' }}
        </button>
        <button class="btn btn-ghost" @click="startEdit">수정하기</button>
        <RouterLink to="/recommend" class="btn btn-primary">
          이 성향으로 추천받기 →
        </RouterLink>
      </div>
    </div>

    <!-- 설문 폼 (F201~F207) -->
    <template v-else>
      <div class="form-head">
        <h1>투자 성향 {{ profile ? '수정' : '분석' }}</h1>
        <p class="muted">추천에 활용할 투자 선호를 선택해 주세요.</p>
        <div class="progress">
          <div class="progress-bar" :style="{ width: progressPct + '%' }"></div>
        </div>
      </div>

      <p v-if="formError" class="form-error">{{ formError }}</p>

      <!-- 테트리스(2열 메이슨리) 배치로 한눈에 -->
      <div class="form-grid">
        <!-- 단일 선택 4문항 -->
        <div v-for="(sec, i) in SELECTS" :key="sec.key" class="card q-card">
          <p class="q-text"><span class="q-num">{{ i + 1 }}</span>{{ sec.label }}</p>
          <div class="q-options">
            <button
              v-for="opt in options?.[sec.key] || []"
              :key="opt.value"
              type="button"
              class="opt"
              :class="{ selected: form[sec.key] === opt.value }"
              @click="form[sec.key] = opt.value"
            >
              <span class="opt-radio"></span>
              <span class="opt-body">
                <span class="opt-label">{{ opt.label }}</span>
                <span v-if="OPTION_DESC[sec.key]?.[opt.value]" class="opt-desc">
                  {{ OPTION_DESC[sec.key][opt.value] }}
                </span>
              </span>
            </button>
          </div>
        </div>

        <!-- 관심 산업 (복수 선택) — 전체폭 -->
        <div class="card q-card sectors-card">
          <p class="q-text">
            <span class="q-num">5</span>관심 산업 <span class="q-sub">(최소 1개)</span>
          </p>
          <div class="chips">
            <button
              v-for="s in options?.sectors || []"
              :key="s.code"
              type="button"
              class="chip"
              :class="{ selected: form.sectors.includes(s.code) }"
              @click="toggleSector(s.code)"
            >
              {{ s.name }}
            </button>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button v-if="profile" type="button" class="btn btn-ghost" @click="cancelEdit">
          취소
        </button>
        <button class="btn btn-primary submit-btn" :disabled="!valid || submitting" @click="onSubmit">
          {{ submitting ? '저장 중...' : profile ? '수정 저장' : '저장하고 결과 보기' }}
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.survey-page {
  padding: 40px 24px 64px;
  max-width: 880px;
}
.loading {
  text-align: center;
  padding: 80px 0;
}

/* ---- 폼 ---- */
.form-head {
  margin-bottom: 24px;
}
.form-head h1 {
  font-size: 26px;
}
.form-head .muted {
  margin: 8px 0 18px;
  font-size: 14.5px;
}
.progress {
  height: 8px;
  background: var(--surface-3);
  border-radius: 999px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background: var(--gold);
  border-radius: 999px;
  transition: width 0.25s ease;
}
.form-grid {
  columns: 2;
  column-gap: 16px;
}
.q-card {
  padding: 22px 24px;
  margin-bottom: 16px;
  break-inside: avoid;
}
/* 관심 산업은 칩이 많아 전체폭으로 (메이슨리 아래 전폭 배치) */
.sectors-card {
  column-span: all;
}
.q-text {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
}
.q-num {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-3);
  color: var(--gold);
  border-radius: 50%;
  font-size: 13px;
  font-weight: 700;
}
.q-sub {
  font-size: 13px;
  color: var(--text-dim);
  font-weight: 400;
}
.q-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.opt {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  text-align: left;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 13px 16px;
  color: var(--text);
  font-size: 14.5px;
  transition: border-color 0.15s, background 0.15s;
}
.opt:hover {
  border-color: var(--text-dim);
}
.opt.selected {
  border-color: var(--gold);
  background: rgba(231, 178, 60, 0.08);
}
.opt-radio {
  position: relative;
  flex-shrink: 0;
  margin-top: 2px;
  width: 18px;
  height: 18px;
  border: 2px solid var(--border);
  border-radius: 50%;
  transition: border-color 0.15s;
}
.opt.selected .opt-radio {
  border-color: var(--gold);
}
.opt.selected .opt-radio::after {
  content: '';
  position: absolute;
  inset: 3px;
  border-radius: 50%;
  background: var(--gold);
}
.opt-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.opt-label {
  font-size: 14.5px;
}
.opt-desc {
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-dim);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.chip {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 9px 16px;
  color: var(--text-muted);
  font-size: 14px;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.chip:hover {
  border-color: var(--text-dim);
  color: var(--text);
}
.chip.selected {
  background: rgba(231, 178, 60, 0.12);
  border-color: var(--gold);
  color: var(--gold);
  font-weight: 600;
}
.form-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 8px;
}
.submit-btn {
  flex: 1;
  padding: 14px;
  font-size: 15.5px;
}

/* ---- 결과 ---- */
.result-card {
  padding: 36px 32px;
  max-width: 600px;
  margin: 0 auto;
}
.result-eyebrow {
  color: var(--text-muted);
  font-size: 14px;
  margin: 0 0 4px;
}
.result-risk {
  font-size: 32px;
  margin: 0;
}
.summary {
  margin: 24px 0 28px;
}
.summary-row {
  display: flex;
  padding: 13px 0;
  border-bottom: 1px solid var(--border);
}
.summary-row:last-child {
  border-bottom: none;
}
.summary-row dt {
  width: 130px;
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: 14px;
}
.summary-row dd {
  margin: 0;
  font-weight: 500;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag {
  background: var(--surface-3);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 500;
}
.result-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
@media (max-width: 760px) {
  .form-grid {
    columns: 1;
  }
}
@media (max-width: 560px) {
  .result-card {
    padding: 28px 22px;
  }
  .result-risk {
    font-size: 26px;
  }
}
</style>
