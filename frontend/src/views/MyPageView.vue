<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const { user } = storeToRefs(auth)
const router = useRouter()

const tabs = [
  { key: 'profile', label: '회원 정보' },
  { key: 'investment', label: '투자 성향' },
  { key: 'scraps', label: '스크랩 뉴스' },
]
const activeTab = ref('profile')

const loading = ref(true)
const editing = ref(false)
const submitting = ref(false)
const formError = ref('')
const errors = reactive({ email: '', current_password: '', new_password: '' })

const form = reactive({ email: '', current_password: '', new_password: '' })

const joinedDate = computed(() => {
  if (!user.value?.date_joined) return '-'
  return new Date(user.value.date_joined).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
})

onMounted(async () => {
  try {
    await auth.fetchMe()
  } catch {
    /* 401 은 인터셉터/가드가 처리 */
  } finally {
    loading.value = false
  }
})

function startEdit() {
  form.email = user.value?.email || ''
  form.current_password = ''
  form.new_password = ''
  Object.keys(errors).forEach((k) => (errors[k] = ''))
  formError.value = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function onSave() {
  Object.keys(errors).forEach((k) => (errors[k] = ''))
  formError.value = ''
  const payload = {}
  if (form.email && form.email !== user.value.email) payload.email = form.email
  if (form.new_password) {
    payload.current_password = form.current_password
    payload.new_password = form.new_password
  }
  if (Object.keys(payload).length === 0) {
    editing.value = false
    return
  }
  submitting.value = true
  try {
    await auth.updateMe(payload)
    editing.value = false
  } catch (e) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      for (const [key, val] of Object.entries(data)) {
        const msg = Array.isArray(val) ? val.join(' ') : String(val)
        if (key in errors) errors[key] = msg
        else formError.value = msg
      }
    } else {
      formError.value = '수정에 실패했습니다.'
    }
  } finally {
    submitting.value = false
  }
}

async function onLogout() {
  await auth.logout()
  router.push('/')
}
</script>

<template>
  <div class="container mypage">
    <div class="layout">
      <!-- 좌측 사이드바 -->
      <aside class="sidebar card">
        <p class="sidebar-title">마이 정보</p>
        <button
          v-for="t in tabs"
          :key="t.key"
          class="side-item"
          :class="{ active: activeTab === t.key }"
          @click="activeTab = t.key"
        >
          {{ t.label }}
        </button>
      </aside>

      <!-- 메인 영역 -->
      <section class="content">
        <template v-if="activeTab === 'profile'">
          <div class="card panel">
            <div class="panel-head">
              <h2>회원 정보</h2>
              <button v-if="!editing" class="btn btn-ghost btn-sm" @click="startEdit">
                수정하기
              </button>
            </div>

            <p v-if="loading" class="muted">불러오는 중...</p>

            <!-- 조회 모드 (F108) -->
            <dl v-else-if="!editing" class="info-list">
              <div class="info-row">
                <dt>아이디</dt>
                <dd>{{ user?.username }}</dd>
              </div>
              <div class="info-row">
                <dt>이메일</dt>
                <dd>{{ user?.email }}</dd>
              </div>
              <div class="info-row">
                <dt>생년월일</dt>
                <dd>{{ user?.birth_date || '-' }}</dd>
              </div>
              <div class="info-row">
                <dt>가입일</dt>
                <dd>{{ joinedDate }}</dd>
              </div>
            </dl>

            <!-- 수정 모드 (F109) -->
            <form v-else class="edit-form" @submit.prevent="onSave">
              <p v-if="formError" class="form-error">{{ formError }}</p>

              <div class="field">
                <label>아이디</label>
                <input class="input" :value="user?.username" disabled />
                <p class="field-hint">아이디는 변경할 수 없습니다.</p>
              </div>

              <div class="field">
                <label for="email">이메일</label>
                <input id="email" v-model="form.email" class="input" type="email" />
                <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
              </div>

              <div class="field">
                <label for="current_password">현재 비밀번호</label>
                <input
                  id="current_password"
                  v-model="form.current_password"
                  class="input"
                  type="password"
                  placeholder="비밀번호 변경 시에만 입력"
                  autocomplete="current-password"
                />
                <p v-if="errors.current_password" class="field-error">
                  {{ errors.current_password }}
                </p>
              </div>

              <div class="field">
                <label for="new_password">새 비밀번호</label>
                <input
                  id="new_password"
                  v-model="form.new_password"
                  class="input"
                  type="password"
                  placeholder="변경하지 않으려면 비워두세요"
                  autocomplete="new-password"
                />
                <p v-if="errors.new_password" class="field-error">
                  {{ errors.new_password }}
                </p>
              </div>

              <div class="edit-actions">
                <button type="button" class="btn btn-ghost" @click="cancelEdit">
                  취소
                </button>
                <button type="submit" class="btn btn-primary" :disabled="submitting">
                  {{ submitting ? '저장 중...' : '저장' }}
                </button>
              </div>
            </form>
          </div>
        </template>

        <!-- 투자 성향 (F200 예정) -->
        <div v-else-if="activeTab === 'investment'" class="card panel">
          <div class="panel-head"><h2>투자 성향 정보</h2></div>
          <div class="placeholder">
            <p class="muted">아직 투자 성향을 등록하지 않았습니다.</p>
            <p class="field-hint">투자 성향 설문 기능은 준비 중입니다. (F200)</p>
          </div>
        </div>

        <!-- 스크랩 뉴스 (F500 예정) -->
        <div v-else class="card panel">
          <div class="panel-head"><h2>스크랩 뉴스</h2></div>
          <div class="placeholder">
            <p class="muted">스크랩한 뉴스가 없습니다.</p>
            <p class="field-hint">뉴스 스크랩 기능은 준비 중입니다. (F500)</p>
          </div>
        </div>
      </section>

      <!-- 우측 프로필 카드 -->
      <aside class="profile card">
        <div class="avatar">👤</div>
        <p class="profile-name">{{ user?.username || 'FinPick 사용자' }}</p>
        <p class="profile-email muted">{{ user?.email }}</p>
        <button class="btn btn-ghost btn-block" @click="onLogout">로그아웃</button>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.mypage {
  padding: 40px 24px 56px;
}
.layout {
  display: grid;
  grid-template-columns: 200px 1fr 260px;
  gap: 20px;
  align-items: start;
}
.sidebar {
  padding: 16px;
}
.sidebar-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-dim);
  margin: 4px 8px 12px;
  letter-spacing: 0.04em;
}
.side-item {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  color: var(--text-muted);
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14.5px;
  font-weight: 500;
}
.side-item:hover {
  background: var(--surface-2);
  color: var(--text);
}
.side-item.active {
  background: var(--surface-3);
  color: var(--gold);
  font-weight: 600;
}
.panel {
  padding: 28px;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
}
.panel-head h2 {
  font-size: 18px;
}
.info-list {
  margin: 0;
}
.info-row {
  display: flex;
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
}
.info-row:last-child {
  border-bottom: none;
}
.info-row dt {
  width: 120px;
  color: var(--text-muted);
  font-size: 14px;
}
.info-row dd {
  margin: 0;
  font-weight: 500;
}
.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
.placeholder {
  padding: 24px 0;
}
.profile {
  padding: 28px 22px;
  text-align: center;
}
.avatar {
  width: 72px;
  height: 72px;
  margin: 0 auto 14px;
  border-radius: 50%;
  background: var(--surface-3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
}
.profile-name {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 4px;
}
.profile-email {
  font-size: 13px;
  margin: 0 0 18px;
  word-break: break-all;
}
@media (max-width: 920px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
