<script setup>
import { reactive, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const form = reactive({
  username: '',
  password: '',
  password_confirm: '',
  email: '',
  birth_date: '',
})

const errors = reactive({})
const formError = ref('')
const submitting = ref(false)

const showPw = ref(false)
const showPwConfirm = ref(false)

// F102 아이디 중복 확인 상태
const usernameCheck = ref(null) // { available, message }
const checking = ref(false)

async function onCheckUsername() {
  errors.username = ''
  usernameCheck.value = null
  if (!form.username.trim()) {
    errors.username = '아이디를 입력해 주세요.'
    return
  }
  checking.value = true
  try {
    usernameCheck.value = await auth.checkUsername(form.username.trim())
  } catch {
    errors.username = '중복 확인 중 오류가 발생했습니다.'
  } finally {
    checking.value = false
  }
}

function clearFieldError(field) {
  errors[field] = ''
  formError.value = ''
  if (field === 'username') usernameCheck.value = null
}

async function onSubmit() {
  Object.keys(errors).forEach((k) => (errors[k] = ''))
  formError.value = ''
  submitting.value = true
  try {
    await auth.signup({ ...form, username: form.username.trim() })
    router.push('/mypage')
  } catch (e) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      let mapped = false
      for (const [key, val] of Object.entries(data)) {
        const msg = Array.isArray(val) ? val.join(' ') : String(val)
        if (key in form) {
          errors[key] = msg
          mapped = true
        } else {
          formError.value = msg
        }
      }
      if (!mapped && !formError.value) formError.value = '회원가입에 실패했습니다.'
    } else {
      formError.value = '회원가입에 실패했습니다. 잠시 후 다시 시도해 주세요.'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card card">
      <h1 class="auth-title">회원가입</h1>
      <p class="auth-sub">FinPick과 함께 현명한 투자를 시작하세요.</p>

      <p v-if="formError" class="form-error">{{ formError }}</p>

      <form @submit.prevent="onSubmit" novalidate>
        <!-- 아이디 + 중복확인 -->
        <div class="field">
          <label for="username">아이디</label>
          <div class="input-group">
            <input
              id="username"
              v-model="form.username"
              class="input"
              type="text"
              placeholder="아이디를 입력해주세요"
              autocomplete="username"
              @input="clearFieldError('username')"
            />
            <button
              type="button"
              class="btn btn-ghost"
              :disabled="checking"
              @click="onCheckUsername"
            >
              {{ checking ? '확인 중' : '중복확인' }}
            </button>
          </div>
          <p v-if="errors.username" class="field-error">{{ errors.username }}</p>
          <p
            v-else-if="usernameCheck"
            :class="usernameCheck.available ? 'field-ok' : 'field-error'"
          >
            {{ usernameCheck.message }}
          </p>
        </div>

        <!-- 비밀번호 -->
        <div class="field">
          <label for="password">비밀번호</label>
          <div class="input-affix">
            <input
              id="password"
              v-model="form.password"
              class="input"
              :type="showPw ? 'text' : 'password'"
              placeholder="비밀번호를 입력해주세요"
              autocomplete="new-password"
              @input="clearFieldError('password')"
            />
            <button type="button" class="toggle-eye" @click="showPw = !showPw">
              {{ showPw ? '🙈' : '👁' }}
            </button>
          </div>
          <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
        </div>

        <!-- 비밀번호 확인 -->
        <div class="field">
          <label for="password_confirm">비밀번호 확인</label>
          <div class="input-affix">
            <input
              id="password_confirm"
              v-model="form.password_confirm"
              class="input"
              :type="showPwConfirm ? 'text' : 'password'"
              placeholder="비밀번호를 다시 입력해주세요"
              autocomplete="new-password"
              @input="clearFieldError('password_confirm')"
            />
            <button
              type="button"
              class="toggle-eye"
              @click="showPwConfirm = !showPwConfirm"
            >
              {{ showPwConfirm ? '🙈' : '👁' }}
            </button>
          </div>
          <p v-if="errors.password_confirm" class="field-error">
            {{ errors.password_confirm }}
          </p>
        </div>

        <!-- 이메일 -->
        <div class="field">
          <label for="email">이메일</label>
          <input
            id="email"
            v-model="form.email"
            class="input"
            type="email"
            placeholder="이메일을 입력해주세요"
            autocomplete="email"
            @input="clearFieldError('email')"
          />
          <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
        </div>

        <!-- 생년월일 -->
        <div class="field">
          <label for="birth_date">생년월일</label>
          <input
            id="birth_date"
            v-model="form.birth_date"
            class="input"
            type="date"
            @input="clearFieldError('birth_date')"
          />
          <p v-if="errors.birth_date" class="field-error">{{ errors.birth_date }}</p>
        </div>

        <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">
          {{ submitting ? '처리 중...' : '회원가입' }}
        </button>
      </form>

      <p class="auth-foot">
        이미 계정이 있으신가요?
        <RouterLink to="/login" class="text-gold">로그인</RouterLink>
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
  max-width: 440px;
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
.auth-foot {
  text-align: center;
  margin: 22px 0 0;
  font-size: 14px;
  color: var(--text-muted);
}
</style>
