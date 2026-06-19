<script setup>
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <div class="container coming">
    <div class="card box">
      <h1>{{ route.meta.title || '준비 중' }}</h1>
      <p class="muted">이 기능은 현재 준비 중입니다.</p>
    </div>
  </div>
</template>

<style scoped>
.coming {
  padding: 80px 24px;
  display: flex;
  justify-content: center;
}
.box {
  text-align: center;
  padding: 56px 48px;
  max-width: 480px;
}
.box h1 {
  font-size: 24px;
  margin-bottom: 12px;
}
</style>
