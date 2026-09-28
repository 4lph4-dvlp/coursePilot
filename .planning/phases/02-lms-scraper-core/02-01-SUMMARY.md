---
phase: "02"
plan: "01"
subsystem: "scraper"
tags:
  - scraper-models
  - course-list
  - navigator
  - debug-dump
  - coursemos
  - bs4
  - lxml
requires:
  - "01-01"
  - "01-02"
provides:
  - CourseItem
  - LectureItem
  - AssessmentItem
  - AttachmentMeta
  - AttendanceStatus
  - SubmissionStatus
  - AssessmentType
  - clean_course_name
  - extract_courses_from_html
  - extract_courses
  - CourseNavigator
  - capture_debug_snapshot
affects:
  - "02-02"
  - "03"
---

# Plan 02-01 Summary: Scraper Core Models, Course List Extractor, Page Navigator & Debug Snapshot

## Executive Summary

Phase 2 Wave 1의 첫 번째 실행 계획(02-01)을 성공적으로 완료했습니다. 고속 파싱을 위한 `beautifulsoup4` 및 `lxml` 의존성을 추가하고, 스크래퍼 핵심 DTO 데이터 모델(`CourseItem`, `LectureItem`, `AssessmentItem` 등)을 선언했습니다. KAU Coursemos 대시보드 구조에 최적화된 강좌 목록 추출 및 분반/학기 표기 정제 정규식 엔진(`clean_course_name`, `extract_courses_from_html`)을 구현하였으며, 2단계 페이지 네비게이터(`CourseNavigator`)와 예외 상황 자동 덤퍼(`capture_debug_snapshot`)를 완성했습니다. 총 21개의 단위 테스트가 100% 통과(Green)함을 검증했습니다.

## Tasks Completed

### Task 02-01-01: Scraper Dependencies & Core DTO Models (SCRP-02, SCRP-03, SCRP-04)
- `pyproject.toml`: `beautifulsoup4>=4.12.0`, `lxml>=5.2.0` 의존성 추가 및 `uv sync` 적용
- `src/coursepilot/scraper/__init__.py`: 스크래퍼 패키지 진입점 생성
- `src/coursepilot/scraper/models.py`: Pydantic v2 DTO 모델 및 Enum 선언 (`AttendanceStatus`, `SubmissionStatus`, `AssessmentType`, `CourseItem`, `LectureItem`, `AttachmentMeta`, `AssessmentItem`)
- `tests/test_scraper_models.py`: 8개 테스트 케이스 작성 및 통과 검증 (기본값, 타입 검증, 직렬화/역직렬화)
- **Commit:** `feat(02-01): scraper dependencies and core dto models` (`e6109d8`)

### Task 02-01-02: Course List Extractor & Name Sanitization (SCRP-02, D-01, D-02, D-04)
- `tests/fixtures/dashboard_coursemos.html`: KAU Coursemos 대시보드(진행 중 강좌, 종료 강좌, Canvas 링크, 분반/학기 태그) 모의 HTML fixture 작성
- `src/coursepilot/scraper/course_list.py`: 분반 및 학기 표기를 분리/정제하는 `clean_course_name`, 과거 강좌 필터링 및 중복 ID 제거 기능의 `extract_courses_from_html`, 캐시 주입 및 스마트 대기를 지원하는 `extract_courses` 구현
- `tests/test_course_list.py`: 4개 테스트 케이스 작성 및 통과 검증 (다양한 정규식 과목명 정제, fixture 파싱 및 종료 강좌 필터링, 캐시 주입, 네비게이션)
- **Commit:** `feat(02-01): course list extractor and name sanitization` (`e18e464`)

### Task 02-01-03: Page Navigator, Smart Wait, WAF Delays & Failure Debug Dumper (D-03, D-13, D-14, D-15, D-16)
- `src/coursepilot/exceptions.py`: `CourseAccessDeniedError` 추가
- `src/coursepilot/scraper/debug_dump.py`: 실패 화면 캡처 및 HTML 저장 함수 `capture_debug_snapshot` 구현 (타임스탬프 파일명, 크래시 방지)
- `src/coursepilot/scraper/navigator.py`: `CourseNavigator` 구현 (0.2~0.5초 WAF 차단 방지 미세 딜레이, 15초 스마트 명시적 대기, 권한 없는 강좌 격리 및 스킵, 진도표 우선 및 메인 홈 폴백)
- `tests/test_debug_dump.py`: 2개 테스트 케이스 작성 및 통과 검증
- `tests/test_navigator.py`: 7개 테스트 케이스 작성 및 통과 검증 (정상 이동, 403 차단 및 경고 박스 감지, 진도표 폴백, 과제 모아보기 이동)
- **Commit:** `feat(02-01): page navigator, smart wait, waf delays and debug snapshot dumper` (`464f99b`)

## Deviations & Adaptations

- `extract_courses_from_html`에서 `h3.coursename`에 감싸인 `a` 태그 처리 시 상위 `div.course_box`를 정상 감지하도록 탐색 계층을 상위 카드 컨테이너 우선으로 보강하여 종료된 강좌가 확실하게 필터링되도록 개선함.

## Verification Results

- `uv run pytest tests/test_scraper_models.py tests/test_course_list.py tests/test_navigator.py tests/test_debug_dump.py -v`:
  - 21 passed in 0.32s (100% Green)
- 전체 테스트 슈트: 42 passed in 0.50s (회귀 없음)

## Key Files Created/Modified

- `pyproject.toml`: bs4, lxml 의존성 추가
- `src/coursepilot/scraper/__init__.py`: 스크래퍼 패키지 노출
- `src/coursepilot/scraper/models.py`: DTO 데이터 모델
- `src/coursepilot/scraper/course_list.py`: 강좌 목록 추출 및 과목명 정제
- `src/coursepilot/scraper/navigator.py`: 스마트 대기 및 2단계 네비게이터
- `src/coursepilot/scraper/debug_dump.py`: 디버그 스냅샷 유틸리티
- `src/coursepilot/exceptions.py`: CourseAccessDeniedError 예외 추가
- `tests/fixtures/dashboard_coursemos.html`: 대시보드 모의 fixture
- `tests/test_scraper_models.py`: 데이터 모델 테스트
- `tests/test_course_list.py`: 강좌 목록 테스트
- `tests/test_navigator.py`: 네비게이터 테스트
- `tests/test_debug_dump.py`: 디버그 스냅샷 테스트

## Self-Check: PASSED
- [x] 모든 3개 태스크 구현 완료
- [x] 각 태스크별 원자적 커밋 완료
- [x] 테스트 21/21 통과
- [x] SUMMARY.md 작성 완료
