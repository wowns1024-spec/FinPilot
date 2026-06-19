import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { setAuthExpiredHandler } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Refresh Token 만료 시 강제 로그아웃 후 로그인 화면으로
const auth = useAuthStore(pinia)
setAuthExpiredHandler(() => {
  auth.clear()
  router.push({ name: 'login' })
})

app.mount('#app')
