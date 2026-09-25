---
phase: 15-course-announcements-q-a-board-briefing
plan: "01"
subsystem: board
tags:
  - models
  - scraper
  - text-converter
  - read-state
  - pydantic
requires: []
provides:
  - board-domain-models
  - board-html-scraper
  - board-text-converter
  - atomic-read-state
affects:
  - "15-02"
tech-stack.added: []
patterns:
  - AST HTML cleaning
  - CP949 safe normalization
  - Dynamic column mapping
  - Atomic temp file replacement
  - LRU FIFO eviction
key-files.created:
  - src/kau_assistant/board/__init__.py
  - src/kau_assistant/board/models.py
  - src/kau_assistant/scraper/board_parser.py
  - src/kau_assistant/board/text_converter.py
  - src/kau_assistant/board/read_state.py
  - tests/test_board_parser.py
  - tests/test_board_text_converter.py
  - tests/test_board_read_state.py
key-decisions:
  - "D-15-04: Enforce schema_version: 1 and extra='forbid' across all board domain models."
  - "D-15-07: Use BeautifulSoup AST transformations and normalize \\xa0 to standard spaces for Windows CP949 compatibility."
  - "D-15-12: Classify Coursemos ubboard/forum modules automatically by keyword matching with custom name override."
  - "D-15-14: Atomically persist read post IDs per course using .tmp replace."
  - "D-15-15: Cap stored read post IDs at 200 per course using LRU/FIFO eviction."
requirements:
  - BRD-01
  - BRD-02
coverage:
  - deliverable: "Board domain models & JSON contract (schema_version: 1)"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_board_parser.py#test_board_report_schema_version_validation"
      status: pass
  - deliverable: "Coursemos board module discovery and dynamic table parser"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_board_parser.py#test_extract_board_modules"
      status: pass
  - deliverable: "HTML to Markdown converter with Windows CP949 safety"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_board_text_converter.py#test_non_breaking_space_replacement"
      status: pass
  - deliverable: "Atomic read state manager with LRU 200 capping"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_board_read_state.py#test_read_state_lru_capping"
      status: pass
duration: "6 min"
completed: "2026-09-26T02:37:00Z"
---

# Phase 15 Plan 01: Domain Models, Coursemos Scraper, HTML-to-Markdown Text Converter & Atomic Read State Manager Summary

Pydantic domain models with schema_version: 1 JSON contract envelope, Coursemos ubboard/forum scraper, CP949-safe Markdown converter, and atomic LRU 200 read state manager.

## Accomplishments

- **Pydantic Domain Models & Contract (`board/models.py`, `board/__init__.py`):**
  - Implemented typed models with `extra="forbid"`: `BoardType`, `BoardModuleInfo`, `BoardAttachmentItem`, `BoardReplyItem`, `BoardPostItem`, `CourseBoardGroup`, `BoardSummary`, `BoardReport` (`schema_version: 1`), and `BoardArticleDetail`.
  - Added unit test suite in `tests/test_board_parser.py` validating default factories, JSON round-tripping, and strict schema version enforcement.

- **Coursemos HTML Scraper (`scraper/board_parser.py`):**
  - Implemented `extract_board_modules` discovering `ubboard` and `forum` activities from course homepages while stripping `.accesshide` spans.
  - Implemented `classify_board_type` keyword categorization (`NOTICE`, `QNA`, `CUSTOM`, `OTHER`).
  - Implemented `parse_board_list_page` handling 5-column notices, 6-column Q&A tables with status badges, comment counts, secret posts, and student question identification (`is_my_question`).
  - Implemented `parse_board_article_page` extracting post subject, author, date, hit count, attachments list, markdown content, and threaded replies.

- **HTML-to-Markdown Converter (`board/text_converter.py`):**
  - Implemented `html_to_markdown` using BeautifulSoup AST traversal to convert HTML tags into clean Markdown formatting.
  - Ensured Windows CP949 console safety by replacing `\xa0` (non-breaking space) with standard spaces (preventing `UnicodeEncodeError`).
  - Implemented `extract_summary_preview` extracting 1-2 line summaries capped at 140 characters.

- **Atomic Read State Manager (`board/read_state.py`):**
  - Implemented `BoardReadStateManager` storing read post IDs per course in `.cache/board_read_state.json`.
  - Implemented atomic file writing using `.tmp` file creation and rename (`replace`) to prevent corruption.
  - Enforced LRU/FIFO capping of at most 200 entries per course.
  - Added automated corrupted-file recovery.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- `uv run pytest tests/test_board_parser.py tests/test_board_text_converter.py tests/test_board_read_state.py` (18 passed in 0.85s).
- All acceptance criteria across Tasks 15-01-01, 15-01-02, and 15-01-03 satisfied.

## Self-Check: PASSED
