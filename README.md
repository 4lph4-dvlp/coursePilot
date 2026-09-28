# CoursePilot

대학 학업 일정·활동 관리 도우미. 영상·자료·과제·퀴즈의 상태와 마감일을 확인하고 개인 스케줄러에 연결합니다.

학교와 플랫폼에 종속되지 않는 제품을 목표로 합니다. **현재 구현은 Coursemos 계열 LMS와 Notion Scheduler 연동**이며, 다른 LMS의 지원은 별도 구현·검증이 필요합니다. 한국항공대는 첫 실사이트 검증 환경입니다.

## 개요 (Overview)

대학 LMS에 학생 로그인 정보를 통해 자동으로 로그인하여, 수강 중인 모든 강의의 주차별 온라인 강의 수강 여부, 과제 제출 여부, 마감 기한을 추출합니다. 결과는 AI 에이전트 채팅창에 브리핑 리포트로 표시되며, 사용자가 승인한 경우에만 개인 Notion `Scheduler` 데이터베이스에 중복 없이 동기화됩니다.

이 프로젝트는 하나의 CLI(`python -m coursepilot`)와, 그 CLI를 자연어로 호출하는 범용 Agent Skill(`skills/coursepilot/`)로 구성됩니다. 이 스킬은 특정 에이전트에 종속되지 않고, `SKILL.md` 형식을 지원하는 모든 에이전트(Claude Code, Codex, Antigravity, Pi, Hermes 등)에서 동일하게 동작합니다.

## 업데이트 및 스킬 연결

- 저장소를 받은 후 `uv sync`를 실행하세요. `uv run coursepilot --help` 또는 `uv run python -m coursepilot --help`로 실행을 확인합니다.
- 에이전트 스킬은 `uv run coursepilot install-skill --agent <id> --link`로 다시 연결하세요. 사용하지 않는 이전 스킬 연결은 직접 제거하고 에이전트를 새 세션으로 시작하세요. 복사 설치라면 `--link` 없이 재설치합니다.
- `~/.coursepilot/.env`의 키·직접 설정한 LMS 주소·세션/진척도 캐시·다운로드 경로·Notion 작업 ID는 그대로 유지됩니다. 예전 학교 기본값에 의존했다면 `LMS_URL` 또는 `LMS_PROFILE=kau`를 지정해야 합니다.
- 로컬 저장소 폴더명과 Git 원격 주소는 자동으로 바꾸지 않습니다. 폴더를 나중에 옮긴 경우 연결형 스킬은 새 위치에서 재설치하세요.

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

3. `.env.example`을 `~/.coursepilot/.env`로 복사한 뒤, 아래 키 값을 **직접** 채워 넣으세요. 이 값들은 절대 채팅이나 커밋에 공유하지 마세요.

   - `LMS_URL` — 학교의 Coursemos 기반 LMS 주소. 직접 지정하거나 `LMS_PROFILE=kau`를 선택하세요. 기본 학교는 없습니다.
   - `LMS_USERNAME` — LMS 학번/아이디
   - `LMS_PASSWORD` — LMS 비밀번호
   - `NOTION_TOKEN` (선택) — Notion 통합(integration) 토큰
   - `NOTION_DATABASE_NAME` 또는 `NOTION_DATABASE_ID` (선택) — 동기화 대상 Notion `Scheduler` 데이터베이스 (둘 중 하나만 있으면 됩니다)

## LMS 주소 (LMS_URL)

- **명시적 학교 선택**: `LMS_URL`을 직접 지정합니다. 주소와 프로필이 모두 없으면 LMS 조회 전에 설정 오류를 반환합니다.
- **선택적 학교 프로필**: 한국항공대는 `LMS_PROFILE=kau`로 https://lxp.kau.ac.kr 을 선택할 수 있습니다. `LMS_URL`이 있으면 프로필보다 우선합니다.
- **이전 LMS**: 이전 주소인 https://lms.kau.ac.kr 은 지난 학기 강좌만 보관하므로 현재 학기 과목이 0개로 나타납니다.
- **다른 학교 지원 (Coursemos 패밀리)**: 같은 유비온 Coursemos (Moodle) 엔진을 사용하는 타 대학 학생인 경우, `.env`의 `LMS_URL`을 해당 학교의 LXP/LMS 주소로 변경하여 사용할 수 있습니다.
- **미지원 플랫폼**: Canvas, Blackboard 등 Coursemos 계열이 아닌 학습 관리 시스템은 지원하지 않습니다.

## 명령어 (Commands)

| 명령어 | 설명 |
|--------|------|
| `python -m coursepilot check` | LMS에 로그인해 미완료 강의/과제 현황을 확인합니다. Notion에는 접근하지 않습니다. |
| `python -m coursepilot sync` | LMS 현황을 Notion Scheduler에 동기화합니다. 기본값은 **미리보기(dry-run)**이며, 아무것도 기록하지 않습니다. |
| `python -m coursepilot sync --apply` | 미리보기 대신 실제로 Notion에 생성/수정을 반영합니다. |
| `python -m coursepilot install-skill --agent <id>` | 이 저장소의 `coursepilot` 스킬을 지정한 에이전트의 사용자 스킬 폴더에 설치합니다. |

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

예를 들어 `uv run python -m coursepilot check --course-week "자료구조:5" --course-week "기초전자실험:5" --prepare-by 2026-10-02 --include-completed --json`으로 수업 준비 목록을 점검한 뒤, 같은 옵션으로 `sync --json` 미리보기를 실행할 수 있습니다. 과제 제목의 `W04`를 학기 4주차로 추정하지 않습니다. 무기한 영상도 선택한 주차에 속하면 포함합니다. `--prepare-by`는 LMS 공식 마감이나 기존 사용자 `Plan`·`상태`를 덮어쓰지 않습니다.

### 종료 코드 (Exit Codes)

| 코드 | 의미 |
|------|------|
| `0` | 완전 성공 |
| `1` | 부분 실패 — 일부 과목/항목에서 오류가 있었지만 나머지 결과는 정상 출력됨 |
| `2` | 치명적 오류 — 설정 누락 또는 로그인 실패 등으로 실행이 중단됨 |

JSON 출력의 정확한 필드 구조는 [`skills/coursepilot/JSON_CONTRACT.md`](skills/coursepilot/JSON_CONTRACT.md)를 참고하세요.

## 문제 해결 (Troubleshooting)

- **수강 중인 과목을 찾지 못함 (`no_courses_found`)**:
  로그인에는 성공했으나 과목이 0개인 경우 안내 문구가 표시됩니다. `~/.coursepilot/.env`의 `LMS_URL` 또는 선택한 `LMS_PROFILE`이 현재 학기 강의가 열리는 주소인지, 그리고 이번 학기 수강 신청된 과목이 있는지 확인하세요.
- **지원하지 않는 사이트 구조 (`UnsupportedLmsError`)**:
  `LMS_URL`이 가리키는 사이트가 Coursemos(Moodle) 기반 사이트가 아닌 경우 치명적 오류(종료 코드 2)가 발생합니다. `~/.coursepilot/.env`의 `LMS_URL`을 확인하고 학교의 Coursemos LXP/LMS 주소로 수정하세요.
- **인증 실패 (`AuthenticationError`)**:
  종료 코드 2와 함께 인증 오류가 발생하면 `.env`의 학번과 비밀번호, 그리고 `LMS_URL`이 맞는지 확인하세요. 필요시 `--relogin` 옵션으로 캐시를 지우거나 `--headed` 옵션으로 로그인 화면을 직접 확인하세요.

## Notion 안전성 (Notion Safety)

`sync`는 기본적으로 **미리보기(dry-run)**입니다 — 생성/수정될 항목 목록만 보여주고 아무것도 쓰지 않습니다. 실제로 Notion에 반영하려면 명시적으로 `--apply`를 붙여야 합니다. 에이전트를 통해 대화로 요청하는 경우("노션에 올려줘")에도 스킬은 먼저 미리보기를 보여주고, 사용자의 명확한 승인을 받은 뒤에만 `--apply`를 실행합니다.

Scheduler 조작의 표준 경로는 CoursePilot CLI입니다. `sync`와 `watch`는 `~/.coursepilot/.env`의 Notion 통합 토큰과 `notion-client` SDK를 사용합니다. 시청과 완료 처리를 함께 명시적으로 요청하면 에이전트도 `watch --update-notion`을 사용하며, 실제 시청 완료된 영상의 일치하는 작업만 완료 처리합니다. 단순 시청 요청이라면 시청 후 `watch sync-notion --dry-run --json`으로 변경 대상을 제안하고 사용자 승인 후 정확한 제목만 `--task-title`로 지정해 반영합니다. 다른 에이전트의 Notion MCP 접속은 이 CLI와 별도 인증·작업 이력을 사용하므로 CoursePilot Scheduler 작업에 섞지 않습니다.

Scheduler에 등록된 미완료 영상 작업 전체를 시청할 때는 `watch scheduler-tasks --json`으로 읽기 전용 목록을 얻고, 각 작업을 `watch --course "<과목 ID>" --week N --task-title "<정확한 작업명>" --update-notion --json`으로 실행합니다. 목록의 다른 작업을 잘못 재생하지 않도록 작업명 일치 여부를 확인합니다.

소스 저장소와 설치된 휠 모두 OS의 사용자 홈 아래 `~/.coursepilot/`에 개인 데이터를 둡니다. 자격 증명은 `.env`, 세션·진도·시청 이력은 `.cache/`, 자료·영상은 `downloads/`, 과목 약칭은 `config/course_mappings.json`입니다. `pathlib.Path.home()`을 사용하므로 Windows·macOS·Linux의 홈 위치를 따릅니다. 상대경로 `SESSION_CACHE_PATH`, `DOWNLOAD_DIR`, `COURSE_MAPPINGS_PATH`도 이 디렉터리에서 해석하고 절대경로 지정은 그대로 사용합니다. 현재 자동 테스트와 실사이트 검증은 Windows에서만 수행했습니다. 자료 `--dry-run`의 `planned`와 예정 저장 경로는 실제 다운로드가 아닙니다.

일부 `ubfile`은 Coursemos 문서 뷰어로만 제공됩니다. 이때 CoursePilot는 원본 파일이 저장된 것처럼 표시하지 않고 `viewed_only`와 원인을 보고합니다. LMS 열람 완료와 로컬 파일 보관 여부는 별도 상태입니다.

## 에이전트 스킬 설치 (Agent Skill Installation)

`skills/coursepilot/`는 에이전트 중립적인 `SKILL.md`(및 `JSON_CONTRACT.md`)로 구성된 범용 Agent Skill입니다. 아래 명령으로 지원하는 각 에이전트의 사용자 스킬 폴더에 설치할 수 있습니다.

| 에이전트 | 설치 명령 | 설치 경로 (예시) | 상태 |
|----------|-----------|-------------------|------|
| Claude Code | `python -m coursepilot install-skill --agent claude` | `~/.claude/skills/coursepilot` | 새 이름 설치 테스트 통과; 에이전트 재발견 확인 대기 |
| Codex | `python -m coursepilot install-skill --agent codex` | `~/.codex/skills/coursepilot` | 새 이름 설치 테스트 통과; 에이전트 재발견 확인 대기 |
| Antigravity | `python -m coursepilot install-skill --agent antigravity` | `~/.gemini/antigravity/skills/coursepilot` | 빈 폴더에서 재확인 대기 |
| Pi | `python -m coursepilot install-skill --agent pi` | `~/.pi/agent/skills/coursepilot` | 새 이름 설치 테스트 통과; 에이전트 재발견 확인 대기 |
| Hermes | `python -m coursepilot install-skill --agent hermes` | `$HERMES_HOME/skills/coursepilot` (또는 Windows `%LOCALAPPDATA%\hermes\skills\coursepilot`, 그 외 `~/.hermes/skills/coursepilot`) | 새 이름 설치 테스트 통과; 에이전트 재발견 확인 대기 |

설치가 끝나면 **해당 에이전트를 재시작(또는 새 세션 시작)**한 뒤 "과제 확인해줘"처럼 자연어로 요청해 보세요. 상세 확인 결과는 `.planning/phases/05-cli-reporting-antigravity-skill-packaging/05-AGENT-SKILL-EVIDENCE.md`에 기록됩니다.

### 개발용 `--link` 설치

`install-skill --agent <id> --link`를 사용하면 복사 대신 심볼릭 링크(Windows에서 권한 문제로 심볼릭 링크가 실패하면 NTFS 접합점(junction)으로 자동 대체)로 설치되어, 저장소의 `skills/coursepilot/` 파일을 수정할 때마다 설치된 스킬에도 즉시 반영됩니다. 심볼릭 링크와 접합점이 **모두** 실패하면 조용히 복사로 넘어가지 않고, 종료 코드 `2`와 함께 명확한 오류 메시지로 실패를 알립니다 — 이 경우 `--link` 없이 다시 실행해 복사 설치를 사용하세요.

## 라이선스

내부/개인 사용 목적의 프로젝트입니다.
