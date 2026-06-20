<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const assetRanges = [
  { label: '100만원 미만', value: 500000 },
  { label: '100만원-500만원', value: 3000000 },
  { label: '500만원-1천만원', value: 7500000 },
  { label: '1천만원 이상', value: 10000000 },
]

const riskTypes = [
  { label: '안정형', value: 'stable', hint: '원금 보존을 가장 중시' },
  { label: '안정추구형', value: 'stability_seeking', hint: '낮은 변동성 선호' },
  { label: '균형형', value: 'balanced', hint: '수익과 위험의 균형' },
  { label: '적극투자형', value: 'active', hint: '성장성과 변동성 수용' },
  { label: '공격투자형', value: 'aggressive', hint: '높은 수익 기회 추구' },
]

const periods = [
  { label: '단타', value: 'short' },
  { label: '스윙', value: 'swing' },
  { label: '중장기', value: 'long' },
]

const goals = [
  { label: '자산 증식', value: 'growth' },
  { label: '안정적 수익', value: 'stable_income' },
  { label: '배당 수익', value: 'dividend' },
  { label: '단기 차익', value: 'short_profit' },
  { label: '노후 대비', value: 'retirement' },
]

const styles = [
  { label: '가치 투자', value: 'value' },
  { label: '성장 투자', value: 'growth' },
  { label: '배당 투자', value: 'dividend' },
  { label: '모멘텀', value: 'momentum' },
  { label: '뉴스 기반', value: 'news' },
]

const industries = [
  { label: '반도체', value: 'semiconductor' },
  { label: '2차전지', value: 'battery' },
  { label: '방산', value: 'defense' },
  { label: 'AI', value: 'ai' },
  { label: '에너지', value: 'energy' },
  { label: '게임', value: 'game' },
  { label: '바이오', value: 'bio' },
  { label: '소비재', value: 'consumer' },
  { label: '금융', value: 'finance' },
  { label: '자동차', value: 'auto' },
]

const form = reactive({
  available_asset: '',
  risk_type: '',
  investment_period: '',
  investment_goal: '',
  investment_style: '',
  interest_industries: [],
})

const errors = reactive({
  available_asset: '',
  risk_type: '',
  investment_period: '',
  investment_goal: '',
  interest_industries: '',
})

const loading = ref(true)
const submitting = ref(false)
const formError = ref('')
const savedOnce = ref(false)

const formattedAsset = computed(() => {
  const value = Number(form.available_asset)
  if (!value) return '-'
  return `${value.toLocaleString('ko-KR')}원`
})

onMounted(async () => {
  const profile = await auth.fetchInvestmentProfile()
  if (profile) {
    form.available_asset = profile.available_asset
    form.risk_type = profile.risk_type
    form.investment_period = profile.investment_period
    form.investment_goal = profile.investment_goal
    form.investment_style = profile.investment_style || ''
    form.interest_industries = [...profile.interest_industries]
    savedOnce.value = true
  }
  loading.value = false
})

function setAsset(value) {
  form.available_asset = value
  errors.available_asset = ''
}

function selectSingle(field, value) {
  form[field] = value
  errors[field] = ''
}

function toggleIndustry(value) {
  const index = form.interest_industries.indexOf(value)
  if (index >= 0) form.interest_industries.splice(index, 1)
  else form.interest_industries.push(value)
  errors.interest_industries = ''
}

function validate() {
  Object.keys(errors).forEach((key) => (errors[key] = ''))
  formError.value = ''

  const asset = Number(form.available_asset)
  if (!Number.isInteger(asset) || asset <= 0) {
    errors.available_asset = '투자 가능 자산을 숫자로 입력해 주세요.'
  }
  if (!form.risk_type) errors.risk_type = '투자 성향을 선택해 주세요.'
  if (!form.investment_period) errors.investment_period = '투자 기간을 선택해 주세요.'
  if (!form.investment_goal) errors.investment_goal = '투자 목적을 선택해 주세요.'
  if (form.interest_industries.length === 0) {
    errors.interest_industries = '관심 산업을 1개 이상 선택해 주세요.'
  }

  return Object.values(errors).every((message) => !message)
}

async function onSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    await auth.saveInvestmentProfile({
      available_asset: Number(form.available_asset),
      risk_type: form.risk_type,
      investment_period: form.investment_period,
      investment_goal: form.investment_goal,
      investment_style: form.investment_style,
      interest_industries: form.interest_industries,
    })
    router.push({ name: 'mypage', query: { tab: 'investment' } })
  } catch (e) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      for (const [key, val] of Object.entries(data)) {
        const msg = Array.isArray(val) ? val.join(' ') : String(val)
        if (key in errors) errors[key] = msg
        else formError.value = msg
      }
    } else {
      formError.value = '투자 성향 저장에 실패했습니다.'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="survey-page">
    <div class="container survey-shell">
      <div class="survey-head">
        <div>
          <p class="eyebrow">F200 투자성향 관리</p>
          <h1>투자 성향 설문</h1>
          <p class="muted">
            입력한 정보는 AI 종목 추천의 자산 규모, 위험도, 기간, 목적 필터에 사용됩니다.
          </p>
        </div>
        <div class="steps" aria-label="설문 단계">
          <span class="step active">1 기본정보</span>
          <span class="step active">2 투자 성향</span>
          <span class="step active">3 투자 목적</span>
          <span class="step active">4 완료</span>
        </div>
      </div>

      <p v-if="loading" class="muted">불러오는 중...</p>
      <form v-else class="survey-grid" @submit.prevent="onSubmit">
        <p v-if="formError" class="form-error full">{{ formError }}</p>

        <section class="survey-panel">
          <div class="section-head">
            <h2>기본정보</h2>
            <span class="required">필수</span>
          </div>

          <div class="field">
            <label for="available_asset">투자 가능 자산</label>
            <div class="asset-input">
              <input
                id="available_asset"
                v-model="form.available_asset"
                class="input"
                type="number"
                min="1"
                step="1"
                placeholder="직접 입력"
                @input="errors.available_asset = ''"
              />
              <span>{{ formattedAsset }}</span>
            </div>
            <div class="choice-grid two">
              <button
                v-for="range in assetRanges"
                :key="range.label"
                type="button"
                class="choice"
                :class="{ selected: Number(form.available_asset) === range.value }"
                @click="setAsset(range.value)"
              >
                {{ range.label }}
              </button>
            </div>
            <p v-if="errors.available_asset" class="field-error">
              {{ errors.available_asset }}
            </p>
          </div>
        </section>

        <section class="survey-panel">
          <div class="section-head">
            <h2>투자 성향</h2>
            <span class="required">필수</span>
          </div>

          <div class="choice-stack">
            <button
              v-for="risk in riskTypes"
              :key="risk.value"
              type="button"
              class="choice risk-choice"
              :class="{ selected: form.risk_type === risk.value }"
              @click="selectSingle('risk_type', risk.value)"
            >
              <strong>{{ risk.label }}</strong>
              <span>{{ risk.hint }}</span>
            </button>
          </div>
          <p v-if="errors.risk_type" class="field-error">{{ errors.risk_type }}</p>
        </section>

        <section class="survey-panel">
          <div class="section-head">
            <h2>투자 기간</h2>
            <span class="required">필수</span>
          </div>
          <div class="choice-grid three">
            <button
              v-for="period in periods"
              :key="period.value"
              type="button"
              class="choice"
              :class="{ selected: form.investment_period === period.value }"
              @click="selectSingle('investment_period', period.value)"
            >
              {{ period.label }}
            </button>
          </div>
          <p v-if="errors.investment_period" class="field-error">
            {{ errors.investment_period }}
          </p>
        </section>

        <section class="survey-panel">
          <div class="section-head">
            <h2>투자 목적</h2>
            <span class="required">필수</span>
          </div>
          <div class="choice-grid wrap">
            <button
              v-for="goal in goals"
              :key="goal.value"
              type="button"
              class="choice"
              :class="{ selected: form.investment_goal === goal.value }"
              @click="selectSingle('investment_goal', goal.value)"
            >
              {{ goal.label }}
            </button>
          </div>
          <p v-if="errors.investment_goal" class="field-error">
            {{ errors.investment_goal }}
          </p>
        </section>

        <section class="survey-panel">
          <div class="section-head">
            <h2>투자 스타일</h2>
            <span class="optional">선택</span>
          </div>
          <div class="choice-grid wrap">
            <button
              v-for="style in styles"
              :key="style.value"
              type="button"
              class="choice"
              :class="{ selected: form.investment_style === style.value }"
              @click="selectSingle('investment_style', style.value)"
            >
              {{ style.label }}
            </button>
          </div>
        </section>

        <section class="survey-panel">
          <div class="section-head">
            <h2>관심 산업</h2>
            <span class="required">필수</span>
          </div>
          <div class="choice-grid sectors">
            <button
              v-for="industry in industries"
              :key="industry.value"
              type="button"
              class="choice"
              :class="{ selected: form.interest_industries.includes(industry.value) }"
              @click="toggleIndustry(industry.value)"
            >
              {{ industry.label }}
            </button>
          </div>
          <p v-if="errors.interest_industries" class="field-error">
            {{ errors.interest_industries }}
          </p>
        </section>

        <div class="actions full">
          <button type="button" class="btn btn-ghost" @click="router.push('/mypage')">
            취소
          </button>
          <button type="submit" class="btn btn-primary" :disabled="submitting">
            {{ submitting ? '저장 중...' : savedOnce ? '수정 완료' : '설문 저장' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.survey-page {
  padding: 36px 0 64px;
}
.survey-shell {
  max-width: 1080px;
}
.survey-head {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  margin-bottom: 24px;
}
.eyebrow {
  color: var(--gold);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}
.survey-head h1 {
  font-size: 28px;
}
.survey-head .muted {
  margin: 8px 0 0;
}
.steps {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
  max-width: 430px;
}
.step {
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-muted);
  font-size: 12.5px;
  padding: 7px 10px;
}
.step.active {
  border-color: rgba(231, 178, 60, 0.55);
  color: var(--gold);
}
.survey-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.survey-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px;
  min-height: 180px;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.section-head h2 {
  font-size: 17px;
}
.required,
.optional {
  font-size: 12px;
  font-weight: 700;
}
.required {
  color: var(--gold);
}
.optional {
  color: var(--text-dim);
}
.asset-input {
  display: grid;
  grid-template-columns: 1fr 130px;
  gap: 10px;
  align-items: center;
}
.asset-input span {
  color: var(--text-muted);
  font-size: 13px;
  text-align: right;
}
.choice-grid {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}
.choice-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.choice-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.choice-grid.wrap,
.choice-grid.sectors {
  grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
}
.choice-stack {
  display: grid;
  gap: 10px;
}
.choice {
  min-height: 42px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  padding: 10px 12px;
  font-size: 14px;
  font-weight: 600;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.choice:hover {
  background: var(--surface-2);
  color: var(--text);
}
.choice.selected {
  border-color: var(--gold);
  background: rgba(231, 178, 60, 0.1);
  color: var(--gold);
}
.risk-choice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
}
.risk-choice span {
  color: var(--text-dim);
  font-size: 12.5px;
  font-weight: 500;
}
.full {
  grid-column: 1 / -1;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}
@media (max-width: 820px) {
  .survey-head,
  .actions {
    flex-direction: column;
    align-items: stretch;
  }
  .steps {
    justify-content: flex-start;
  }
  .survey-grid {
    grid-template-columns: 1fr;
  }
  .asset-input {
    grid-template-columns: 1fr;
  }
  .asset-input span {
    text-align: left;
  }
}
</style>
