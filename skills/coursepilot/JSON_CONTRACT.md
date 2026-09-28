# coursepilot CLI JSON 계약 v1 (JSON Contract v1)

이 문서는 `python -m coursepilot check --json`, `python -m coursepilot sync --json`, 그리고 `python -m coursepilot watch --json`이 표준출력(stdout)에 출력하는 JSON의 정확한 구조를 설명합니다. 실제 소스는 `src/coursepilot/report_models.py`와 `src/coursepilot/player/runner.py`의 Pydantic 모델이며, 이 문서는 그 모델을 사람이 읽을 수 있게 옮긴 참조 자료입니다. `skills/coursepilot/SKILL.md`는 이 문서를 가리킵니다.

## 버전 규칙 (Versioning)

- 현재 스키마 버전은 `schema_version: 1`입니다.
- **선택적(optional) 필드를 추가하는 것**은 `schema_version`을 그대로 `1`로 유지합니다 (`notices` 필드는 v1 하에서 선택적 필드로 추가되었습니다).
- **필드 이름 변경, 필드 제거, 필드 타입 변경**은 반드시 `schema_version`을 올립니다 (breaking change).
- 이 스키마를 파싱하는 모든 에이전트는 `schema_version`을 먼저 확인하고, 알지 못하는 값이면 파싱을 중단하고 사람에게 알려야 합니다.

## 호출 방식과 스트림 (Invocation & Streams)

### 활동 범위와 준비일 (선택적 v1 확장)

`check`/`sync` 공통 옵션: `--week N` 및 `--course-week "과목명:N"`는 반복할 수 있습니다. 과목명은 전체 이름·고유한 일부 이름·설정된 약칭·과목 ID로 식별합니다. `--due-before YYYY-MM-DD`는 KST 종일 마감 기준이며 모든 범위 선택 조건은 OR입니다. `--prepare-by YYYY-MM-DD`는 공식 마감과 별도입니다. `--include-completed` 사용 시 `summary.total_count`는 완료 항목을 포함하는 점검표의 총수입니다.

`ReportItem`에 다음 선택 필드가 추가되었습니다. 누락된 경우 기본값을 적용하는 v1 호환 확장입니다.

| 필드 | 타입 | 의미 |
|---|---|---|
| `week_number` | `int \| None` | 제목 숫자가 아닌 실제 LMS 섹션 주차 |
| `is_completed` | `bool` | LMS 완료 여부, 기본 false |
| `start_date` | `datetime \| None` | 공식 공개/시작 일시 |
| `is_available` | `bool` | 실제 활동 링크 공개 여부, 기본 true |
| `preparation_date` | `datetime \| None` | 개인 수업 준비 목표, 공식 `due_date`를 변경하지 않음 |

`task_type`은 기존 유형에 `material`(강의자료 확인 및 다운로드)을 추가 지원합니다. 자료 이름은 `[과목] N주차 자료제목 확인 및 다운로드`이며 모듈 ID와 원본 URL로 식별합니다. Notion은 메모의 LMS URL로 동일 활동을 우선 식별하고, 이전 데이터는 정규화 제목으로 대조합니다. 동일한 원본 활동이나 제목이 모호하면 오류를 반환합니다. 완료 활동은 `sync.skip[].reason: lms_completed`로 건너뜁니다. 공식 마감 `DueDate`, 메모의 준비 목표, 보호되는 사용자 `Plan`은 서로 다른 값입니다.

`MaterialItem`도 `start_date`, `due_date`, `raw_due_date`, `is_overdue`, `is_available`를 제공합니다. 아직 공개되지 않은 자료는 `materials` 실행에서 `skipped`로 표시하고 방문/다운로드하지 않습니다. `ProgressReport.courses[].all_items`의 각 활동은 실제 섹션 주차와 `module_id`를 사용하며 `start_date`와 `is_available`도 선택적 v1 확장 필드입니다.

`materials --dry-run`은 방문·다운로드를 실행하지 않습니다. 공개된 자료의 `status`는 `planned`, `view_success`는 `false`, `downloaded_count`와 `viewed_count`는 0입니다. `saved_path`는 예정 경로이며 실제 파일 생성 증거가 아닙니다. `item.is_completed`는 LMS 열람 상태입니다. 실행 모드의 `status: downloaded`와 비어 있지 않은 `saved_path`만 다운로드 결과로 해석하세요.

Coursemos 문서 뷰어가 원본 파일 링크를 제공하지 않을 때 실행 결과는 `status: viewed_only`, 빈 `saved_path`, 설명이 담긴 `error_message`입니다. LMS 열람 완료는 `view_success: true`로 나타나며, 이미 완료된 활동도 여기에 포함됩니다. 이는 로컬 파일 다운로드 성공이 아닙니다.

유일한 LMS 원본 URL로 기존 Notion 페이지를 식별한 경우 제목 변경은 `sync.update[].changes`에 `field: "이름"`으로 나타납니다. 새 제목이 다른 페이지와 충돌하면 `title_collision` 오류가 나며 해당 작업은 수정하지 않습니다. `상태`와 `Plan`은 계속 보호됩니다.

`progress`만은 수집에 성공해도 `summary.missed_past_count > 0`이면 기존 동작에 따라 종료 코드 `1`을 반환합니다. 이 경우 `status: success`, 빈 `errors`, 각 과목 `status: ok`를 확인하고 수집 실패와 구분하세요.

- `--json` 플래그와 함께 실행하면 표준출력(stdout)에는 **정확히 하나의 JSON 객체**만 출력됩니다. 그 외의 텍스트는 출력되지 않습니다.
- 표준에러(stderr)에는 진행 상황(`[i/N] 과목명 수집 중` 형태)과 로그 메시지만 출력됩니다. stderr는 절대 JSON으로 파싱하지 마세요.
- click(CLI 프레임워크)이 자체적으로 발생시키는 사용 오류(알 수 없는 옵션 등)는 종료 코드 `2`로 종료하며 JSON을 전혀 출력하지 않습니다. 이 경우 stderr의 사용법(usage) 메시지를 그대로 사용자에게 보여주세요.

## 종료 코드 (Exit Codes)

| 코드 | 의미 |
|------|------|
| `0` | 완전 성공 — 오류 없이 모든 결과가 정상적으로 수집/처리됨 |
| `1` | 부분 실패 — 일부 과목 또는 항목에서 오류가 발생했지만, 나머지 결과는 여전히 유효하며 함께 출력됨 (`errors` 배열 확인) |
| `2` | 치명적 오류 — 설정 오류 또는 로그인 실패 등으로 실행이 중단됨. `errors[].scope == "fatal"`인 항목이 최소 하나 존재함 |

## 데이터/시간 형식

모든 날짜·시각 필드는 ISO-8601 형식이며 한국 표준시(KST, `+09:00`) 오프셋을 포함합니다. 예: `2026-09-23T13:49:13.279844+09:00`.

---

## 모델 필드 참조

아래 표의 "타입"은 Python/Pydantic 타입 힌트를 그대로 옮긴 것이고, "Nullable"은 `None`(JSON의 `null`)이 허용되는지를 뜻합니다. "의미"는 각 모델의 클래스 docstring을 기반으로 합니다.

### `ReportSummary`

과목 수와 긴급도별 카운트 — 브리핑 헤더에 표시됩니다 (D-03).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `course_count` | `int` | 아니오 | 수집을 시도한 과목 수 |
| `total_count` | `int` | 아니오 | 기본은 미완료 항목 수, `--include-completed`는 완료 포함 점검 항목 수 |
| `overdue_count` | `int` | 아니오 | 기한 초과 항목 수 |
| `due_within_24h_count` | `int` | 아니오 | 24시간 이내 마감 항목 수 |
| `later_count` | `int` | 아니오 | 그 이후 일정 항목 수 |
| `error_count` | `int` | 아니오 | 수집/동기화 오류 수 (`errors` 배열 길이) |

### `ReportItem`

브리핑에 나타나는 미완료 강의/과제/퀴즈 한 건 (D-01, D-02).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `task_id` | `str` | 아니오 | 항목 고유 식별자 |
| `title` | `str` | 아니오 | 정규화된 작업 이름 (예: `[자구] 3주차 강의 시청`) |
| `course_id` | `str` | 아니오 | 과목 고유 식별자 |
| `course_name` | `str` | 아니오 | 과목 전체 이름 |
| `course_abbr` | `str` | 아니오 | 과목 약칭 (예: `자구`) |
| `task_type` | `str` | 아니오 | 작업 종류 (강의/과제/퀴즈 등) |
| `due_date` | `datetime \| None` | 예 | 마감일시 (없으면 `null`) |
| `remaining_minutes` | `int \| None` | 예 | 남은(또는 지난, 음수) 분. `due_date`가 없으면 `null` |
| `remaining_text` | `str` | 아니오 | 사람이 읽는 남은 시간 문구 (예: `3시간 12분 남음`, `2일 3시간 지남`) |
| `lms_url` | `str` | 아니오 | 해당 항목의 LMS 바로가기 링크 |
| `detail` | `str \| None` | 예 | 상세 설명(메모). 기한 초과/24시간 이내 항목에만 채워지고, 그 외에는 `null` |

### `CourseGroup`

한 과목에 속한 항목들 — 브리핑 섹션 안에서 나타나는 순서를 유지합니다 (D-01).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `course_id` | `str` | 아니오 | 과목 고유 식별자 |
| `course_name` | `str` | 아니오 | 과목 전체 이름 |
| `course_abbr` | `str` | 아니오 | 과목 약칭 |
| `items` | `list[ReportItem]` | 아니오 (빈 배열 가능) | 이 과목에 속한 항목 목록 |

### `BriefingSections`

긴급도 순서로 나뉜 세 섹션: 기한 초과, 24시간 이내, 이후 일정 (D-01, D-05).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `overdue` | `list[CourseGroup]` | 아니오 (빈 배열 가능) | 기한이 지난 항목들, 과목별로 묶음. N일 컷오프 없음 (LMS가 미완료로 보고하는 한 모두 포함) |
| `due_within_24h` | `list[CourseGroup]` | 아니오 (빈 배열 가능) | 24시간 이내 마감 항목들 |
| `later` | `list[CourseGroup]` | 아니오 (빈 배열 가능) | 그 이후 일정 항목들 |

### `ErrorItem`

수집 오류 또는 치명적 오류 하나 — 안전한 허용목록(allowlist)을 거쳐 만들어집니다 (D-14).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `scope` | `Literal["fatal", "course", "notion"]` | 아니오 | 오류 범위. 열거값: `fatal`(실행 전체 중단), `course`(한 과목만 실패, 나머지는 계속), `notion`(Notion 동기화 중 한 항목 실패) |
| `code` | `str` | 아니오 | 오류 코드. 일반적인 값: `ConfigError`(설정 누락), `AuthenticationError`(LMS 로그인 실패), `UnsupportedLmsError`(Coursemos/Moodle 강의 목록 구조 미발견), `NavigationTimeoutError`(페이지 응답 지연), `CourseAccessDeniedError`(과목 접근 권한 없음), 그 외 예기치 않은 예외는 해당 예외 클래스 이름이 그대로 코드로 사용됨(RuntimeError 등). Notion 관련 코드: `duplicate_incoming_title`, `duplicate_existing_title`, `malformed_existing_page`(중복/손상 감지), 또는 `NotionAuthenticationError`/`NotionPermissionError`/`NotionTargetError`/`NotionSchemaError`/`NotionTransportError`(Notion API 오류 클래스 이름) |
| `message` | `str` | 아니오 | 사람이 읽는 오류 메시지. 절대 비밀값이나 원본 예외 텍스트를 그대로 포함하지 않음(허용목록을 거친 고정 문구) |
| `course_id` | `str \| None` | 예 | 관련 과목 ID (있는 경우) |
| `course_name` | `str \| None` | 예 | 관련 과목 이름 (있는 경우) |
| `task_title` | `str \| None` | 예 | 관련 작업 제목 (있는 경우) |

### `ReportNotice`

에이전트가 브리핑 전에 사용자에게 반드시 먼저 전달해야 하는 안내(비오류) 공지 (예: 수강 과목 미발견).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `code` | `str` | 아니오 | 안내 코드 (예: `no_courses_found`) |
| `message` | `str` | 아니오 | 사용자에게 표시할 안내 메시지 |

#### 안내 코드 (Notice Codes)

| 코드 | 의미 |
|------|------|
| `no_courses_found` | 로그인에는 성공했으나 수강 과목을 찾지 못함 (잘못된 `LMS_URL`이거나 해당 학기 수강 과목 없음). 종료 코드는 `0`을 유지하며, 에이전트는 요약(summary) 전에 이 안내 메시지를 반드시 사용자에게 표시해야 합니다. |

### `CheckReport`

`check` 명령의 버전이 명시된 JSON 봉투 — 원본 모델을 그대로 덤프한 것이 아닙니다 (D-13).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `schema_version` | `Literal[1]` (기본값 `1`) | 아니오 | 스키마 버전. 항상 `1` |
| `command` | `Literal["check"]` (기본값 `"check"`) | 아니오 | 실행된 명령 이름 |
| `generated_at` | `datetime` | 아니오 | 이 리포트를 생성한 시각 (KST) |
| `summary` | `ReportSummary` | 아니오 | 요약 카운트 |
| `items` | `BriefingSections` | 아니오 | 긴급도별 섹션 |
| `errors` | `list[ErrorItem]` | 아니오 (빈 배열 가능) | 수집 중 발생한 오류 목록 |
| `notices` | `list[ReportNotice]` | 아니오 (기본 빈 배열) | 사용자에게 브리핑 전에 먼저 안내해야 할 비오류 공지 목록 (예: `no_courses_found`) |

### `SyncChange`

변경된 Scheduler 속성 하나 — 변경 전/후를 표시용 문자열로 나타냅니다.

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `field` | `str` | 아니오 | 변경된 Notion 속성 이름 (예: `DueDate`) |
| `before` | `str \| None` | 예 | 변경 전 표시값 (`None`/`datetime.isoformat()`/`Enum.value`/기타는 `str()`) |
| `after` | `str \| None` | 예 | 변경 후 표시값 |

### `SyncCreateItem`

새 Scheduler 페이지로 생성될 작업.

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `task_id` | `str` | 아니오 | 작업 고유 식별자 |
| `title` | `str` | 아니오 | 생성될 페이지 제목 |
| `course_name` | `str` | 아니오 | 과목 이름 |
| `due_date` | `datetime \| None` | 예 | 마감일시 |

### `SyncUpdateItem`

허용된 필드만 부분 갱신될 기존 Scheduler 페이지.

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `task_id` | `str` | 아니오 | 작업 고유 식별자 |
| `title` | `str` | 아니오 | 페이지 제목 |
| `page_id` | `str` | 아니오 | 기존 Notion 페이지 ID |
| `notion_url` | `str` | 아니오 | 기존 페이지의 Notion URL |
| `changes` | `list[SyncChange]` | 아니오 (빈 배열 가능) | 변경될 속성 목록 |

### `SyncSkipItem`

의도적으로 변경하지 않고 건너뛴 작업.

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `task_id` | `str` | 아니오 | 작업 고유 식별자 |
| `title` | `str` | 아니오 | 작업 제목 |
| `page_id` | `str \| None` | 예 | 대응하는 기존 페이지 ID (있는 경우) |
| `notion_url` | `str \| None` | 예 | 대응하는 기존 페이지 URL (있는 경우) |
| `reason` | `str` | 아니오 | 건너뛴 이유: `unchanged`(변경 사항 없음), `notion_disabled`(Notion 미설정), `lms_completed`(LMS 완료 항목) |

### `SyncCounts`

생성/수정/건너뜀/오류의 합계 카운트.

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `total` | `int` | 아니오 | 전체 계획 건수 |
| `create` | `int` | 아니오 | 생성 예정/완료 건수 |
| `update` | `int` | 아니오 | 수정 예정/완료 건수 |
| `skip` | `int` | 아니오 | 건너뛴 건수 |
| `error` | `int` | 아니오 | 오류 건수 |

### `SyncSection`

JSON 계약 v1의 sync 절반 — 생성/수정/건너뜀 계획 (D-13, D-16).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `enabled` | `bool` | 아니오 | Notion 설정이 완료되어 동기화를 시도했는지 여부 |
| `dry_run` | `bool` | 아니오 | 미리보기 모드였는지 여부 (`--apply` 없이 실행하면 `true`) |
| `applied` | `bool` | 아니오 | 실제로 Notion에 반영되었는지 여부 (`enabled`이고 `dry_run`이 아닐 때만 `true`) |
| `target_title` | `str \| None` | 예 | 대상 Notion 데이터 소스의 제목 |
| `notice` | `str \| None` | 예 | Notion이 설정되지 않았을 때만 채워지는 안내 문구. `.env`의 `NOTION_TOKEN`, `NOTION_DATABASE_NAME` 또는 `NOTION_DATABASE_ID` 키 이름만 언급하며 값은 절대 포함하지 않음 |
| `create` | `list[SyncCreateItem]` | 아니오 (빈 배열 가능) | 생성될(된) 항목 목록 |
| `update` | `list[SyncUpdateItem]` | 아니오 (빈 배열 가능) | 수정될(된) 항목 목록 |
| `skip` | `list[SyncSkipItem]` | 아니오 (빈 배열 가능) | 건너뛴 항목 목록 |
| `counts` | `SyncCounts` | 아니오 | 합계 카운트 |

### `SyncReport`

`sync` 명령의 버전이 명시된 JSON 봉투 — 원본 `SyncResult`를 그대로 덤프한 것이 아닙니다 (D-13).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `schema_version` | `Literal[1]` (기본값 `1`) | 아니오 | 스키마 버전. 항상 `1` |
| `command` | `Literal["sync"]` (기본값 `"sync"`) | 아니오 | 실행된 명령 이름 |
| `generated_at` | `datetime` | 아니오 | 이 리포트를 생성한 시각 (KST) |
| `summary` | `ReportSummary` | 아니오 | 요약 카운트 (LMS 수집 결과 기준) |
| `sync` | `SyncSection \| None` | 예 | 동기화 계획. LMS 수집 단계에서 치명적 오류가 발생해 Notion 단계에 도달하지 못한 경우 `null` |
| `errors` | `list[ErrorItem]` | 아니오 (빈 배열 가능) | 수집 및 동기화 중 발생한 오류 목록 |
| `notices` | `list[ReportNotice]` | 아니오 (기본 빈 배열) | 사용자에게 브리핑 전에 먼저 안내해야 할 비오류 공지 목록 (예: `no_courses_found`) |

---

## 예시 페이로드

아래 예시는 실제 학생 데이터가 아닌, 완전히 가상의 데이터입니다.

### `check --json` 예시

```json
{
  "schema_version": 1,
  "command": "check",
  "generated_at": "2026-03-10T09:00:00+09:00",
  "summary": {
    "course_count": 2,
    "total_count": 2,
    "overdue_count": 1,
    "due_within_24h_count": 1,
    "later_count": 0,
    "error_count": 0
  },
  "items": {
    "overdue": [
      {
        "course_id": "course-example-1",
        "course_name": "예시자료구조",
        "course_abbr": "예자구",
        "items": [
          {
            "task_id": "task-example-1",
            "title": "[예자구] 2주차 강의 시청",
            "course_id": "course-example-1",
            "course_name": "예시자료구조",
            "course_abbr": "예자구",
            "task_type": "lecture",
            "due_date": "2026-03-08T23:59:00+09:00",
            "remaining_minutes": -1440,
            "remaining_text": "1일 0시간 지남",
            "lms_url": "https://lms.example.ac.kr/course/example-1/lecture/2",
            "detail": "예시 강의 설명입니다."
          }
        ]
      }
    ],
    "due_within_24h": [
      {
        "course_id": "course-example-2",
        "course_name": "예시운영체제",
        "course_abbr": "예운체",
        "items": [
          {
            "task_id": "task-example-2",
            "title": "[예운체] 과제3 제출",
            "course_id": "course-example-2",
            "course_name": "예시운영체제",
            "course_abbr": "예운체",
            "task_type": "assignment",
            "due_date": "2026-03-10T20:00:00+09:00",
            "remaining_minutes": 660,
            "remaining_text": "11시간 0분 남음",
            "lms_url": "https://lms.example.ac.kr/course/example-2/assignment/3",
            "detail": "예시 과제 설명입니다."
          }
        ]
      }
    ],
    "later": []
  },
  "errors": [],
  "notices": []
}
```

### `sync --json` (미리보기) 예시

```json
{
  "schema_version": 1,
  "command": "sync",
  "generated_at": "2026-03-10T09:00:05+09:00",
  "summary": {
    "course_count": 2,
    "total_count": 2,
    "overdue_count": 1,
    "due_within_24h_count": 1,
    "later_count": 0,
    "error_count": 0
  },
  "sync": {
    "enabled": true,
    "dry_run": true,
    "applied": false,
    "target_title": "Scheduler",
    "notice": null,
    "create": [
      {
        "task_id": "task-example-1",
        "title": "[예자구] 2주차 강의 시청",
        "course_name": "예시자료구조",
        "due_date": "2026-03-08T23:59:00+09:00"
      }
    ],
    "update": [
      {
        "task_id": "task-example-2",
        "title": "[예운체] 과제3 제출",
        "page_id": "example-page-id-2",
        "notion_url": "https://www.notion.so/examplepageid2",
        "changes": [
          {
            "field": "DueDate",
            "before": "2026-03-09T20:00:00+09:00",
            "after": "2026-03-10T20:00:00+09:00"
          }
        ]
      }
    ],
    "skip": [],
    "counts": {
      "total": 2,
      "create": 1,
      "update": 1,
      "skip": 0,
      "error": 0
    }
  },
  "errors": [],
  "notices": []
}
```

### `WatchResult`

`watch` 명령의 실행 결과 객체입니다 (`src/coursepilot/player/runner.py`).

`watch` 기본 실행은 Notion을 변경하지 않습니다. 사용자가 재생과 완료 처리를 함께 명시한 경우 `watch --update-notion`은 실제 시청 완료된 영상의 매칭된 Scheduler 작업만 갱신합니다. 시청만 요청했다면 `watch sync-notion --dry-run --json`의 `planned_tasks`/`planned_count`로 완료 변경 대상을 확인하고, 승인 후 동일한 제목을 반복 `--task-title`로 지정해 적용합니다. 미리보기는 `dry_run: true`, `synced_count: 0`, 빈 `synced_tasks`를 반환하며 Notion이나 로컬 시청 이력을 수정하지 않습니다. `already_completed_tasks`는 Notion에서 이미 완료된 항목, `unmatched_tasks`는 해당 제목의 Scheduler 페이지가 없는 항목, `ambiguous_tasks`는 동일 제목 페이지가 둘 이상이라 안전하게 제외한 항목입니다. 실제 적용 결과는 `dry_run: false`와 `synced_tasks`/`synced_count`로 확인합니다.

`watch scheduler-tasks --json`은 읽기 전용으로 미완료 강의 작업을 `tasks`(각 `title`, `course_abbr`, `week`, `clip`)와 `count`, `ambiguous_tasks`, `read_only: true`로 반환합니다. `watch --task-title`은 생성된 강의 작업명이 정확히 일치하는 미시청 영상만 선택합니다.

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `course_id` | `str` | 아니오 | 대상 과목 고유 식별자 |
| `course_name` | `str` | 아니오 | 대상 과목 전체 이름 |
| `target_week` | `str` | 아니오 | 시청 대상 주차 (`current`, `all`, 또는 `4` 등) |
| `total_vods` | `int` | 아니오 | 이번 실행에서 감지된 시청 대상 미완료 VOD 수 |
| `completed_vods` | `int` | 아니오 | 이번 실행에서 정상적으로 시청을 완료한 VOD 수 |
| `skipped_vods` | `int` | 아니오 | 이미 수강 완료되어 건너뛴 VOD 수 |
| `playback_results` | `list[PlaybackProgress]` | 아니오 (빈 배열 가능) | 개별 VOD 시청 진행/완료 상세 결과 목록 |
| `notion_updated_count` | `int` | 아니오 | `--update-notion` 플래그 활성화 시 '완료' 상태로 업데이트된 Notion 페이지 수 |
| `dry_run` | `bool` | 아니오 | 미리보기 모드 여부 (`--dry-run` 플래그) |
| `error_message` | `str \| None` | 예 | 과목 탐색 실패 또는 실행 오류 메시지 (성공 시 `null`) |

### `PlaybackProgress`

개별 VOD 영상의 재생 진행 상황 및 결과입니다 (`src/coursepilot/player/models.py`).

| 필드 | 타입 | Nullable | 의미 |
|------|------|----------|------|
| `vod_url` | `str` | 아니오 | VOD 접속 링크 URL |
| `title` | `str` | 아니오 | 영상 제목 |
| `duration` | `float` | 아니오 | 영상 전체 길이(초) |
| `current_time` | `float` | 아니오 | 최종 재생 위치(초) |
| `progress_percent` | `float` | 아니오 | 시청 진행률 (%) |
| `is_completed` | `bool` | 아니오 | 시청 완료 여부 (출석 인정 조건 충족) |
| `is_paused` | `bool` | 아니오 | 영상 일시정지 여부 |
| `error_message` | `str \| None` | 예 | 개별 영상 재생 실패 시 오류 메시지 |

### `watch --json` 예시

```json
{
  "course_id": "84321",
  "course_name": "기초전자실험",
  "target_week": "current",
  "total_vods": 2,
  "completed_vods": 2,
  "skipped_vods": 1,
  "playback_results": [
    {
      "vod_url": "https://lxp.kau.ac.kr/mod/vod/view.php?id=12345",
      "title": "[기전실] 4주차 1강: 오실로스코프 사용법",
      "duration": 1500.0,
      "current_time": 1500.0,
      "progress_percent": 100.0,
      "is_completed": true,
      "is_paused": false,
      "error_message": null
    },
    {
      "vod_url": "https://lxp.kau.ac.kr/mod/vod/view.php?id=12346",
      "title": "[기전실] 4주차 2강: 함수발생기 실습",
      "duration": 1800.0,
      "current_time": 1800.0,
      "progress_percent": 100.0,
      "is_completed": true,
      "is_paused": false,
      "error_message": null
    }
  ],
  "notion_updated_count": 2,
  "dry_run": false,
  "error_message": null
}
```
