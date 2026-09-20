# Technology Stack

## Recommended Stack

### 1. Web Automation & Scraping
- **Playwright for Python (`playwright>=1.42.0`)**
  - **Rationale**: 대학 포털 및 LMS(Canvas, Moodle, KAU LXP)는 동적 자바스크립트(SPA/Vue/React) 및 비동기 XHR 호출이 많아 단순 requests/BeautifulSoup만으로는 렌더링 후 DOM 파싱이 어렵습니다. Playwright는 Chromium 기반의 강력한 헤드리스 브라우저 엔진을 제공하며, 네트워크 유휴 대기(`networkidle`), 선택자 자동 대기, 브라우저 세션(쿠키 및 `storage_state`) 저장을 기본 지원하여 로그인 세션을 안전하게 재사용할 수 있습니다.
  - **대안 비교**: Selenium은 설정이 무겁고 드라이버 관리가 번거로움; Requests/HTTP 세션은 SSO 및 JS 렌더링 페이지 대응에 한계가 있음.

### 2. Notion Integration
- **`notion-client>=2.2.1` (Python SDK)** & **Notion MCP Server**
  - **Rationale**: 에이전트 환경 내에서 Notion MCP를 직접 호출할 수도 있고, 독립적인 Python CLI 스크립트 실행 시 `notion-client` 공식 SDK를 통해 안정적으로 Notion API v1을 호출할 수 있습니다.
  - **데이터베이스 필드 연동**:
    - `이름` (title): `[{과목약어}] {주차}주차 {강의명} 수강`
    - `선택` (select): `루틴` (인강) / `이벤트` (과제)
    - `구분` (multi_select): `["학업"]`, `["학업", "과제"]`, 과목명 태그
    - `DueDate` (date): `YYYY-MM-DD` 또는 ISO-8601 Datetime (KST)
    - `우선순위` (select): `🔴 긴급 (P1)` (마감 24시간 이내), `🟡 중요 (P2)` (마감 3일 이내), `🔵 보통 (P3)` (기본)
    - `상태` (status): `시작 전`
    - `메모` (rich_text): 강의/과제 상세 링크 및 설명

### 3. Config & Validation
- **`python-dotenv>=1.0.0` & `pydantic>=2.6.0`**
  - **Rationale**: 학교 LMS 접속 URL, 학번, 비밀번호, 노션 API 토큰 및 데이터베이스 ID(`21d53280-64be-80ec-af4e-000b679f03bb`)를 `.env` 파일과 타입 검증 모델로 안전하게 관리.

### 4. CLI & Formatting
- **`rich>=13.7.0` & `click>=8.1.0`**
  - **Rationale**: 에이전트 채팅 대화창 및 터미널 출력 시 수강 진행 현황, 미제출 과제, 마감 임박 알림을 직관적인 표(Table)와 색상 하이라이트로 렌더링.

### 5. Date Parsing
- **`python-dateutil>=2.9.0` & `pytz`**
  - **Rationale**: 한국 대학 사이트의 다양한 날짜/시간 표기(`2026.09.21 23:59`, `~ 09/21 23:59:00` 등)를 한국 표준시(KST, UTC+9) 기준으로 정확하게 파싱하여 Notion ISO 8601 포맷으로 변환.

## What NOT to Use
- **Selenium**: 브라우저 드라이버 바이너리 불일치 문제 및 느린 실행 속도로 인해 제외.
- **순수 HTTP Requests/Scrapy**: 학교 사이트의 세션 인증 흐름 및 동적 렌더링(Canvas/LXP) 시 파싱 실패율이 높아 메인 크롤러로 부적합.
