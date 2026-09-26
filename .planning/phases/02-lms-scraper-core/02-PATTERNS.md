# Phase 2: LMS Scraper Core - Pattern Mapping

**Generated:** 2026-09-21  
**Phase:** 02-lms-scraper-core  
**Status:** Complete  

---

## 1. Codebase Status & Architectural Context

Phase 1에서 구축한 인프라(`SessionManager`, `auth.py`, `course_mapping.py`, `config.py`)를 기반으로, Phase 2는 실질적인 데이터 수집 엔진인 `src/coursepilot/scraper/` 서브패키지를 구축합니다.
- **인증 분리:** 모든 스크래퍼는 자체 로그인 로직을 갖지 않고 `SessionManager`로부터 인증된 Playwright `Page` 객체를 주입받아 사용합니다.
- **하이브리드 파싱:** 브라우저 탐색 및 스마트 대기는 Playwright가 수행하고, 복잡한 DOM 테이블 파싱은 `page.content()` + `BeautifulSoup4` 인메모리 파서로 수행하여 IPC 지연을 최소화합니다.
- **안전한 격리:** 개별 강좌/페이지 수집 실패 시 전체 루프가 다운되지 않고 경고 로그 및 `.cache/debug/` 디버그 스냅샷을 남긴 뒤 계속 진행합니다.

---

## 2. File Pattern Mapping

| Target File | Pattern Archetype | Reference in 02-RESEARCH.md | Primary Responsibilities |
|-------------|-------------------|-----------------------------|--------------------------|
| `src/coursepilot/scraper/__init__.py` | Package Root | Standard Python convention | 패키지 공개 API export (`CourseListScraper`, `LectureParser`, `AssessmentParser`, `CourseNavigator`, `capture_debug_snapshot`) |
| `src/coursepilot/scraper/models.py` | Data Transfer Objects (DTO) | Section: Architecture Patterns (Data Models) | `CourseItem`, `LectureItem`, `AssessmentItem`, `AttachmentMeta`, 상태 Enum(`AttendanceStatus`, `SubmissionStatus`, `AssessmentType`) |
| `src/coursepilot/scraper/debug_dump.py` | Operational Diagnostics | Section: Pattern 4 (Debug Snapshotting) | 실패 시점 `.cache/debug/{timestamp}_{action}.png` 및 `.html` 파일 덤프 |
| `src/coursepilot/scraper/date_parser.py` | Tolerant Text Parser | Section: Pattern 2 (Date Parser) | 다중 정규식 한국어/표준 날짜 파싱, 주차 기준 일요일 23:59:59 폴백 |
| `src/coursepilot/scraper/course_list.py` | DOM Extractor | Section: Code Examples (Course List) | 대시보드(`/my/`) 강좌 목록 추출, '진행 중'/학기 텍스트 필터링, 정규식 과목명 정제 (SCRP-02) |
| `src/coursepilot/scraper/navigator.py` | Web Flow Orchestrator | Section: Architecture Patterns | 과목별 진도표/모아보기/메인홈 순차 이동, 스마트 대기, 0.2~0.5초 WAF 차단 방지 슬립, 권한 없음 과목 스킵 |
| `src/coursepilot/scraper/lecture_parser.py` | Specialized DOM Parser | Section: Code Examples (Lecture) | 주차별 동영상 클립(차시) 분할, 출석 마크('O') 및 진도율(%) 하이브리드 판정, 지연 과목 플래깅 (SCRP-03) |
| `src/coursepilot/scraper/assessment_parser.py` | Deep DOM Extractor | Section: Architecture Patterns | 과제/퀴즈/토론 목록 수집, 과제 상세 페이지 본문 안내문 및 첨부파일 메타데이터 추출, 제출 완료 상태 판정 (SCRP-04) |
| `tests/fixtures/*.html` | Test Fixtures | Section: Validation Architecture | Coursemos 대시보드, 진도표, 과제 목록, 과제 상세 샘플 HTML 스냅샷 |
| `tests/test_scraper_models.py` | Model Unit Tests | Section: Validation Architecture | DTO 스키마, 기본값 및 Enum 변환 검증 |
| `tests/test_date_parser.py` | Date Parser Unit Tests | Section: Validation Architecture | 다중 포맷 날짜 파싱 및 일요일 폴백 검증 |
| `tests/test_course_list.py` | Course List Unit Tests | Section: Validation Architecture | 대시보드 파싱, 분반/학기 필터링 정규식 검증 |
| `tests/test_navigator.py` | Navigator Unit Tests | Section: Validation Architecture | 진도표 우선 및 메인홈 폴백 네비게이션, 권한 에러 과목 스킵 검증 |
| `tests/test_lecture_parser.py` | Lecture Parser Unit Tests | Section: Validation Architecture | 다중 차시 분할, 출석/진도율 판정, 마감 기한 검증 |
| `tests/test_assessment_parser.py` | Assessment Unit Tests | Section: Validation Architecture | 과제/퀴즈 목록, 본문/첨부파일 메타데이터, 제출/미제출 검증 |
| `tests/test_debug_dump.py` | Debug Dump Unit Tests | Section: Validation Architecture | 스크린샷 및 HTML 스냅샷 저장 검증 |

---

## 3. Detailed Architectural Patterns & Code Blueprints

### Pattern 1: Safe Sequential Course Processing (D-03, D-15)
```python
def scrape_all_courses(page: Page, courses: list[CourseItem]) -> dict:
    results = {}
    for course in courses:
        try:
            logger.info("과목 수집 시작: %s (%s)", course.clean_name, course.course_id)
            course_data = navigator.navigate_course(page, course)
            results[course.course_id] = course_data
        except CourseAccessDeniedError:
            logger.warning("과목 접근 권한 없음(스킵): %s", course.clean_name)
            continue
        except Exception as e:
            logger.error("과목 파싱 중 오류 발생: %s - %s", course.clean_name, e)
            capture_debug_snapshot(page, f"error_{course.course_id}")
            continue
        finally:
            # WAF 차단 방지 미세 딜레이
            time.sleep(random.uniform(0.2, 0.4))
    return results
```

### Pattern 2: Multi-Clip Lecture Splitting (D-07)
```python
# 1개 섹션/주차 내에 여러 개의 영상 액티비티가 존재할 경우:
for idx, act in enumerate(section.select(".activity.vod"), start=1):
    items.append(LectureItem(
        course_id=course_id,
        week_number=week,
        clip_number=idx,
        title=f"{idx}차시: {clean_title}",
        full_title=f"[{course_short}] {week}주차 {idx}차시: {clean_title}",
        ...
    ))
```

### Pattern 3: Assessment Deep Parsing (D-11, D-12)
```python
# 모아보기 목록 테이블에서 기본 정보 수집 후 상세 URL로 방문
page.goto(assign_url)
page.wait_for_selector("#region-main", timeout=10000)
detail_soup = BeautifulSoup(page.content(), "html.parser")
desc = detail_soup.select_one(".box.generalbox, .submissionstatustable")
# 첨부파일 메타 추출
attachments = []
for file_link in detail_soup.select(".fileuploadsubmission a, .intro a"):
    attachments.append(AttachmentMeta(filename=file_link.text.strip(), url=file_link.get("href", "")))
```

---

*Phase: 02-lms-scraper-core*
*Patterns mapped: 2026-09-21*
