---
phase: "02"
plan: "02"
subsystem: "scraper"
tags:
  - date-parser
  - lecture-parser
  - assessment-parser
  - attendance-hybrid
  - overdue-detection
  - deep-scraping
requires:
  - "02-01"
provides:
  - parse_lms_date
  - is_past_deadline
  - parse_lectures_from_progress_table
  - parse_lectures_from_course_sections
  - clean_lecture_title
  - parse_assessment_list
  - enrich_assessment_detail
  - scrape_course_assessments
affects:
  - "03"
  - "04"
---

# Plan 02-02 Summary: Lecture Progress Parser, Assessment Deep Parser & Resilient Date Parser

## Executive Summary

Phase 2 Wave 2의 두 번째 실행 계획(02-02)을 완벽히 완료했습니다. 다중 정규식 기반 KST 표준화 및 주차 일요일 폴백 날짜 파서(`date_parser.py`), 주차 내 개별 차시 분할 및 출석 마크('O')와 진도율(100%) 하이브리드 판정, 과거 지연 강의 전수 추출(`lecture_parser.py`), 그리고 과제/퀴즈 요약 및 상세 본문/첨부파일/지각 마감일 전수 추출(`assessment_parser.py`)을 구현했습니다. 총 11개의 신규 단위 테스트를 포함해 프로젝트 전체 59개의 테스트가 100% Green 통과함을 검증했습니다.

## Tasks Completed

### Task 02-02-01: Flexible Multi-Pattern Date Parser & Weekly Fallback (D-08)
- `src/coursepilot/scraper/date_parser.py`: 한국 표준시(KST) 타임존 상수, 다중 포맷(ISO, 온점 구분, 한글 날짜, 날짜 범위 `~`, 요일 표기) 파싱 함수 `parse_lms_date` 구현
- 주차 일요일 23:59:59 KST 안전 폴백 로직(`_apply_fallback`) 및 마감 경과 판별 함수 `is_past_deadline` 구현
- `tests/test_date_parser.py`: 5개 테스트 케이스 작성 및 검증
- **Commit:** `feat(02-02): flexible multi-pattern date parser and weekly fallback` (`87af07c`)

### Task 02-02-02: Lecture Video & Clip Parser with Attendance/Progress Hybrid Check (SCRP-03, D-05, D-06, D-07)
- `tests/fixtures/progress_report.html`: Coursemos 학습현황/진도표(다중 차시, 출석 'O', 100% 진도, 마감 경과 지연 강의) 모의 HTML fixture 작성
- `src/coursepilot/scraper/lecture_parser.py`: 주차 내 개별 차시 분할 및 표준 제목 포맷(`[{course}] {week}주차 {clip}차시: {title}`), 출석 마크 우선 + 진도율 100% 보조 하이브리드 판정(`parse_lectures_from_progress_table`), 메인 홈 주차별 섹션 폴백 파서(`parse_lectures_from_course_sections`) 구현
- `tests/test_lecture_parser.py`: 3개 테스트 케이스 작성 및 검증
- **Commit:** `feat(02-02): lecture video and clip parser with hybrid attendance evaluation` (`a12dfd8`)

### Task 02-02-03: Assessment Parser with Deep Detail Extraction & Status Detection (SCRP-04, D-09, D-10, D-11, D-12)
- `tests/fixtures/assignment_list.html` & `tests/fixtures/assignment_detail.html`: 과제/퀴즈 모아보기 및 상세 안내문, 첨부파일, 지각 제출 마감일 모의 fixture 작성
- `src/coursepilot/scraper/assessment_parser.py`: 과제/평가 목록 파서(`parse_assessment_list`, 제출완료/채점완료/임시저장/미제출 정밀 매핑), 상세 안내문 본문/첨부파일/지각마감일 추출기(`enrich_assessment_detail`), 순차 순회 탐색기(`scrape_course_assessments`) 구현
- `src/coursepilot/scraper/__init__.py`: 스크래퍼 전체 공개 API 심볼 re-export
- `tests/test_assessment_parser.py`: 3개 테스트 케이스 작성 및 검증
- **Commit:** `feat(02-02): assessment deep parser with submission status detection and detail enrichment` (`778a61d`)

## Deviations & Adaptations

- Windows 기본 환경에서 IANA tzdata가 부재할 경우 `zoneinfo.ZoneInfo("Asia/Seoul")`에서 `ZoneInfoNotFoundError`가 발생할 수 있으므로, `datetime.timezone(timedelta(hours=9), name="KST")`로 안전하게 폴백하도록 방어 로직을 추가하여 운영체제 종속성을 제거함.

## Verification Results

- `uv run pytest tests/test_date_parser.py tests/test_lecture_parser.py tests/test_assessment_parser.py -v`:
  - 11 passed in 0.46s (100% Green)
- 전체 프로젝트 테스트 스위트 (`uv run pytest -v`):
  - 59 passed in 0.62s (100% Green, 무결함)

## Key Files Created/Modified

- `src/coursepilot/scraper/date_parser.py`: 유연한 다중 정규식 날짜 파서
- `src/coursepilot/scraper/lecture_parser.py`: 강의 차시 분할 및 하이브리드 수강 판정기
- `src/coursepilot/scraper/assessment_parser.py`: 평가 항목 상세 본문/첨부파일 파서
- `src/coursepilot/scraper/__init__.py`: 패키지 공개 API
- `tests/fixtures/progress_report.html`: 진도표 HTML fixture
- `tests/fixtures/assignment_list.html`: 과제 목록 HTML fixture
- `tests/fixtures/assignment_detail.html`: 과제 상세 HTML fixture
- `tests/test_date_parser.py`: 날짜 파서 테스트
- `tests/test_lecture_parser.py`: 강의 파서 테스트
- `tests/test_assessment_parser.py`: 평가 파서 테스트

## Self-Check: PASSED
- [x] 모든 3개 태스크 구현 완료
- [x] 각 태스크별 원자적 커밋 완료
- [x] 테스트 59/59 통과
- [x] SUMMARY.md 작성 완료
