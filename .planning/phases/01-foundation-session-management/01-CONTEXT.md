# Phase 1: Foundation & Session Management - Context

**Gathered:** 2026-09-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1은 프로젝트의 기반 인프라를 구축합니다:
1. Python 프로젝트 환경 및 의존성 설정 (`pyproject.toml` + `uv`)
2. 안전한 환경변수 로딩 (`.env.example`, `config.py`)
3. 과목명 축약 매핑 로더 (`config/course_mappings.json`)
4. Playwright 기반 헤드리스 브라우저 구동 및 세션 캐시 관리자 (`session_manager.py`, `auth.py`)
5. 대학 LMS 자동 로그인 및 세션 유효성 판별

</domain>

<decisions>
## Implementation Decisions

### 1. LMS 접속 및 로그인 대상 (Login Target & Flow)
- **D-01:** LMS 로그인 URL은 `.env`의 `LMS_URL`에 지정된 커스텀 URL로 직접 접근하며, 환경변수로 유연하게 변경 가능하도록 구성. — **Reversibility:** reversible
- **D-02:** Python 프로젝트 패키징 및 의존성 관리는 `pyproject.toml` 및 `uv`를 기본 도구로 채택 (초고속 가상환경 생성 및 의존성 락 지원). — **Reversibility:** costly — 빌드 및 의존성 도구 변경 시 설정 마이그레이션 필요

### 2. 세션 캐싱 및 저장 정책 (Session Caching & Persistence)
- **D-03:** Playwright의 `storage_state` 파일은 `.cache/session.json`에 저장하고, `.gitignore`에 등록하여 개인정보/세션 쿠키가 Git에 커밋되지 않도록 격리. — **Reversibility:** reversible
- **D-04:** 세션 만료 판별은 대시보드 페이지 접근 시 로그인 URL로 리다이렉트되거나 세션 유효성 검증 셀렉터(프로필/로그아웃 버튼 등)가 존재하지 않을 때 만료로 판단하고, 즉시 자동 재로그인을 수행하여 새 세션을 획득 및 갱신. — **Reversibility:** reversible

### 3. 과목명 축약 매핑 방식 (Course Name Mapping)
- **D-05:** 과목명 축약 매핑은 `config/course_mappings.json` 독립 JSON 파일로 관리하여 사용자가 손쉽게 편집할 수 있도록 분리. (기본 샘플: `{"공학수학2": "공수2", "자료구조": "자구", "디지털시스템설계": "디시설"}`). — **Reversibility:** reversible
- **D-06:** 매핑 파일에 등록되지 않은 신규 과목이 감지될 경우, 파싱 에러를 발생시키지 않고 원본 과목명 그대로 사용하며, 사용자에게 축약어 등록을 권장하는 친절한 로그를 출력. — **Reversibility:** reversible

### 4. 브라우저 실행 환경 & 디버깅 (Browser Execution & Debugging)
- **D-07:** 브라우저는 기본적으로 Headless(백그라운드) 모드로 구동하되, 초기 로그인 셋업 및 디버깅을 위해 CLI 플래그(`--headful`) 및 환경변수(`HEADLESS=false`)로 브라우저 화면 표시 전환을 지원. — **Reversibility:** reversible
- **D-08:** 기본 페이지 로딩 및 네비게이션 타임아웃은 30초로 설정하며, 일시적 네트워크 오류나 페이지 지연 시 1회 자동 재시도 로직을 적용. — **Reversibility:** reversible

### the agent's Discretion
- 세부적인 Playwright 브라우저 컨텍스트 옵션(User-Agent, Viewport 등) 설정
- 로깅 포맷 및 콘솔 출력 메시지 스타일

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Roadmap Specs
- `.planning/PROJECT.md` — 프로젝트 개요, 핵심 가치, 시스템 제약 사항
- `.planning/REQUIREMENTS.md` — CONF-01, CONF-02, CONF-03, SCRP-01 요구사항 상세
- `.planning/ROADMAP.md` — Phase 1 목표, 성공 기준, 계획 분할 지침
- `.planning/research/STACK.md` — Playwright, Pydantic, uv 기술 스택 권장사항
- `.planning/research/PITFALLS.md` — 세션 만료, 로그인 리다이렉트, 타임아웃 방지 대책

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- 신규 프로젝트(Greenfield)로 기존 소스 코드가 없으나, GSD 도구 체인 및 `.planning/config.json` 설정이 완비되어 있음.

### Integration Points
- `.env` 및 `.cache/session.json`
- `config/course_mappings.json`
- 향후 Phase 2의 강좌 크롤러(`KauLxpScraper`)가 본 Phase 1의 `SessionManager` 및 `Auth` 모듈을 상속/주입받아 활용함.

</code_context>

<specifics>
## Specific Ideas

- 사용자의 노션 스케줄러에는 이미 `[공수2]`, `[자구]`, `[디시설]` 형태의 대괄호 축약어가 사용되고 있으므로 기본 매핑 파일에 이를 샘플로 등록해 둘 것.
- `.env.example`에 KAU e-Class/Canvas 사이트 주소 예시와 노션 DB ID(`21d53280-64be-80ec-af4e-000b679f03bb`)를 미리 기재하여 사용자의 설정을 도울 것.

</specifics>

<deferred>
## Deferred Ideas

- None — 모든 논의가 Phase 1 인프라 및 세션 관리 범위 내에서 진행됨.

</deferred>

---

*Phase: 1-Foundation & Session Management*
*Context gathered: 2026-09-21*
