# Phase 17: Universal Skill Packaging, Multi-Agent Deployment & End-to-End Verification - Context

**Gathered:** 2026-09-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 17은 이전 단계(Phase 12~16)에서 구현된 전체 신규 기능(`progress`, `board`/`notices`/`qna`, `materials`/`files`, `download-vod`, `watch` 고급 제어 옵션)을 범용 Agent Skill 규격에 완벽히 통합·패키징하고, 지원되는 5개 AI 코딩 에이전트에 일괄 재배포하며, 실제 KAU LXP 사이트 대상 E2E 통합 검증을 완수합니다:
1. `skills/coursepilot/SKILL.md` 업데이트: 프론트매터 description 확장, 대표 한국어 발화 엄선 및 인텐트 매핑, 기능별 독립 섹션(§7 종합 진도율 대시보드, §8 공지 및 Q&A 게시판, §9 학습자료 다운로드/열람, §10 VOD 스트림 다운로드) 구성, 마크다운 표준 템플릿 명시, 비동기/동기 실행 모드 분리 지침 수록.
2. `skills/coursepilot/JSON_CONTRACT.md` 확장: `ProgressReport`, `BoardReport`, `MaterialReport`, `DownloadVodReport` 등 신규 4대 서브커맨드 모델 및 필드 전수 명세, 가상 예시 JSON 페이로드 수록, 공통 envelope(`schema_version: 1`) 정책 명시.
3. `tests/test_contract_doc.py` 및 `tests/test_installer.py` 자동 검증 확장: 모든 신규 모델의 필드 백틱 누락 검사, 예시 JSON 모델 유효성 검증, 5개 에이전트 경로 배포 무결성 검증 pytest 추가.
4. `install-skill --agent all --link` CLI 옵션 확장 및 5개 에이전트(Claude Code, Codex, Antigravity, Pi, Hermes) 선제 배포/심볼릭 링크 갱신.
5. 실제 KAU LXP 사이트 대상 E2E 검증: 7개 수강 과목 전수 읽기/브리핑 검증(`check`, `progress`, `notices`, `qna`), 1개 과목 핀포인트 다운로드 스모크 테스트(`materials`, `download-vod`), `watch` 라이프사이클(dry-run -> 백그라운드 시작 -> `status` -> `stop` 안전 중단), Notion 실데이터 조회 및 순수 드라이런(0건 쓰기 보장) 검증.

</domain>

<decisions>
## Implementation Decisions

### 1. SKILL.md 구조화 및 에이전트 트리거 설계
- **D-17-01:** 기능/인텐트별 독립 섹션 구성: 기존 §4(check), §5(sync), §6(watch)에 이어 §7 종합 진도율 대시보드(progress), §8 공지 및 Q&A(board/notices/qna), §9 학습자료(materials/files), §10 VOD 다운로드(download-vod)로 명확히 분리하여 구성한다. — **Reversibility:** costly — 에이전트 스킬 프롬프트 구조 및 자연어 인터페이스 가이드라인에 영향
- **D-17-02:** 대표 한국어 발화 8~10개 엄선 + 인텐트 매핑 가이드: frontmatter description 및 본문 상단에 대표 한국어 발화를 엄선하고, '진도율 확인', '공지/Q&A', '자료 다운', '영상 다운' 등 사용자 질문 상황별 최적 커맨드 분기 가이드를 명시한다.
- **D-17-03:** 서브커맨드별 마크다운 렌더링 템플릿 명시: 에이전트가 CLI의 JSON 출력을 사용자 대화창에 마크다운으로 재구성할 때 따를 표준 표 컬럼 순서, 진행 상태 배지(`[완료]`, `[진행중]`, `[누락]`), 3단 대시보드 구조 등을 규정한다.
- **D-17-04:** 작업 특성별 실행 모드 분리: 실시간 1.0배속 재생이 필요한 `watch`만 비동기 백그라운드 태스크(서브에이전트)로 위임하고, 고속 병렬 다운로드(`download-vod`), 파일 다운로드(`materials`), 상태 제어(`watch status`, `watch stop`, `watch sync-notion`)는 동기식 즉시 실행으로 명시한다.

### 2. E2E 실사이트 검증 범위 및 라이브 테스트 전략
- **D-17-05:** 7개 전 과목 전수 조회 검증: 실제 KAU LXP 사이트 대상 E2E 검증 시 `check`, `progress`, `notices`, `qna`를 7개 수강 과목 전체에 대해 실행하여 모든 파서 및 3단 대시보드 무결성을 입증한다.
- **D-17-06:** 1개 대표 과목 핀포인트 스모크 다운로드: 대용량 네트워크/디스크 부하를 방지하기 위해 `download-vod` 및 `materials --download`는 1개 대표 과목의 1개 항목에 한해 실제로 다운로드하여 파일 생성 및 스트림 결합 무결성을 검증하고 정리한다.
- **D-17-07:** 드라이런 + 라이브 시작/진행/중단 라이프사이클 검증: `watch`는 dry-run 목록 검증 후, 실제 1개 영상 재생을 시작하여 `watch status` 갱신을 확인하고 `watch stop`으로 안전하게 중단하는 라이프사이클을 검증하여 출석 상태 오염을 방지한다.
- **D-17-08:** 실데이터 조회 + 순수 드라이런 0건 쓰기 보장: 학생의 실제 Notion Scheduler DB 연동 검증은 스키마와 페이지를 실시간으로 쿼리하되, 쓰기는 드라이런으로 차단하여 0건 생성/수정을 보장한다. — **Reversibility:** costly — Notion 실데이터 무결성 보호

### 3. 5개 에이전트 배포 및 링크 무결성 검증
- **D-17-09:** --link 심볼릭 링크 유지 및 5개 에이전트 링크 무결성 검증: 개발 저장소의 소스 변경이 즉시 모든 에이전트에 반영되도록 심볼릭 링크/정션 배포 방식을 유지하고 상태를 점검 및 갱신한다.
- **D-17-10:** --agent all 일괄 배포 옵션 추가: `python -m coursepilot install-skill --agent all --link`를 지원하도록 `installer.py`와 `cli.py`를 확장하여 5개 에이전트에 한 번에 설치/링크할 수 있게 한다. — **Reversibility:** costly — CLI 시그니처 및 installer API
- **D-17-11:** 부모 홈 폴더 자동 생성 및 5개 에이전트 선제 배포: 머신에 특정 에이전트의 홈 디렉터리가 아직 없더라도 부모 폴더를 생성하여 링크를 선제 배포함으로써 향후 에이전트 도구 설치 시 즉시 활성화되도록 한다.
- **D-17-12:** pytest 에이전트 배포 무결성 검증 테스트 추가: `tests/test_installer.py`에 5개 에이전트 전체 경로의 `SKILL.md`, `JSON_CONTRACT.md`, `repo-root.txt` 유효성을 검증하는 테스트 케이스를 추가한다.

### 4. JSON_CONTRACT.md 확장 및 자동 계약 검증 테스트
- **D-17-13:** 신규 4대 서브커맨드 모델 및 필드 전수 기술: `JSON_CONTRACT.md`에 `progress`, `board`, `materials`, `download-vod`의 모든 DTO 모델(필드명, 타입, Nullable, 설명)을 check/sync 수준으로 완전 문서화한다.
- **D-17-14:** 4개 신규 서브커맨드 각각 완전한 가상 JSON 예시 블록 수록: `progress`, `board`, `materials`, `download-vod` 모두 실제 출력과 일치하는 현실적인 가상 JSON을 수록한다.
- **D-17-15:** 신규 4개 보고서 모델 전체로 pytest 자동 검증 확장: `tests/test_contract_doc.py`를 확장하여 `ProgressReport`, `BoardReport`, `MaterialReport`, `DownloadVodReport`의 모든 필드 백틱 누락 검사 및 예시 JSON 자동 모델 검증을 적용한다. — **Reversibility:** costly — CI/테스트 게이트 및 계약 테스트 확장
- **D-17-16:** schema_version: 1 통일 및 비파괴 확장 정책: 모든 신규 서브커맨드가 공통 envelope(`schema_version: 1`, `command`, `generated_at`/`timestamp`, `errors`)을 준수하며 신규 필드 추가 시 v1을 유지한다.

### the agent's Discretion
- SKILL.md 내 세부 자연어 발화 문구의 정밀 튜닝.
- 5개 에이전트 배포 시 Windows 환경(symlink vs junction) 세부 플래그 처리.
- 스모크 테스트 대상 1개 대표 과목(예: 기전실 등)의 구체적 선정.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Roadmap & Requirements
- `.planning/ROADMAP.md` § Phase 17 — Universal Skill Packaging, Multi-Agent Deployment & End-to-End Verification
- `.planning/REQUIREMENTS.md` § SKIL-04, VERIF-03 — Skill packaging and end-to-end verification requirements

### Universal Skill & Contract Specifications
- `skills/coursepilot/SKILL.md` — Universal Agent Skill specification and execution rules
- `skills/coursepilot/JSON_CONTRACT.md` — Machine-readable CLI JSON contract specification
- `README.md` — Project overview and agent installation guide table

### Agent Installer & CLI Entrypoints
- `src/coursepilot/installer.py` — `AGENT_SKILL_PATHS`, `install_skill`, and home resolution logic
- `src/coursepilot/cli.py` — Click CLI commands (`install-skill`, `progress`, `board`, `materials`, `download-vod`, `check`, `sync`, `watch`)

### Report Models & Pipelines
- `src/coursepilot/report_models.py` — Core report models (CheckReport, SyncReport, ErrorItem, ReportNotice)
- `src/coursepilot/progress/models.py` — ProgressReport, CourseProgress, DashboardSummary DTOs
- `src/coursepilot/board/models.py` — BoardReport, BoardPostItem, BoardCommentItem DTOs
- `src/coursepilot/materials/models.py` — MaterialReport, DownloadedMaterialItem DTOs
- `src/coursepilot/stream/downloader.py` — DownloadVodReport and HLS downloader models
- `src/coursepilot/player/runner.py` — WatchResult and PlaybackProgress models

### Test Suites
- `tests/test_installer.py` — Agent skill installer unit and contract tests
- `tests/test_contract_doc.py` — Contract documentation and model consistency tests

### Historical Verification Logs
- `.planning/phases/08-end-to-end-verification-agent-redeployment/08-01-SUMMARY.md` — Milestone 2 live verification patterns
- `.planning/phases/11-background-subagent-packaging/11-01-SUMMARY.md` — Multi-agent skill packaging and background task patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AGENT_SKILL_PATHS` (`src/coursepilot/installer.py`): 5개 지원 에이전트(Claude Code, Codex, Antigravity, Pi, Hermes)의 홈 마커 및 스킬 폴더 경로 정의 테이블.
- `install_skill()` (`src/coursepilot/installer.py`): `--link` 심볼릭 링크 및 복사 모드 설치 엔진.
- `_collect_model_field_names()` (`tests/test_contract_doc.py`): Pydantic 모델의 모든 필드를 재귀적으로 추출하여 문서 백틱 존재 여부를 검사하는 도구.
- `_extract_json_blocks()` (`tests/test_contract_doc.py`): 마크다운 문서 내 JSON 코드 블록 추출 및 Pydantic 검증 유틸리티.

### Established Patterns
- Click CLI 서브커맨드 패턴: `stdout`은 순수 JSON 단독 출력, `stderr`는 Rich 진행 상황/스피너 출력.
- 안전한 에러 마스킹 (`errors.py`, `safe_cli_error`): 자격 증명이나 원본 스택 트레이스 노출 방지.
- `schema_version: 1` 공통 envelope 구조: 모든 JSON 응답이 동일한 버전 규칙 준수.
- 에이전트 중립성 (`_AGENT_SPECIFIC_DENYLIST`): `SKILL.md` 본문에 특정 에이전트 전용 도구명을 언급하지 않는 원칙.

### Integration Points
- `src/coursepilot/installer.py`: `install_skill(agent="all", ...)` 지원 추가.
- `src/coursepilot/cli.py`: `@cli.command("install-skill")`의 `--agent` 옵션에 `all` 허용.
- `skills/coursepilot/SKILL.md`: 신규 5개 커맨드 문서화 및 발화 매핑.
- `skills/coursepilot/JSON_CONTRACT.md`: 신규 모델 및 예시 JSON 페이로드 추가.
- `tests/test_installer.py`: `test_install_skill_all_agents()` 추가.
- `tests/test_contract_doc.py`: `ProgressReport`, `BoardReport`, `MaterialReport`, `DownloadVodReport` 검증 로직 추가.

</code_context>

<specifics>
## Specific Ideas

- 사용자가 "이번 학기 과목별 진도율 어때?" 또는 "학습활동 대시보드 보여줘"라고 질문 시:
  "에이전트가 `progress --json`을 호출하고, 3단 대시보드 템플릿(종합 요약 게이지 표, 이번 주차 To-Do 목록, 지난 주차 결석/미제출 Alert)으로 브리핑."
- 사용자가 "공지사항 새로 올라온 거 있어?"라고 질문 시:
  "에이전트가 `notices --json`을 호출하고, 과목별 최신 공지 목록 및 링크를 마크다운 표로 깔끔하게 렌더링."
- 사용자가 "5개 에이전트에 스킬 배포해줘"라고 요청 시:
  "CLI에서 `python -m coursepilot install-skill --agent all --link`를 실행하여 5개 에이전트 경로에 심볼릭 링크를 일괄 생성/검증."
- 실사이트 검증 시:
  "7개 전 과목 대상 `check`, `progress`, `notices`, `qna` 전수 조회로 0-defect 확인 및 기전실 1개 항목 대상 핀포인트 다운로드/재생 라이프사이클 스모크 테스트."

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 17-universal-skill-packaging-multi-agent-deployment-end-to-end-verification*
*Context gathered: 2026-09-26*
