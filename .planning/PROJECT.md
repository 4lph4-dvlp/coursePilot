# KAU LXP Assistant & Notion Scheduler Sync Skill

## What This Is

대학 온라인 학습 플랫폼(한국항공대 LXP / 표준 Canvas·Moodle 기반 LMS)에 학생 로그인 정보를 통해 자동으로 로그인하여, 수강 중인 모든 강의의 주차별 온라인 강의 수강 여부 및 과제 제출 여부, 마감 기한을 추출하는 AI 에이전트 Skill입니다. 
추출된 데이터는 에이전트와의 채팅창 브리핑 리포트로 제공되며, 학생의 기존 Notion `Scheduler` 데이터베이스에 통일된 네이밍 규칙으로 중복 없이 자동 동기화됩니다.

## Core Value

학생이 수강 중인 모든 강의의 미완료 인강 및 과제 마감 기한을 빠짐없이 확인하고, 중복 없이 정형화된 이름 규칙으로 개인 노션 스케줄러에 동기화하여 학업 누락을 원천 방지하는 것.

## Requirements

### Validated

- ✓ `.env` 또는 설정 파일을 통한 LMS 접속 정보(URL, ID, PW) 및 노션 설정 안전 관리 — Phase 1
- ✓ Python + Playwright 기반 헤드리스 브라우저를 통한 LMS 자동 로그인 및 세션 관리 — Phase 1
- ✓ 수강 중인 전체 과목 목록 및 주차별 강의 수강 상태(진행도, 마감일) 파싱 — Phase 2
- ✓ 각 과목별 과제 목록 및 제출 여부, 제출 마감일 파싱 — Phase 2
- ✓ 24시간 이내 마감 임박 항목 감지 및 우선순위/경고 리포트 기능 — Phase 3
- ✓ 통일화된 작업 이름 규칙(예: `[{과목약어}] {N}주차 강의 시청`, `[{과목약어}] {과제명} 제출`) 및 노션 속성(`선택`=루틴/이벤트, `구분`=학업, `DueDate`, `우선순위`, `상태`=시작 전) 자동 매핑 — Phase 3
- ✓ Notion `Scheduler` 연동, 정규화 제목 기반 기등록 항목 중복 방지, 보호 필드 보존 및 실데이터 읽기/쓰기 0건 드라이런 — Phase 4

### Active

- [ ] 에이전트 채팅 대화창을 통한 미완료 항목 및 마감일 요약 브리핑 리포트 출력
- [ ] 범용 Agent Skill 패키징(에이전트 중립 `SKILL.md`, 에이전트별 설치 명령·안내, 의존성 가이드) — Antigravity 전용이 아닌 모든 SKILL.md 지원 에이전트 대상

### Out of Scope

- 자동 강의 재생/출석 대리 처리 — 대학 학칙 및 부정행위 방지를 위해 상태 조회 및 마감일 알림만 지원
- 2차 인증(OTP/캡차) 자동 우회 — 일반 ID/PW 로그인 기반 지원 (추후 필요시 수동 세션 쿠키 주입 방식 고려)
- 다중 사용자 SaaS 호스팅 — 학생 로컬 환경에서 에이전트가 직접 실행하는 단일 사용자 스킬 형태로 설계

## Context

- **대상 플랫폼**: 한국항공대 LXP 및 Canvas/Moodle 표준 LMS 구조 대응
- **Notion 데이터베이스**: `Scheduler` (database container: `21d53280-64be-80e9-827a-e6fd0f85499a`, data source: `21d53280-64be-80ec-af4e-000b679f03bb`)
  - 필드: `이름`(Title), `선택`(Select: 루틴/이벤트), `구분`(Multi-select: 학업 등), `DueDate`(Date), `Plan`(Date), `우선순위`(Select: 🔴 긴급 (P1)/🟡 중요 (P2)/🔵 보통 (P3)/⚪ 낮음 (P4)), `상태`(Status: 시작 전/진행 중/완료/폐기), `메모`(Text)
  - 기존 네이밍 관례: `[공수2] 3주차 강의 시청`, `[자구] 3주차 강의 시청`, `[디시설] 2주차 개념 강의 정리` 등 `[{과목약어}] ...` 브래킷 표기법 준수
- **동작 방식**: 에이전트 스킬 호출 시 Python 스크립트를 헤드리스로 구동하여 스크래핑 후 JSON 결과 반환 및 노션 동기화

## Constraints

- **Tech Stack**: Python 3.10+, Playwright, Notion API / Notion MCP
- **보안**: 계정 정보 및 API 키는 코드에 하드코딩하지 않고 `.env` 파일로 격리
- **중복 방지**: 정규화된 작업 제목을 단독 식별자로 사용하며, 같은 제목의 기존 페이지가 있으면 마감일 변경도 새 페이지 대신 해당 페이지의 허용 필드만 갱신

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Playwright 헤드리스 브라우저 사용 | SPA 및 자바스크립트 렌더링 기반 대학 LMS의 동적 요소를 안정적으로 크롤링하기 위함 | ✓ Validated (Phase 1, 2) |
| 기존 Notion Scheduler DB 스키마 직접 준수 | 사용자가 이미 사용하는 스케줄러 환경에 자연스럽게 통합되어 추가 마이그레이션이 불필요함 | ✓ Validated (Phase 4) |
| 과목명 약칭 매핑 테이블 적용 | 노션의 기존 네이밍 스타일(`[공수2]`, `[자구]`)을 그대로 유지하기 위함 | ✓ Validated (Phase 1, 3) |
| 순수 도메인 계층 격리 (Pure Domain Layer) | I/O(Playwright, Notion API) 없는 결정론적 테스트 및 빠른 단위 테스트 보장 | ✓ Implemented (Phase 3) |
| 24시간 긴급도 우선순위 사다리 (P1~P4) | 마감 24시간 이내 미완료 항목은 P1, 지연 항목은 P4로 자동 분류 | ✓ Implemented (Phase 3) |
| Notion 2000자 제한 방어 메모 절삭 | 과제 설명문 1500자 초과 시 절삭, 전체 메모 1950자 상한 하드캡 적용 | ✓ Implemented (Phase 3) |
| 데이터베이스 컨테이너와 데이터 소스 ID 분리 | 검색·스키마·쿼리 API가 요구하는 대상이 서로 달라 잘못된 대상 선택을 방지 | ✓ Validated (Phase 4) |
| SDK 429 재시도와 읽기 전용 529 재시도 분리 | 재시도 중첩과 결과가 불확실한 쓰기 요청의 재실행을 방지 | ✓ Validated (Phase 4) |
| 정규화 제목 단독 중복 식별 | 마감일 변경 시 중복 페이지 생성 대신 기존 페이지를 한 번만 갱신 | ✓ Validated (Phase 4) |
| `DueDate`·`우선순위`·`메모`만 부분 갱신 | 사용자가 관리하는 `상태`와 `Plan`을 동기화가 덮어쓰지 않도록 보존 | ✓ Validated (Phase 4) |
| 우선순위 라벨 API 경계 변환 | 도메인은 P1~P4를 유지하면서 기존 Scheduler의 장식된 한글 옵션을 그대로 사용 | ✓ Validated (Phase 4) |
| 실데이터 읽기 후 쓰기 차단 드라이런 | 미리보기와 실동기화가 동일한 판단 경로를 쓰되 생성·수정 호출은 기계적으로 0건 보장 | ✓ Validated (Phase 4) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-22 after Phase 4*
