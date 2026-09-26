---
phase: 15-course-announcements-q-a-board-briefing
plan: "02"
subsystem: board
tags:
  - runner
  - reporter
  - cli
  - rich
  - click
  - json-contract
requires:
  - "15-01"
provides:
  - board-runner-pipeline
  - single-article-viewer
  - rich-terminal-reporter
  - board-cli-commands
affects: []
tech-stack.added: []
patterns:
  - Course error isolation
  - List-first network optimization
  - Stream separation (stderr vs stdout)
  - Unified CLI command options decorator
key-files.created:
  - src/coursepilot/board/runner.py
  - src/coursepilot/board/reporter.py
  - tests/test_board_runner.py
  - tests/test_cli_board.py
key-files.modified:
  - src/coursepilot/reporter.py
  - src/coursepilot/cli.py
key-decisions:
  - "D-15-01: Expose unified coursepilot board with notices and qna convenience commands."
  - "D-15-02: Compact 1-line muted text for inactive courses without notices or Q&A."
  - "D-15-04: Strict schema_version: 1 JSON contract formatting for machine-readable output."
  - "D-15-06: Provide --view <id> for single post inspection with markdown rendering."
  - "D-15-08: Reuse Phase 13 downloader engine for --download-attachments."
  - "D-15-10: Color badge indicators for [답변완료] (green) and [답변대기] (yellow)."
  - "D-15-13: Do not connect to Notion Scheduler DB, keeping board briefing CLI-focused."
  - "D-15-14: Distinguish unread posts with bold red [NEW] badges and --unread-only filter."
  - "D-15-15: Automatically mark posts as read when viewed via --view or --detail."
  - "D-15-16: List-first network optimization fetching view.php by default."
requirements:
  - BRD-01
  - BRD-02
coverage:
  - deliverable: "Multi-course board collection pipeline and error isolation"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_board_runner.py#test_run_board_pipeline_course_error_isolation"
      status: pass
  - deliverable: "Single article viewer with auto read tracking and attachments"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_board_runner.py#test_view_board_article_auto_marks_read"
      status: pass
  - deliverable: "Rich terminal reporting with status badges and inactive course summaries"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_board_runner.py#test_render_board_report"
      status: pass
  - deliverable: "Click CLI commands (board, notices, qna) and schema_version 1 JSON contract"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_cli_board.py#test_cli_board_json_contract"
      status: pass
duration: "7 min"
completed: "2026-09-26T02:44:00Z"
---

# Phase 15 Plan 02: Board Runner Pipeline, Rich Console Presentation, CLI Commands & JSON Contract Summary

Multi-course board collection pipeline, single article viewer, Rich terminal tables and status badges, Click CLI commands (`board`, `notices`, `qna`), and schema_version: 1 JSON contract.

## Accomplishments

- **Multi-Course Collection Pipeline & Viewer (`board/runner.py`):**
  - Implemented `run_board_pipeline` supporting multi-course traversal with per-course `try-except` error isolation.
  - Implemented network traffic optimization (D-15-16): defaults to lightweight `view.php` list fetching, requesting `article.php` only on `--detail` or `--view`.
  - Implemented all post filters: `--limit`, `--all`, `--unread-only`, `--unanswered`, `--my`, and `--board-name`.
  - Implemented `view_board_article` fetching full markdown bodies, attachments, official teacher/TA replies, and auto-marking viewed posts as read in `BoardReadStateManager`.
  - Integrated attachment downloads with Phase 13's downloader engine when `--download-attachments` is set (D-15-08).

- **Rich Terminal Presentation (`board/reporter.py`, `reporter.py`):**
  - Implemented `render_board_report` rendering summary header panels, 1-line muted summaries for inactive courses (`[dim]• 과목명: 최근 공지 및 질문 없음[/dim]`), and structured tables for active courses.
  - Implemented visual status badges: `[NEW]`, `[답변완료]`, `[답변대기]`, and `[내 질문]`.
  - Implemented `render_article_viewer` rendering metadata panels, attachments lists with file sizes/saved paths, body markdown, and reply sub-panels.
  - Re-exported renderer functions in `src/coursepilot/reporter.py`.

- **Click CLI Commands & JSON Contract (`cli.py`):**
  - Registered `@cli.command("board")` for unified briefing, along with convenience commands `@cli.command("notices")` and `@cli.command("qna")`.
  - Implemented strict stream separation: navigation and progress logs directed to stderr, reports and JSON directed to stdout.
  - Strictly enforced JSON contract (`schema_version: 1`) on `--json` flag.
  - Mapped exit codes: 0 for success, 1 for partial collection warnings, 2 for fatal exceptions.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- `uv run pytest tests/test_board_*.py tests/test_cli_board.py` (30 passed in 1.69s).
- All acceptance criteria across Tasks 15-02-01, 15-02-02, and 15-02-03 satisfied.

## Self-Check: PASSED
