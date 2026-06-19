<script setup></script>

<template>
  <footer class="footer">
    <div class="container">
      <p class="disclaimer">
        본 서비스가 제공하는 종목 추천, 추천 점수, AI 답변, 뉴스 및 시장 정보는 투자 판단을
        돕기 위한 참고 자료이며 특정 금융상품의 매수 또는 매도를 권유하지 않습니다. 투자
        결정과 그에 따른 손익의 책임은 사용자 본인에게 있습니다.
      </p>
      <p class="copyright">© 2026 FinPick</p>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  margin-top: auto;
  border-top: 1px solid var(--border);
  padding: 24px 0;
}
.disclaimer {
  margin: 0;
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.6;
}
.copyright {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--text-dim);
}
</style>
