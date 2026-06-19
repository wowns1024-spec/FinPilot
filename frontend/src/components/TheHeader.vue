<script setup>
import { RouterLink, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const { isAuthenticated } = storeToRefs(auth)
const router = useRouter()

const navItems = [
  { label: '홈', to: '/' },
  { label: 'AI 추천', to: '/recommend' },
  { label: '종목조회', to: '/stocks' },
  { label: '뉴스', to: '/news' },
  { label: '주식용어', to: '/terms' },
]

async function onLogout() {
  await auth.logout()
  router.push('/')
}
</script>

<template>
  <header class="header">
    <div class="container header-inner">
      <RouterLink to="/" class="logo">Fin<span>Pick</span></RouterLink>

      <nav class="nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="auth-area">
        <template v-if="isAuthenticated">
          <RouterLink to="/mypage" class="nav-link">마이페이지</RouterLink>
          <button class="btn btn-ghost btn-sm" @click="onLogout">로그아웃</button>
        </template>
        <template v-else>
          <RouterLink to="/login" class="nav-link">로그인</RouterLink>
          <RouterLink to="/signup" class="btn btn-primary btn-sm">회원가입</RouterLink>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(11, 13, 16, 0.85);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
}
.header-inner {
  display: flex;
  align-items: center;
  height: 64px;
  gap: 28px;
}
.logo {
  font-size: 21px;
  font-weight: 800;
  letter-spacing: -0.02em;
}
.logo span {
  color: var(--gold);
}
.nav {
  display: flex;
  gap: 8px;
  flex: 1;
  justify-content: center;
}
.nav-link {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14.5px;
  font-weight: 500;
  color: var(--text-muted);
  transition: color 0.15s, background 0.15s;
}
.nav-link:hover {
  color: var(--text);
  background: var(--surface-2);
}
.nav-link.router-link-exact-active {
  color: var(--gold);
}
.auth-area {
  display: flex;
  align-items: center;
  gap: 10px;
}
.btn-sm {
  padding: 8px 14px;
  font-size: 14px;
}
@media (max-width: 760px) {
  .nav {
    display: none;
  }
}
</style>
