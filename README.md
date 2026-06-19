# F100 회원관리 기능 구현

FinPick(투자 성향 기반 맞춤형 주식 종목 추천 서비스)의 첫 기능인 **F100 회원관리**를
구현한 기록입니다. 회원가입, 로그인, 토큰 갱신, 로그아웃, 회원정보 조회·수정까지의
인증 흐름을 Django REST Framework와 Vue 3로 구현했습니다.

**기술 스택**
- 백엔드: Django, Django REST Framework, `djangorestframework-simplejwt`
- 프론트엔드: Vue 3, Vue Router, Pinia, Axios
- 인증: JWT (Access + Refresh Token)
- DB: SQLite (개발)

---

## 구현 내용

### 백엔드 API

| 기능 | Method | Endpoint |
|---|---|---|
| 아이디 중복확인 (F102) | GET | `/api/v1/accounts/check-username/?username=` |
| 회원가입 (F103) | POST | `/api/v1/accounts/signup/` |
| 로그인 (F105) | POST | `/api/v1/accounts/login/` |
| 토큰 갱신 (F106) | POST | `/api/v1/accounts/token/refresh/` |
| 로그아웃 (F107) | POST | `/api/v1/accounts/logout/` |
| 회원정보 조회·수정 (F108·F109) | GET/PATCH | `/api/v1/accounts/me/` |

- **회원가입**: 아이디 중복(대소문자 무관)·비밀번호 일치·비밀번호 정책·이메일 형식을
  검증하고, 비밀번호는 해시로 저장한다. 가입 성공 시 JWT를 발급해 바로 로그인 상태가 된다.
- **로그인 / 토큰 갱신**: 로그인 시 Access·Refresh 토큰을 발급하고, Access 만료 시
  Refresh로 재발급한다. 로그인 실패 메시지는 계정 존재 여부를 노출하지 않는 공통 오류로 처리한다.
- **로그아웃**: Refresh 토큰을 블랙리스트에 등록해 로그아웃 후 재사용을 차단한다.
- **회원정보 수정**: 비밀번호 변경 시 현재 비밀번호를 확인하고, 이메일은 본인을 제외한
  중복을 검증한다.

### 프론트엔드 화면

- **회원가입 / 로그인 / 마이페이지** 화면을 다크 + 골드 테마로 구현
- 로그인 상태에 따라 헤더가 `로그인·회원가입` ↔ `마이페이지·로그아웃`으로 전환
- Axios 인터셉터로 모든 요청에 토큰을 자동 첨부하고, 401 발생 시 Refresh 토큰으로
  자동 재발급 후 재시도
- 라우터 가드로 비로그인 사용자의 마이페이지 접근을 차단

---

## 모델 설계

회원 정보는 Django 기본 `auth.User` 대신 **커스텀 User 모델**(`accounts.User`)로 설계했다.

```python
class User(AbstractUser):
    email = models.EmailField("email address", unique=True)   # 이메일 중복 불가
    birth_date = models.DateField("생년월일", null=True, blank=True)

    @property
    def has_investment_profile(self) -> bool:
        # 투자성향(F200) 등록 여부 — 별도 모델과의 관계로 판단
        return hasattr(self, "investment_profile")
```

**설계 의도**
- `AbstractUser`를 상속해 username·password·date_joined 등 기본 인증 필드를 그대로 활용하면서,
  서비스에 필요한 `birth_date`(생년월일)와 `email` 유니크 제약만 추가했다.
- 투자성향 같은 부가 정보는 User에 직접 넣지 않고 별도 모델(F200, `InvestmentProfile`)과의
  1:1 관계로 분리해, User 모델은 인증 책임만 갖도록 했다.
- 프로젝트 초기에 커스텀 User로 전환해 두면 이후 필드 확장이 자유롭다.

---

## 어려웠던 점과 해결 방법

### 1. 이미 마이그레이션된 기본 User 모델
F100 구현 직전, 이미 Django 기본 `auth.User`가 마이그레이션되어 있었다.
커스텀 User 모델로 바꾸려면 충돌이 발생하는 상황이었다.
→ 사용자가 0명인 개발 초기였으므로 **개발 DB를 초기화하고 커스텀 User 기준으로
다시 마이그레이션**했다. 초기에 결정한 덕분에 비용 없이 전환할 수 있었다.

### 2. 로그아웃 후에도 토큰이 살아있는 문제
JWT는 기본적으로 서버에 상태를 저장하지 않아, 로그아웃해도 발급된 토큰은
만료 전까지 유효하다.
→ **`token_blacklist` 앱을 적용해 Refresh 토큰을 블랙리스트에 등록**하도록 했다.
로그아웃 후 해당 토큰으로 갱신을 시도하면 차단되는 것을 테스트로 확인했다.

### 3. 화면 전환 후 인증 상태가 끊기는 문제
SPA에서 새로고침이나 페이지 이동 시 토큰을 잃지 않아야 했다.
→ 토큰을 **localStorage에 저장**하고 Axios 요청 인터셉터에서 자동으로 첨부하도록 했다.
Access 만료 시에는 응답 인터셉터가 Refresh로 한 번 갱신한 뒤 원래 요청을 재시도한다.

---

## 느낀점

- **인증은 "성공 경로"보다 "실패·경계 경로"가 핵심**이었다. 로그인 성공보다 잘못된
  비밀번호, 만료된 토큰, 로그아웃 후 재사용 같은 경우를 어떻게 처리하느냐가 더 중요했다.
- **초반 결정의 무게를 체감했다.** User 모델처럼 나중에 바꾸기 어려운 선택은,
  사용자가 없는 초기에 미리 정해두는 것이 비용을 크게 줄여준다는 걸 직접 겪었다.
- **명세서를 코드 ID와 1:1로 연결**(F102, F103 …)해두니, 무엇을 구현했고 무엇이 남았는지
  추적하기가 훨씬 수월했다. 다음 기능부터도 이 방식을 유지할 생각이다.
- 작은 도구 문제(PDF 인코딩) 하나로도 작업이 멈출 수 있다는 점에서, 막혔을 때
  **방법을 바꿔보는 판단**의 중요성을 다시 느꼈다.

---

## 다음 단계

- F100 브라우저 E2E 검증 (가입 → 로그인 → 마이페이지 → 로그아웃)
- F200 투자성향 설문 구현
