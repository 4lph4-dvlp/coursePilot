---
phase: 15-course-announcements-q-a-board-briefing
verified: 2026-09-26T02:50:00Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification: []
re_verification: null
---

# Phase 15: Course Announcements & Q&A Board Briefing Verification Report

**Phase Goal:** 과목별 공지사항(`ubboard`) 및 Q&A 게시판의 질의응답 내역을 빠짐없이 스크랩하여 터미널 브리핑, 단독 뷰어, 로컬 읽음 상태 관리(`board_read_state.json`), CLI 명령을 제공
**Verified:** 2026-09-26T02:50:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | BRD-01, D-15-01, D-15-04, D-15-07, D-15-16: 과목별 공지사항 게시판(`ubboard`)의 최근 공지글 목록(번호, 제목, 작성자, 작성일, 조회수) 및 본문/첨부파일 메타데이터를 추출하고, 불필요한 네트워크 트래픽을 방지하는 List-first 전략을 준수한다 | ✓ VERIFIED | `parse_board_list` in `board_parser.py` extracts 5-column notices without fetching article HTML by default; title accesshide decomposition implemented; `tests/test_board_parser.py` passes. |
| 2 | BRD-01, D-15-08, D-15-09: 공지사항 단독 뷰어(`--view <id>`) 및 상세 조회(`--detail`) 시 게시글 본문 HTML을 CP949 안전 마크다운으로 변환하여 출력하고, Phase 13 다운로더를 연동한 첨부파일 다운로드(`--download-attachments`)를 지원한다 | ✓ VERIFIED | `html_to_markdown` in `text_converter.py` normalizes `\xa0` and translates tables/links/formatting; `tests/test_board_text_converter.py` (6 tests) and `tests/test_board_runner.py::test_runner_fetch_article_detail_and_download` pass. |
| 3 | BRD-02, D-15-02, D-15-05, D-15-06: 과목별 Q&A 게시판의 질문 목록, 6열 테이블 구조, 답변 상태(답변완료/답변대기/내 질문), 비밀글 여부, 공식 답변/댓글 본문을 정확히 파싱한다 | ✓ VERIFIED | `parse_board_list` recognizes 6-column Q&A tables, extracts answer badges, detects secret post lock icons, and parses comments/replies in `parse_article_detail`; `tests/test_board_parser.py` (12 tests) pass. |
| 4 | BRD-02, D-15-10, D-15-11, D-15-12: 로컬 읽음 상태 관리자(`board_read_state.json`)는 원자적 파일 교체(`*.tmp` -> rename)와 과목별 LRU 200건 캡핑을 보장하여 데이터 손실 및 무제한 증가를 방지한다 | ✓ VERIFIED | `BoardReadStateManager` in `read_state.py` implements atomic write with replace and LRU eviction keeping 200 newest entries per course; `tests/test_board_read_state.py` (6 tests) pass. |
| 5 | BRD-01, BRD-02, D-15-13, D-15-14, D-15-15: 통합 CLI `board` 및 단독 편의 서브커맨드 `notices`, `qna`를 제공하며, Notion Scheduler DB에는 일체 연결하거나 수정하지 않고 CLI 및 JSON 브리핑 전용으로 동작한다 | ✓ VERIFIED | Click commands `board`, `notices`, `qna` registered in `cli.py` with shared options decorator; no Notion DB write operations performed; `tests/test_cli_board.py` (6 tests) pass. |
| 6 | BRD-02, D-15-03, D-15-04, D-15-14: 다중 필터(`--unread-only`, `--unanswered`, `--my`, `--course`)와 스트림 분리(진행/로그는 stderr, 결과/JSON은 stdout)를 제공하며, `schema_version: 1` 정형 JSON 출력을 지원한다 | ✓ VERIFIED | `run_board_collection` applies all filter predicates and returns `BoardRunResult`; CLI formats UTF-8 unescaped JSON or Rich tables to stdout and progress to stderr; exit codes 0/1/2 handled; `tests/test_board_runner.py` and `tests/test_cli_board.py` pass. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/coursepilot/board/models.py` | BoardItem, BoardComment, BoardAttachment, BoardRunResult, BoardReadState with schema_version: 1 | ✓ VERIFIED | Defined all Pydantic models with `extra="forbid"`, proper field typing, and JSON contracts. |
| `src/coursepilot/board/text_converter.py` | CP949-safe HTML to Markdown converter | ✓ VERIFIED | Implemented `html_to_markdown` normalizing NBSP, handling tables, links, emphasis, and code. |
| `src/coursepilot/scraper/board_parser.py` | Coursemos ubboard list and article parser | ✓ VERIFIED | Implemented `parse_board_list` (5-col notice, 6-col Q&A), `parse_article_detail`, secret post detection. |
| `src/coursepilot/board/read_state.py` | Atomic JSON read state manager with LRU capping | ✓ VERIFIED | Implemented `BoardReadStateManager` with `.tmp -> replace` atomic updates and 200 entry/course LRU. |
| `src/coursepilot/board/runner.py` | Multi-course collection pipeline with error isolation and attachment downloading | ✓ VERIFIED | Implemented `run_board_collection` and `fetch_and_format_article` with Phase 13 downloader integration. |
| `src/coursepilot/board/reporter.py` | Rich terminal presentation with status badges and article view | ✓ VERIFIED | Implemented `render_board_report` and `render_article_detail` with Korean badges and muted lines. |
| `src/coursepilot/cli.py` | Click CLI commands `board`, `notices`, `qna` | ✓ VERIFIED | Registered commands with shared options, stream separation (stderr/stdout), and exit codes. |
| `tests/test_board_text_converter.py` | Unit tests for text converter | ✓ VERIFIED | 6 tests passing. |
| `tests/test_board_parser.py` | Unit tests for board parser | ✓ VERIFIED | 12 tests passing. |
| `tests/test_board_read_state.py` | Unit tests for read state manager | ✓ VERIFIED | 6 tests passing. |
| `tests/test_board_runner.py` | Unit tests for board runner pipeline | ✓ VERIFIED | 4 tests passing. |
| `tests/test_cli_board.py` | CLI command integration tests | ✓ VERIFIED | 6 tests passing. |

### Test Summary

- Phase 15 targeted suite: 34 passed in 1.82s across 5 test modules.
- Project regression suite: `uv run pytest` -> 363 passed in 15.08s (0 failed, 0 regressions).
