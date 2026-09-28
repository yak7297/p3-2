# 학습시간 데이터 AI 비서

학습시간 시계열 데이터를 추가·수정·삭제하고, 요약 정보를 바탕으로 AI와 대화하는 과제용 애플리케이션입니다.

## 현재 구현된 기능

- 데이터 CRUD 및 기간/개수/평균/최대/최소/최근 추세 요약
- 대화 자동 저장, 목록 조회, 전체 메시지 불러오기, 삭제
- 요약 정보를 시스템 지침에 넣는 OpenAI 호환 Chat Completions API 채팅
- 개발 중 토큰을 전혀 사용하지 않는 `AI_MODE=mock`
- 로컬 JSON 저장과 Firestore 저장 모드
- FastAPI Swagger UI와 바닐라 HTML/CSS/JavaScript 화면

## 토큰 절약 원칙

- 120개 원본 데이터와 메모는 GPT에 보내지 않고 작은 요약 JSON만 전송
- 최근 메시지 4개만 전송하고 각 메시지를 500자로 제한
- 질문을 500자로 제한하고 출력은 기본 220토큰으로 제한
- 출력은 기본 220토큰으로 제한
- 개발과 화면 확인은 mock 모드로 진행하고 마지막 실제 확인만 OpenAI 모드 사용

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

## 배포 전 남은 작업

- Vercel에 프론트 배포 및 화면 확인
- README에 배포 URL과 제출 스크린샷 추가

## 배포 주소

- GitHub: https://github.com/yak7297/p3-2
- 백엔드 API: https://p3-2-backend.onrender.com
- Swagger UI: https://p3-2-backend.onrender.com/docs
- 프론트엔드: Vercel 배포 후 추가

## Vercel 환경 변수

Vercel 프로젝트의 Root Directory를 `frontend`로 지정하고 아래 환경변수를 등록합니다.

```dotenv
API_BASE_URL=https://p3-2-backend.onrender.com
```

빌드 과정에서 이 값으로 `dist/config.js`를 만들며, 브라우저에는 API 키나 Firebase 서비스 계정 키가 포함되지 않습니다.
