# Phase 1: Foundation & Session Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-21
**Phase:** 1-Foundation & Session Management
**Areas discussed:** LMS 접속 및 로그인 대상, 프로젝트 환경 구성, 세션 캐싱 및 저장 정책, 과목명 축약 매핑 방식, 브라우저 실행 환경 & 디버깅

---

## 1. LMS 접속 및 로그인 대상 (Login Target & Flow)

| Option | Description | Selected |
|--------|-------------|----------|
| e-Class / LXP 직접 로그인 | Canvas 기반 URL로 직접 접근 | |
| 학교 종합정보 포털(SSO) 로그인 후 이동 | 포털 로그인 후 LXP 리다이렉트 | |
| .env에 지정한 커스텀 URL로 직접 접근 | 사용자가 환경변수로 자유롭게 지정 | ✓ |

**User's choice:** .env에 지정한 커스텀 URL로 직접 접근
**Notes:** 사용자별/학교별 URL 차이를 수용할 수 있도록 유연한 환경변수 설정 방식 채택

---

## 2. 프로젝트 환경 구성 (Environment Setup)

| Option | Description | Selected |
|--------|-------------|----------|
| requirements.txt + venv | 범용적이고 직관적 | |
| pyproject.toml + uv | 초고속 의존성 관리 및 최신 표준 | ✓ |
| Poetry | pyproject.toml 기반 의존성 락 관리 | |

**User's choice:** pyproject.toml + uv (초고속 의존성 관리 및 최신 표준)
**Notes:** 빠른 가상환경 생성 및 모던 파이썬 패키징 표준 준수

---

## 3. 세션 캐싱 및 저장 정책 (Session Caching & Persistence)

| Option | Description | Selected |
|--------|-------------|----------|
| .cache/session.json에 저장하고 .gitignore에 추가 | 캐시 디렉터리 분리 및 커밋 방지 | ✓ |
| data/session.json에 저장하고 .gitignore에 추가 | 데이터 디렉터리 분리 | |
| 프로젝트 루트의 session.json에 저장 | 루트 경로에 직접 저장 | |

**User's choice:** .cache/session.json에 저장하고 .gitignore에 추가하여 커밋 방지

---

## 4. 세션 만료 판별 및 갱신 방식

| Option | Description | Selected |
|--------|-------------|----------|
| 대시보드 접근 시 로그인 페이지로 리다이렉트되거나 세션 셀렉터 부재 시 자동 재로그인 | 상태 기반 동적 감지 및 자동 복구 | ✓ |
| 세션 파일 유효시간(예: 2시간) 기준 만료 판정 후 재로그인 | 시간 기반 만료 | |
| 재로그인 시도 없이 즉시 에러 발생 | 수동 재로그인 유도 | |

**User's choice:** 대시보드 접근 시 로그인 페이지로 리다이렉트되거나 세션 셀렉터 부재 시 자동 재로그인

---

## 5. 과목명 축약 매핑 방식 (Course Name Mapping)

| Option | Description | Selected |
|--------|-------------|----------|
| config/course_mappings.json 독립 파일로 관리 | 사용자가 직접 편집 용이 | ✓ |
| .env 파일 내에 JSON 문자열로 포함 | 단일 설정 파일 관리 | |

**User's choice:** config/course_mappings.json 독립 JSON 파일로 관리 (사용자가 직접 편집 용이)

---

## 6. 미등록 신규 과목 처리 룰

| Option | Description | Selected |
|--------|-------------|----------|
| 매핑이 없으면 원본 과목명 그대로 사용하되, 축약어 등록 권장 로그 출력 | 무중단 실행 및 안내 제공 | ✓ |
| 앞 2~4글자 자동 추출하여 임시 약칭 생성 | 자동 약칭 유추 | |
| 에러를 내고 실행 중단 | 매핑 강제 | |

**User's choice:** 매핑이 없으면 원본 과목명 그대로 사용하되, 사용자에게 축약어 등록을 권장하는 로그 출력

---

## 7. 브라우저 실행 모드 (Headless vs Headful)

| Option | Description | Selected |
|--------|-------------|----------|
| 기본 Headless 구동 + CLI 플래그(--headful) 및 .env(HEADLESS=false) 지원 | 백그라운드 기본 + 디버깅 유연성 | ✓ |
| 항상 완전한 Headless로만 구동 | 화면 표시 기능 제외 | |

**User's choice:** 기본 Headless 구동 + CLI 플래그(--headful) 및 .env(HEADLESS=false)로 브라우저 표시 전환 지원

---

## 8. 타임아웃 및 재시도 정책

| Option | Description | Selected |
|--------|-------------|----------|
| 기본 페이지 로딩 타임아웃 30초 + 로그인/네비게이션 실패 시 1회 자동 재시도 | 안정적인 재시도 | ✓ |
| 타임아웃 15초 + 재시도 없이 즉시 실패 리포트 | 빠른 실패 | |
| 타임아웃 60초 | 장기 대기 | |

**User's choice:** 기본 페이지 로딩 타임아웃 30초 + 로그인/네비게이션 실패 시 1회 자동 재시도

---

## the agent's Discretion

- Playwright 브라우저 컨텍스트 세부 옵션
- 로깅 레벨 및 터미널 출력 포맷

## Deferred Ideas

- None
