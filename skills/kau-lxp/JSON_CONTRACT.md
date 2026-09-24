# kau-lxp CLI JSON 계약 v1 (JSON Contract v1)

이 문서는 `python -m kau_assistant check --json`과 `python -m kau_assistant sync --json`이 표준출력(stdout)에 출력하는 JSON의 정확한 구조를 설명합니다. 실제 소스는 `src/kau_assistant/report_models.py`의 Pydantic 모델이며, 이 문서는 그 모델을 사람이 읽을 수 있게 옮긴 참조 자료입니다. `skills/kau-lxp/SKILL.md`는 이 문서를 가리킵니다.

## 버전 규칙 (Versioning)

- 현재 스키마 버전은 `schema_version: 1`입니다.
- **선택적(optional) 필드를 추가하는 것**은 `schema_version`을 그대로 `1`로 유지합니다 (`notices` 필드는 v1 하에서 선택적 필드로 추가되었습니다).
- **필드 이름 변경, 필드 제거, 필드 타입 변경**은 반드시 `schema_version`을 올립니다 (breaking change).
- 이 스키마를 파싱하는 모든 에이전트는 `schema_version`을 먼저 확인하고, 알지 못하는 값이면 파싱을 중단하고 사람에게 알려야 합니다.

## 호출 방식과 스트림 (Invocation & Streams)

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
| `total_count` | `int` | 아니오 | 전체 미완료 항목 수 |
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
| `reason` | `str` | 아니오 | 건너뛴 이유. 열거값: `unchanged`(변경 사항 없음), `notion_disabled`(Notion 미설정) |

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
