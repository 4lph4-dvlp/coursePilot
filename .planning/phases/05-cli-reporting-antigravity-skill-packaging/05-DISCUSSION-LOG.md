# Phase 5: CLI Reporting & Universal Agent Skill Packaging - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22 (Codex session, areas 1–2) / 2026-09-23 (Claude Code session, resumed from checkpoint)
**Phase:** 05-cli-reporting-antigravity-skill-packaging
**Areas discussed:** 브리핑 구성, 명령 안전성, 스킬 호출 경험, 범용 에이전트 스킬 패키징, CLI 옵션 범위, 진행 표시, 종료 코드와 JSON 계약, E2E 검증 방식

---

## 브리핑 구성 (Codex session)

| Question | Options | Selected |
|---|---|---|
| 최상위 정렬 구조 | 긴급도 우선 / 과목 우선 / 단일 통합표 | 긴급도 우선 (기한 초과 → 24h → 이후, 구역 내 과목별) |
| 항목 정보 밀도 | 2단계 표시 / 간결한 표만 / 상세 표 | 2단계 표시 |
| 상단 요약 | 상태별 요약 / 최소 요약 / 상세 요약 | 상태별 요약 (과목 수 + 구역별 건수) |
| 항목이 많을 때 | 항상 전체 표시 / 채널별 차등 / 기본 개수 제한 | 항상 전체 표시 |

## 명령 안전성 (Codex session)

| Question | Options | Selected |
|---|---|---|
| sync 기본 쓰기 정책 | 미리보기 기본 / 확인 후 쓰기 / 즉시 쓰기 | 미리보기 기본 (--apply 명시 시만 쓰기) |
| check 범위 | LMS 조회와 브리핑만 / Notion 비교까지 / 선택적 비교 | LMS 조회와 브리핑만 |
| 부분 실패 처리 | 부분 성공 + 실패 종료 코드 / 즉시 중단 / 부분 성공 + 정상 종료 | 부분 성공 + 실패 종료 코드 |
| 출력 형식 | Rich 기본 + --json / Rich만 / JSON 기본 + --human | Rich 기본 + --json |

## 스킬 호출 경험

| Question | Options | Selected |
|---|---|---|
| SKILL.md 위치 | skills/kau-lxp/ 전용 폴더 / 저장소 루트 / .agents/skills/ | skills/kau-lxp/ |
| '노션에 올려줘' 흐름 | 드라이런 → 확인 → --apply / 바로 --apply / 항상 드라이런만 | 드라이런 → 확인 → --apply |
| 대화 출력 | --json → 마크다운 재구성 / Rich 그대로 / --markdown 모드 | --json → 마크다운 재구성 |
| 첫 실행 환경 미비 | 설치 자동·비밀정보 안내 / 안내만 / 대화로 .env 작성 | 설치 자동·비밀정보 안내 |

## 범용 에이전트 스킬 패키징

**User correction:** "왜 antigravity라고만 에이전트를 하나로 한정했어? 이 시스템은 모든 에이전트에서 사용 가능하도록 만들어야 하는데"

| Question | Options | Selected |
|---|---|---|
| 범용성 범위 | 중립 SKILL.md + 설치 안내 / + 설치 스크립트 / SKILL.md만 | 설치 안내 + 설치 스크립트 모두 (user free-text: "1번안과 2번안 둘을 합치는게") |
| 문서 표현 | 범용으로 수정 / CONTEXT.md에만 기록 | 범용으로 수정 |
| 설치 대상 | Claude Code / Codex / Antigravity / Pi·Hermes | 전부 |
| 설치 방식 | 복사 기본 + --link / 항상 링크 / 항상 복사 | 복사 기본 + --link |
| 스크립트 형태 | CLI 하위 명령 / 셸 스크립트(sh+ps1) | CLI 하위 명령 |

## CLI 옵션 범위 · 진행 표시 · 종료 코드와 JSON 계약 · E2E 검증

| Question | Options | Selected |
|---|---|---|
| CLI 옵션 | 최소 + 디버그 / + 과목 필터 / 최소만 | 최소 + 디버그 (--json, --headed, --relogin, --apply) |
| 기한 초과 표시 범위 | LMS 미완료 전부 / 최근 N일 | LMS 미완료 전부 |
| 진행 표시 | 과목별 + stderr / 없음 / --json 시 무음 | 과목별 + stderr |
| 종료 코드 | 0/1/2 / 0/1 / 오류별 세분화 | 0/1/2 |
| JSON 계약 | schema_version + 문서화 키 / 모델 직렬화 | schema_version + 문서화 키 |
| 민감정보 | 계정·토큰·쿠키 배제, URL 포함 / 링크도 제외 | 계정·토큰·쿠키 배제, URL 포함 |
| E2E | 픽스처 + 라이브 check/드라이런 / + 라이브 --apply / 픽스처만 | 픽스처 + 라이브 check/드라이런 |
| 스킬 호출 검증 | Claude Code 한 번 / 설치 경로 테스트만 / 전 에이전트 수동 | 전 에이전트 수동 확인 |

## Claude's Discretion

- CLI wiring and module layout, Rich styling, time-remaining format, sub-top-level JSON field names, project-level install target support.

## Deferred Ideas

- Per-agent install adapters and compatibility verification were deferred in the Codex session. Both were pulled into Phase 5 by the user's later choices. Nothing remains deferred.
