# Phase 4: Notion Scheduler Integration & Deduplication - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-21
**Phase:** 04-notion-scheduler-integration-deduplication
**Areas discussed:** 중복 감지 및 동기화 정책, 드라이런 시뮬레이션 및 결과 모델, Notion API 연동 라이브러리 및 DB 자동 검색, 페이지 본문 블록 vs 메모 속성, 노션 미연동 사용자를 위한 독립 실행 및 안전 폴백

---

## 중복 감지 및 기존 페이지 동기화 정책 (Deduplication & Upsert Strategy)

| Option | Description | Selected |
|--------|-------------|:---:|
| 스마트 부분 업데이트 (Smart Upsert) | 제목 일치 시 마감일·메모·우선순위만 갱신, 사용자가 수정한 상태('완료', '진행 중') 및 Plan(계획일) 보존 | ✓ |
| 신규 항목만 등록 (Insert-only) | 이미 존재하는 경우 수정 없이 스킵 | |
| 전체 속성 덮어쓰기 (Full Overwrite) | 기존 페이지 발견 시 상태('시작 전')를 포함한 모든 속성 덮어쓰기 | |

**User's choice:** 스마트 부분 업데이트 (Smart Upsert)
**Notes:** 제목이 일치하는 기존 페이지가 있으면 마감일·메모·우선순위만 최신으로 갱신하되, 사용자가 노션에서 직접 변경한 '상태'('완료', '진행 중' 등)나 직접 입력한 'Plan'(계획일)은 덮어쓰지 않고 안전하게 보존하기로 확정.

---

## 중복 판별 고유 식별자 (Matching Key)

| Option | Description | Selected |
|--------|-------------|:---:|
| 정규화된 작업명(title) 기준 매칭 | [과목약어] N주차 과제명 제출 고유 제목으로 매칭. 기한 연장 시 중복 없이 갱신 | ✓ |
| 작업명 + 마감일 복합 매칭 | 분 단위까지 일치해야 기존 페이지로 판별 | |
| LMS 고유 ID 태깅 매칭 | 메모 하단에 숨김 식별자 기록하여 매칭 | |

**User's choice:** 정규화된 작업명(title) 기준 매칭
**Notes:** Phase 3의 통일 규칙으로 생성된 제목이 고유성을 보장하므로, 마감 기한이 변경되더라도 동일 작업으로 매칭되어 중복 생성을 원천 방지함.

---

## 노션 DB 조회 범위 (Query Window / Scope)

| Option | Description | Selected |
|--------|-------------|:---:|
| 최근 3개월 이내 DueDate 또는 미완료('상태' != '완료') 필터 조회 | 과거 학기 데이터 배제, 현재 학기 및 미완료 페이지만 타겟 조회 | ✓ |
| DB 전체 페이지 전수 조회 | 전체 페이지 페이지네이션 순회 로드 | |

**User's choice:** 최근 3개월 이내 DueDate 또는 미완료 필터 조회
**Notes:** API 레이트 리밋과 쿼리 성능을 최적화하기 위해 필요한 페이지만 필터 조회.

---

## 드라이런(Dry-run) 시뮬레이션 및 결과 모델 (Dry-run & Sync Result Reporting)

| Option | Description | Selected |
|--------|-------------|:---:|
| 완전한 시뮬레이션 (Real Read, Mocked Write) | 조회는 실제 수행하여 중복 여부 판별, 생성/수정 호출만 차단하고 SyncResult 반환 | ✓ |
| 오프라인 로컬 분석 모드 | 노션 API 미호출, 스크래퍼 통계만 출력 | |

**User's choice:** 완전한 시뮬레이션 (Real Read, Mocked Write)
**Notes:** 실제 노션 DB 상태를 반영하여 무엇이 생성되고 무엇이 스킵될지 정확한 사전 검증을 제공하기로 결정.

---

## 동기화 결과 객체(SyncResult) 상세 수준

| Option | Description | Selected |
|--------|-------------|:---:|
| 상세 계층형 SyncResult (Phase 5 Rich 최적화) | 생성/수정/스킵/에러 분리, 변경 필드 diff 및 스킵 사유 포함 | ✓ |
| 단순 카운트 중심 SyncResult | 건수 및 태스크 ID만 반환 | |

**User's choice:** 상세 계층형 SyncResult (Phase 5 Rich 최적화)
**Notes:** Phase 5의 터미널 색상 표 출력을 위해 변경 전후 diff와 사유를 충실히 제공.

---

## Notion API 클라이언트 및 데이터베이스 탐색 (API Client & Database Resolution)

| Option | Description | Selected |
|--------|-------------|:---:|
| 공식 Python notion-client + DB 이름 자동 탐색 | NOTION_DATABASE_NAME="Scheduler" 기반 search API 자동 매핑 + 지수 백오프 | ✓ |
| httpx 직접 호출 | 자체 REST 클라이언트 및 수동 ID 입력 | |

**User's choice:** 공식 Python notion-client + DB 이름 자동 탐색
**Notes:** 사용자의 탁월한 제안에 따라, 일반 사용자가 알기 어려운 32자리 UUID 대신 데이터베이스 이름(예: `Scheduler` 또는 `스케줄러`)으로 Notion API search를 통해 ID를 자동 탐색·해결하는 사용자 친화적 아키텍처 채택.

---

## 페이지 본문 블록 vs 메모 속성 (Page Properties vs Body Content)

| Option | Description | Selected |
|--------|-------------|:---:|
| DB 속성 메모(rich_text) 전담 기록 | 카드/행 미리보기 지원, 단 1회 API 호출로 페이지 생성 완료 (고속·효율) | ✓ |
| 페이지 본문(Block Children) 추가 생성 | 본문 단락 블록 추가 생성 (추가 API 호출 필요) | |

**User's choice:** DB 속성 메모(rich_text) 전담 기록
**Notes:** 추천안 채택. 노션 뷰에서 열지 않고도 확인 가능하고 성능을 극대화함.

---

## 노션 미연동 사용자를 위한 독립 실행 및 안전 폴백 (Decoupled Mode)

| Option | Description | Selected |
|--------|-------------|:---:|
| 안전 폴백 (Graceful Fallback) | 토큰/DB 부재 시 에러 크래시 없이 LXP 수집/분석만 완료 후 리포트 출력 | ✓ |
| 필수 검증 실패 (Hard Error) | 토큰 없으면 예외 발생 및 즉시 중단 | |

**User's choice:** 안전 폴백 (Graceful Fallback)
**Notes:** 사용자의 추가 요청 반영. 노션 스케줄러를 쓰지 않는 학생도 LXP 강의/과제 확인용으로 문제없이 사용할 수 있도록 지원.

---

## the agent's Discretion

- `notion-client` 내부 요청 시 `httpx.Timeout` 30초 설정
- 노션 API 에러 코드(401 Unauthorized, 404 Not Found) 발생 시 친절한 한국어 가이드 메시지 포맷팅

## Deferred Ideas

- None — 모든 논의가 Phase 4 범위 내에서 완결됨.
