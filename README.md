# KAU LXP Assistant & Notion Scheduler Sync

한국항공대학교(KAU) LMS(코스모스/Coursemos) 자동 출결/과제 확인 및 개인 Notion 스케줄러 동기화 도구.

## 개요 (Overview)

대학 LMS에 학생 로그인 정보를 통해 자동으로 로그인하여, 수강 중인 모든 강의의 주차별 온라인 강의 수강 여부, 과제 제출 여부, 마감 기한을 추출합니다. 결과는 AI 에이전트 채팅창에 브리핑 리포트로 표시되며, 사용자가 승인한 경우에만 개인 Notion `Scheduler` 데이터베이스에 중복 없이 동기화됩니다.

이 프로젝트는 하나의 CLI(`python -m kau_assistant`)와, 그 CLI를 자연어로 호출하는 범용 Agent Skill(`skills/kau-lxp/`)로 구성됩니다. 이 스킬은 특정 에이전트에 종속되지 않고, `SKILL.md` 형식을 지원하는 모든 에이전트(Claude Code, Codex, Antigravity, Pi, Hermes 등)에서 동일하게 동작합니다.

## 요구 사항 (Requirements)

- Python 3.11 이상
- [`uv`](https://docs.astral.sh/uv/) — Python 패키지 및 실행 관리자

## 설치 및 설정 (Setup)

1. 저장소를 클론한 뒤 의존성을 설치합니다.

   ```
   uv sync
   ```

2. Playwright의 Chromium 브라우저를 설치합니다.

   ```
   uv run playwright install chromium
   ```

3. `.env.example`을 `.env`로 복사한 뒤, 아래 키 값을 **직접** 채워 넣으세요. 이 값들은 절대 채팅이나 커밋에 공유하지 마세요.

   - `LMS_URL` — 학교의 Coursemos(Moodle) 기반 LXP/LMS 주소 — 한국항공대는 기본값 https://lxp.kau.ac.kr 이므로 비워 두거나 그대로 두면 됩니다.
   - `LMS_USERNAME` — LMS 학번/아이디
   - `LMS_PASSWORD` — LMS 비밀번호
   - `NOTION_TOKEN` — Notion 통합(integration) 토큰
   - `NOTION_DATABASE_NAME` 또는 `NOTION_DATABASE_ID` — 동기화 대상 Notion `Scheduler` 데이터베이스 (둘 중 하나만 있으면 됩니다)

## LMS 주소 (LMS_URL)

- **기본 주소**: 한국항공대 학생의 이번 학기 강의는 https://lxp.kau.ac.kr (KAU LXP)에서 열립니다. `.env`에 `LMS_URL`을 설정하지 않으면 자동으로 이 주소를 조회합니다.
- **이전 LMS**: 이전 주소인 https://lms.kau.ac.kr 은 지난 학기 강좌만 보관하므로 현재 학기 과목이 0개로 나타납니다.
- **다른 학교 지원 (Coursemos 패밀리)**: 같은 유비온 Coursemos (Moodle) 엔진을 사용하는 타 대학 학생인 경우, `.env`의 `LMS_URL`을 해당 학교의 LXP/LMS 주소로 변경하여 사용할 수 있습니다.
- **미지원 플랫폼**: Canvas, Blackboard 등 Coursemos 계열이 아닌 학습 관리 시스템은 지원하지 않습니다.

## 명령어 (Commands)

| 명령어 | 설명 |
|--------|------|
| `python -m kau_assistant check` | LMS에 로그인해 미완료 강의/과제 현황을 확인합니다. Notion에는 접근하지 않습니다. |
| `python -m kau_assistant sync` | LMS 현황을 Notion Scheduler에 동기화합니다. 기본값은 **미리보기(dry-run)**이며, 아무것도 기록하지 않습니다. |
| `python -m kau_assistant sync --apply` | 미리보기 대신 실제로 Notion에 생성/수정을 반영합니다. |
| `python -m kau_assistant install-skill --agent <id>` | 이 저장소의 `kau-lxp` 스킬을 지정한 에이전트의 사용자 스킬 폴더에 설치합니다. |

공통 옵션:

| 옵션 | 설명 |
|------|------|
| `--json` | 사람이 읽는 Rich 리포트 대신, 버전이 명시된 JSON을 표준출력에 출력합니다. |
| `--headed` | 브라우저 창을 표시하며 실행합니다 (기본은 헤드리스). |
| `--relogin` | 캐시된 세션(`session.json`)을 무시하고 다시 로그인합니다. |
| `--include-completed` | 완료 항목도 점검표에 표시합니다. 동기화에서는 새로 생성하지 않습니다. |
| `--week N` | 지정한 실제 LMS 주차를 포함합니다. 반복 가능 (`check`/`sync`). |
| `--course-week "과목명:N"` | 과목별 주차를 지정합니다. 전체 이름·고유한 일부 이름·설정된 약칭·ID, 반복 가능. |
| `--due-before YYYY-MM-DD` | 지정일 종일까지 마감하는 작업도 포함합니다. 주차 조건과 OR. |
| `--prepare-by YYYY-MM-DD` | 공식 마감과 별도로 수업 준비 목표를 JSON·Notion 메모에 기록합니다. |

`check`와 `sync`는 영상·자료·과제·퀴즈를 모두 수집합니다. 강의실 요약 대시보드에서는 주차별 목록으로 전환하고 실제 섹션의 주차와 완료 상태를 읽습니다. 활동 링크가 있는데 해석하지 못하면 부분 수집 실패를 보고합니다.

예를 들어 `uv run python -m kau_assistant check --course-week "자료구조:5" --course-week "기초전자실험:5" --prepare-by 2026-10-02 --include-completed --json`으로 수업 준비 목록을 점검한 뒤, 같은 옵션으로 `sync --json` 미리보기를 실행할 수 있습니다. 과제 제목의 `W04`를 학기 4주차로 추정하지 않습니다. 무기한 영상도 선택한 주차에 속하면 포함합니다. `--prepare-by`는 LMS 공식 마감이나 기존 사용자 `Plan`·`상태`를 덮어쓰지 않습니다.

### 종료 코드 (Exit Codes)

| 코드 | 의미 |
|------|------|
| `0` | 완전 성공 |
| `1` | 부분 실패 — 일부 과목/항목에서 오류가 있었지만 나머지 결과는 정상 출력됨 |
| `2` | 치명적 오류 — 설정 누락 또는 로그인 실패 등으로 실행이 중단됨 |

JSON 출력의 정확한 필드 구조는 [`skills/kau-lxp/JSON_CONTRACT.md`](skills/kau-lxp/JSON_CONTRACT.md)를 참고하세요.

## 문제 해결 (Troubleshooting)

- **수강 중인 과목을 찾지 못함 (`no_courses_found`)**:
  로그인에는 성공했으나 과목이 0개인 경우 안내 문구가 표시됩니다. 저장소 `.env`의 `LMS_URL`이 현재 학기 강의가 열리는 주소(한국항공대 기본값 https://lxp.kau.ac.kr)인지, 그리고 이번 학기 수강 신청된 과목이 있는지 확인하세요.
- **지원하지 않는 사이트 구조 (`UnsupportedLmsError`)**:
  `LMS_URL`이 가리키는 사이트가 Coursemos(Moodle) 기반 사이트가 아닌 경우 치명적 오류(종료 코드 2)가 발생합니다. 저장소 `.env`의 `LMS_URL`을 확인하고 학교의 Coursemos LXP/LMS 주소로 수정하세요.
- **인증 실패 (`AuthenticationError`)**:
  종료 코드 2와 함께 인증 오류가 발생하면 `.env`의 학번과 비밀번호, 그리고 `LMS_URL`이 맞는지 확인하세요. 필요시 `--relogin` 옵션으로 캐시를 지우거나 `--headed` 옵션으로 로그인 화면을 직접 확인하세요.

## Notion 안전성 (Notion Safety)

`sync`는 기본적으로 **미리보기(dry-run)**입니다 — 생성/수정될 항목 목록만 보여주고 아무것도 쓰지 않습니다. 실제로 Notion에 반영하려면 명시적으로 `--apply`를 붙여야 합니다. 에이전트를 통해 대화로 요청하는 경우("노션에 올려줘")에도 스킬은 먼저 미리보기를 보여주고, 사용자의 명확한 승인을 받은 뒤에만 `--apply`를 실행합니다.

## 에이전트 스킬 설치 (Agent Skill Installation)

`skills/kau-lxp/`는 에이전트 중립적인 `SKILL.md`(및 `JSON_CONTRACT.md`)로 구성된 범용 Agent Skill입니다. 아래 명령으로 지원하는 각 에이전트의 사용자 스킬 폴더에 설치할 수 있습니다.

| 에이전트 | 설치 명령 | 설치 경로 (예시) | 상태 |
|----------|-----------|-------------------|------|
| Claude Code | `python -m kau_assistant install-skill --agent claude` | `~/.claude/skills/kau-lxp` | 확인됨 (과제 확인, 노션 미리보기) |
| Codex | `python -m kau_assistant install-skill --agent codex` | `~/.codex/skills/kau-lxp` | 과제 확인 확인됨, 노션 미리보기 재확인 대기 |
| Antigravity | `python -m kau_assistant install-skill --agent antigravity` | `~/.gemini/antigravity/skills/kau-lxp` | 빈 폴더에서 재확인 대기 |
| Pi | `python -m kau_assistant install-skill --agent pi` | `~/.pi/agent/skills/kau-lxp` | 과제 확인 확인됨, 노션 미리보기 재확인 대기 |
| Hermes | `python -m kau_assistant install-skill --agent hermes` | `$HERMES_HOME/skills/kau-lxp` (또는 Windows `%LOCALAPPDATA%\hermes\skills\kau-lxp`, 그 외 `~/.hermes/skills/kau-lxp`) | 설치 경로 수정됨, 재확인 대기 |

설치가 끝나면 **해당 에이전트를 재시작(또는 새 세션 시작)**한 뒤 "과제 확인해줘"처럼 자연어로 요청해 보세요. 상세 확인 결과는 `.planning/phases/05-cli-reporting-antigravity-skill-packaging/05-AGENT-SKILL-EVIDENCE.md`에 기록됩니다.

### 개발용 `--link` 설치

`install-skill --agent <id> --link`를 사용하면 복사 대신 심볼릭 링크(Windows에서 권한 문제로 심볼릭 링크가 실패하면 NTFS 접합점(junction)으로 자동 대체)로 설치되어, 저장소의 `skills/kau-lxp/` 파일을 수정할 때마다 설치된 스킬에도 즉시 반영됩니다. 심볼릭 링크와 접합점이 **모두** 실패하면 조용히 복사로 넘어가지 않고, 종료 코드 `2`와 함께 명확한 오류 메시지로 실패를 알립니다 — 이 경우 `--link` 없이 다시 실행해 복사 설치를 사용하세요.

## 라이선스

내부/개인 사용 목적의 프로젝트입니다.
