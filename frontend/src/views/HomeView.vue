<script setup>
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const { isAuthenticated } = storeToRefs(auth)
</script>

<template>
  <section class="hero">
    <div class="container hero-inner">
      <div class="hero-copy">
        <h1 class="hero-title">
          나에게 딱 맞는<br />
          주식 추천, <span class="text-gold">FinPick</span>
        </h1>
        <p class="hero-sub">
          AI와 데이터로 당신의 투자 성향을 분석해<br />
          지금, 맞춤형 종목 추천을 경험해보세요.
        </p>
        <RouterLink
          :to="isAuthenticated ? '/recommend' : '/signup'"
          class="btn btn-primary hero-cta"
        >
          AI 종목 추천 받기 →
        </RouterLink>
      </div>
    </div>
  </section>

  <section class="container info-section">
    <div class="info-grid">
      <div class="card info-card">
        <h3>인기 섹터 TOP 3</h3>
        <p class="muted small">시장 분석 기능은 준비 중입니다. (F700)</p>
      </div>
      <div class="card info-card">
        <h3>주요 뉴스</h3>
        <p class="muted small">뉴스 기능은 준비 중입니다. (F500)</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  border-bottom: 1px solid var(--border);
  background: radial-gradient(
    1200px 400px at 70% -10%,
    rgba(231, 178, 60, 0.12),
    transparent 60%
  );
}
.hero-inner {
  padding: 88px 24px;
}
.hero-copy {
  max-width: 560px;
}
.hero-title {
  font-size: 44px;
  line-height: 1.2;
}
.hero-sub {
  color: var(--text-muted);
  margin: 20px 0 32px;
  font-size: 16px;
}
.hero-cta {
  font-size: 16px;
  padding: 13px 22px;
}
.info-section {
  padding: 40px 24px 56px;
}
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.info-card {
  padding: 24px;
}
.info-card h3 {
  font-size: 16px;
  margin-bottom: 10px;
}
.small {
  font-size: 13px;
}
@media (max-width: 760px) {
  .hero-title {
    font-size: 32px;
  }
  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
