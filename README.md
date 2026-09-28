# 학습시간 데이터 AI 비서

학습시간 시계열 데이터를 추가·수정·삭제하고, 요약 정보를 바탕으로 AI와 대화하는 과제용 애플리케이션입니다.

## 기술 스택

- 백엔드: Python, FastAPI, Uvicorn, Pydantic
- 데이터베이스: Firebase Cloud Firestore
- AI: OpenAI Python SDK, Codyssey OpenAI 호환 API
- 프론트엔드: HTML, CSS, JavaScript
- 배포: Render, Vercel

## 현재 구현된 기능

- 데이터 CRUD 및 기간/개수/평균/최대/최소/최근 추세 요약
- 대화 자동 저장, 목록 조회, 전체 메시지 불러오기, 삭제
- 요약 정보를 시스템 지침에 넣는 OpenAI 호환 Chat Completions API 채팅
- 개발 중 토큰을 전혀 사용하지 않는 `AI_MODE=mock`
- 로컬 JSON 저장과 Firestore 저장 모드
- FastAPI Swagger UI와 바닐라 HTML/CSS/JavaScript 화면

## 아키텍처와 파일별 책임

프론트엔드와 백엔드를 분리해 화면 변경, API 처리, 분석 방식, 저장소 교체가 서로에게 미치는 영향을 줄였습니다.

| 위치 | 책임 |
|---|---|
| `frontend/index.html`, `styles.css` | 화면 구조와 반응형 레이아웃 |
| `frontend/app.js` | 화면 상태, API 요청, CRUD 및 대화 불러오기 |
| `backend/main.py` | FastAPI 앱 초기화, CORS, 라우터와 정적 파일 연결 |
| `backend/app/routes.py` | HTTP 엔드포인트, 요청 흐름, 상태 코드와 대화 저장 시점 |
| `backend/app/models.py` | Pydantic 요청 스키마와 입력 검증 |
| `backend/app/services.py` | 데이터 요약과 AI 요청 구성 |
| `backend/app/storage.py` | 로컬 JSON/Firestore 저장소 구현과 선택 |
| `backend/app/config.py` | `.env` 및 실행 환경변수 읽기 |

화면의 기본 흐름은 `초기화 → /health 확인 → 데이터·대화 목록 조회 → 사용자 요청 → FastAPI 검증 → 서비스 처리 → Firestore 저장 → 화면 갱신` 순서입니다. 오류가 발생하면 API의 `detail` 메시지를 화면 상단에 표시하며, AI 요청 중에는 중복 전송을 막습니다.

## Firestore 컬렉션 설계

문서 ID는 Firestore가 자동 생성합니다. 현재 구현은 컬렉션 전체를 읽은 뒤 애플리케이션에서 정렬하므로 별도의 복합 색인이 필요하지 않습니다.

### `data` 컬렉션

```json
{
  "date": "2026-09-28",
  "value": 80,
  "memo": "테스트"
}
```

- `date`: 학습 날짜(`YYYY-MM-DD`)
- `value`: 하루의 학습시간(분), 0~1440
- `memo`: 선택 메모, 최대 300자

데이터 관리 화면에서 기록을 추가하면 이 컬렉션에 문서가 생성되고, `/api/data/summary`와 다음 AI 답변에 즉시 반영됩니다.

### `conversations` 컬렉션

```json
{
  "title": "현재 평균 학습시간과 최근 추세를 알려줘",
  "messages": [
    {"role": "user", "content": "현재 평균 학습시간을 알려줘"},
    {"role": "assistant", "content": "현재 평균 학습시간은 64.6분입니다."}
  ],
  "updated_at": "2026-09-28T10:28:42+00:00"
}
```

- 새 질문의 AI 답변 생성이 성공한 직후 사용자 메시지와 답변을 함께 저장합니다.
- 기존 `conversation_id`가 있으면 같은 문서를 갱신하고, 없으면 새 문서를 만듭니다.
- 목록 API에서는 전송량을 줄이기 위해 `messages`를 제외하고, 항목을 선택했을 때 전체 대화를 불러옵니다.

## 토큰 절약 원칙

- 120개 원본 데이터와 메모는 GPT에 보내지 않고 작은 요약 JSON만 전송
- 최근 메시지 4개만 전송하고 각 메시지를 500자로 제한
- 질문을 500자로 제한하고 출력은 기본 220토큰으로 제한
- 개발과 화면 확인은 mock 모드로 진행하고 마지막 실제 확인만 OpenAI 모드 사용

## AI 컨텍스트 주입 방식

`backend/app/services.py`의 `answer()`가 고정된 시스템 지침에 `_compact_summary()` 결과를 JSON으로 넣습니다. 원본 학습 기록과 메모는 보내지 않으며, 대화 문맥도 최근 메시지 4개만 각각 500자로 잘라 전달합니다.

- 기대효과: 답변을 실제 요약 수치에 근거시키고 토큰 비용과 개인정보 노출 범위를 줄입니다.
- 유효범위: 기간, 개수, 합계·평균·최대·최소, 최고 학습일, 최근 추세처럼 요약에 포함된 정보입니다.
- 한계: 요약에서 제외된 특정 날짜의 상세 기록이나 원인은 판단할 수 없습니다. 시스템 지침에도 없는 정보는 모른다고 답하도록 지정했습니다.
- 안전성: API 키는 백엔드에만 저장하고, 사용자 메모 원문은 AI에 보내지 않습니다. 고정된 시스템 지침이 사용자 질문보다 먼저 전달되며 질문·대화 길이도 제한합니다. 다만 AI 답변은 참고용이므로 중요한 판단에는 원본 데이터를 다시 확인해야 합니다.

## 요약 기준과 변경 방법

요약 책임은 `backend/app/services.py`의 `summarize(rows)`에 있습니다. 현재 기준은 다음과 같습니다.

1. 같은 날짜의 여러 기록을 일별 합계로 묶습니다.
2. 최근 7개 기록일 평균과 그 직전 7개 기록일 평균을 비교합니다.
3. 변화율이 `5% 초과`면 증가, `-5% 미만`이면 감소, 그 사이는 유지입니다.
4. 기록일이 14개 미만이면 추세 판단을 보류합니다.

기간이나 임계값을 바꾸려면 `summarize()`의 `14`, `7`, `5` 기준을 수정합니다. 특정 기간만 분석하려면 `backend/app/routes.py`의 `data_summary()`에서 날짜로 행을 거른 뒤 `summarize()`에 전달하도록 확장할 수 있습니다. 요약 결과는 DB에 따로 저장하지 않고 `/api/data/summary` 호출과 채팅 요청 때마다 다시 계산하므로, 기준을 변경한 뒤 테스트하고 재배포하면 기존 데이터에도 새 기준이 즉시 적용됩니다.

요약 로직을 다른 프로젝트에서 재사용하거나 교체할 때는 `summarize()`와 AI용 `_compact_summary()`를 함께 변경하면 API·화면·AI가 같은 기준을 유지합니다.

## 로컬 실행

Python 3.10 이상이 필요합니다.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python seed.py
uvicorn main:app --reload
```

- 앱: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- 테스트: `pytest -q`

## 주요 API 사용 예시

학습 기록 추가:

```bash
curl -X POST http://127.0.0.1:8000/api/data \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-09-28","value":80,"memo":"FastAPI 공부"}'
```

`GET /api/data/summary` 응답 예시:

```json
{
  "period": "2026-05-01 ~ 2026-09-28",
  "count": 122,
  "unit": "분",
  "metrics": {"total": 7886, "average": 64.6, "max": 95, "min": 30},
  "best_day": {"date": "2026-09-28", "value": 110},
  "trend": "증가",
  "change_percent": 11.1,
  "trend_basis": "최근 7개 기록일과 직전 7개 기록일의 일별 합계 평균 비교"
}
```

검증에 실패하면 FastAPI가 `422`를 반환합니다. 예를 들어 `value`가 1440을 넘거나 날짜 형식이 잘못됐거나 정의되지 않은 필드를 추가하면 요청이 거절됩니다.

## 입력 검증과 보안

- Pydantic에서 알 수 없는 필드를 금지하고 문자열 양끝 공백을 제거합니다.
- 학습시간은 0~1440분, 메모는 300자, 질문은 500자, 메시지는 3000자로 제한합니다.
- 문서 ID는 영문자·숫자·밑줄·하이픈만 최대 128자까지 허용합니다.
- 역할 값은 `user` 또는 `assistant`만 허용하고 대화는 최대 50개 메시지로 제한합니다.
- 화면은 사용자·AI 문자열을 `innerHTML`이 아닌 `textContent`로 출력해 스크립트 실행을 막습니다.
- 특정 단어 블랙리스트는 정상 질문까지 차단할 수 있어 사용하지 않고, 구조·길이·역할 검증과 AI 시스템 지침으로 범위를 제한합니다.

## 실제 OpenAI 확인

`backend/.env`에서 아래 세 항목만 바꿉니다.

```dotenv
AI_MODE=openai
OPENAI_API_KEY=본인의_키
OPENAI_BASE_URL=https://copa.codyssey.kr/v1
OPENAI_MODEL=gpt-5.4-mini
```

API 키는 GitHub에 올리지 않습니다. 공식 OpenAI Python SDK가 환경변수의 키와 Codyssey의 OpenAI 호환 주소를 읽어 Chat Completions API를 호출합니다.

## Firestore 전환

Firebase에서 Firestore Database와 서비스 계정을 준비한 후 `backend/.env`를 바꿉니다.

```dotenv
STORAGE_BACKEND=firestore
FIREBASE_SERVICE_ACCOUNT_JSON={서비스 계정 JSON 전체}
```

로컬에서는 `GOOGLE_APPLICATION_CREDENTIALS=/절대/경로/service-account.json` 방식도 사용할 수 있습니다.

## 배포 주소

- GitHub: [https://github.com/yak7297/p3-2](https://github.com/yak7297/p3-2)
- 프론트엔드: [https://p3-2-frontend.vercel.app](https://p3-2-frontend.vercel.app)
- 백엔드 API: [https://p3-2-backend.onrender.com](https://p3-2-backend.onrender.com)
- Swagger UI: [https://p3-2-backend.onrender.com/docs](https://p3-2-backend.onrender.com/docs)

Render 무료 인스턴스는 사용하지 않을 때 정지되므로 첫 요청에 약 50초 이상 걸릴 수 있습니다. 첫 접속에서는 로딩이 끝날 때까지 기다린 뒤 실패하면 한 번 새로고침합니다. 운영 정책과 요금제가 허용한다면 외부 스케줄러로 `/health`를 주기적으로 호출하는 프리워밍을 고려할 수 있지만, 무료 서비스 정책을 우회하는 용도로 사용하지 않습니다.

## 환경 변수

백엔드 최소 환경변수는 다음과 같습니다. 실제 키와 서비스 계정 JSON은 GitHub에 올리지 않습니다.

```dotenv
STORAGE_BACKEND=firestore
AI_MODE=openai
OPENAI_API_KEY=본인의_키
OPENAI_BASE_URL=https://copa.codyssey.kr/v1
OPENAI_MODEL=gpt-5.4-mini
MAX_OUTPUT_TOKENS=220
FIREBASE_SERVICE_ACCOUNT_JSON={서비스 계정 JSON 전체}
ALLOWED_ORIGINS=https://p3-2-frontend.vercel.app
```

실행 환경(Render 등에 등록한 값 또는 셸 환경변수)이 `backend/.env`보다 우선합니다. Firebase 인증은 `FIREBASE_SERVICE_ACCOUNT_JSON`이 있으면 그 JSON을 우선 사용하고, 없으면 Application Default Credentials를 사용합니다. 로컬의 `GOOGLE_APPLICATION_CREDENTIALS`는 후자의 인증 파일 위치를 지정할 때 사용합니다.

`ALLOWED_ORIGINS`에는 실제 프론트 주소만 쉼표로 구분해 등록합니다. 운영 환경에서 `*`를 사용하지 않아 임의 사이트의 브라우저 요청을 허용하지 않습니다.

## Vercel 환경 변수

Vercel 프로젝트의 Root Directory를 `frontend`로 지정하고 아래 환경변수를 등록합니다.

```dotenv
API_BASE_URL=https://p3-2-backend.onrender.com
```

빌드 과정에서 이 값으로 `dist/config.js`를 만들며, 브라우저에는 API 키나 Firebase 서비스 계정 키가 포함되지 않습니다.

## 제출 스크린샷

아래 화면으로 필수 기능과 실제 배포 상태를 확인할 수 있습니다. API 키와 Firebase 서비스 계정 값은 포함하지 않았습니다.

### 데이터 요약 기반 AI 채팅

![데이터 요약과 AI 질문 및 답변](docs/screenshots/chat-summary.png)

### 데이터 관리 CRUD

![데이터 추가 후 목록과 요약 갱신](docs/screenshots/data-crud.png)

### 저장된 대화 목록

![저장된 대화 목록](docs/screenshots/conversation-history.png)

### 대화 기록 불러오기

![저장된 대화 불러오기](docs/screenshots/conversation-load.png)

### Firestore 데이터베이스 생성

![Cloud Firestore 데이터베이스](docs/screenshots/firestore.png)

### Render 백엔드 배포 성공

![Render FastAPI 백엔드 배포 성공](docs/screenshots/backend-deploy.png)

### Vercel 프론트엔드 배포 성공

![Vercel 프론트엔드 배포 성공](docs/screenshots/frontend-deploy.png)

### FastAPI Swagger API 문서

![FastAPI CRUD, 대화 기록, AI 채팅 API 문서](docs/screenshots/swagger-api.png)
