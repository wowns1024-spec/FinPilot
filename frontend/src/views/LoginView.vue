<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const REMEMBER_KEY = 'finpick_remember_username'

const form = reactive({ username: '', password: '' })
const remember = ref(false)
const showPw = ref(false)
const formError = ref('')
const submitting = ref(false)

onMounted(() => {
  const saved = localStorage.getItem(REMEMBER_KEY)
  if (saved) {
    form.username = saved
    remember.value = true
  }
})

async function onSubmit() {
  formError.value = ''
  if (!form.username.trim() || !form.password) {
    formError.value = '아이디와 비밀번호를 입력해 주세요.'
    return
  }
  submitting.value = true
  try {
    await auth.login({ username: form.username.trim(), password: form.password })
    if (remember.value) localStorage.setItem(REMEMBER_KEY, form.username.trim())
    else localStorage.removeItem(REMEMBER_KEY)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirect)
  } catch (e) {
    // F105: 계정 존재 여부를 노출하지 않는 공통 오류
    if (e.response?.status === 401) {
      formError.value = '아이디 또는 비밀번호가 올바르지 않습니다.'
    } else {
      formError.value = '로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card card">
      <h1 class="auth-title">로그인</h1>
      <p class="auth-sub">FinPick에 오신 것을 환영합니다.</p>

      <p v-if="formError" class="form-error">{{ formError }}</p>

      <form @submit.prevent="onSubmit" novalidate>
        <div class="field">
          <label for="username">아이디</label>
          <input
            id="username"
            v-model="form.username"
            class="input"
            type="text"
            placeholder="아이디를 입력해주세요"
            autocomplete="username"
          />
        </div>

        <div class="field">
          <label for="password">비밀번호</label>
          <div class="input-affix">
            <input
              id="password"
              v-model="form.password"
              class="input"
              :type="showPw ? 'text' : 'password'"
              placeholder="비밀번호를 입력해주세요"
              autocomplete="current-password"
            />
            <button type="button" class="toggle-eye" @click="showPw = !showPw">
              {{ showPw ? '🙈' : '👁' }}
            </button>
          </div>
        </div>

        <div class="login-options">
          <label class="remember">
            <input type="checkbox" v-model="remember" />
            <span>아이디 저장</span>
          </label>
          <span class="muted find-pw">비밀번호 찾기</span>
        </div>

        <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">
          {{ submitting ? '처리 중...' : '로그인' }}
        </button>
      </form>

      <p class="auth-foot">
        계정이 없으신가요?
        <RouterLink to="/signup" class="text-gold">회원가입</RouterLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding: 56px 24px;
}
.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 36px 32px;
}
.auth-title {
  text-align: center;
  font-size: 26px;
}
.auth-sub {
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
  margin: 8px 0 28px;
}
.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  font-size: 13.5px;
}
.remember {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-muted);
  cursor: pointer;
}
.remember input {
  accent-color: var(--gold);
}
.find-pw {
  cursor: default;
}
.auth-foot {
  text-align: center;
  margin: 22px 0 0;
  font-size: 14px;
  color: var(--text-muted);
}
</style>
