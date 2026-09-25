# Phase 15: Course Announcements & Q&A Board Briefing - Pattern Map

**Mapped:** 2026-09-26  
**Phase Directory:** `file:///D:/dev/kau-lxp-assistant/.planning/phases/15-course-announcements-q-a-board-briefing`  
**Files Analyzed:** 14  
**Analogs Found:** 14 (Established codebase patterns directly reused)

---

## File Classification

| File Path | Action | Role | Data Flow |
|---|---|---|---|
| [`src/kau_assistant/board/__init__.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/board/__init__.py) | Create | Package Init & Exports | Internal modules -> `__all__` export table -> External callers & CLI |
| [`src/kau_assistant/board/models.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/board/models.py) | Create | Domain Models & JSON Contract | Raw parser/state dicts -> Pydantic Schema (`schema_version: 1`) -> Validated typed objects / JSON |
| [`src/kau_assistant/scraper/board_parser.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/scraper/board_parser.py) | Create | Service / Pure HTML Scraper | Raw LMS HTML (`course/view.php`, `ubboard/view.php`, `article.php`) -> BeautifulSoup AST -> Typed DTOs |
| [`src/kau_assistant/board/text_converter.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/board/text_converter.py) | Create | HTML-to-Markdown Utility | Raw Moodle Atto HTML -> DOM cleaning & AST tag transformation -> Clean Markdown & 2-line previews |
| [`src/kau_assistant/board/read_state.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/board/read_state.py) | Create | Model / Service (Atomic State) | `.cache/board_read_state.json` <-> Atomic `.tmp` rename + per-course LRU 200 capping |
| [`src/kau_assistant/board/runner.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/board/runner.py) | Create | Controller / Orchestrator | CLI options -> Course discovery -> Board parsing -> State check -> Report builder / Article viewer |
| [`src/kau_assistant/board/reporter.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/board/reporter.py) | Create | View / Presentation | `BoardReport` / `BoardPostItem` -> Rich Console tables, color badges, Markdown panels |
| [`src/kau_assistant/reporter.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/reporter.py) | Modify | Reporter Re-export & Integration | Re-export board reporter functions for unified reporting access |
| [`src/kau_assistant/cli.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/cli.py) | Modify | Route / CLI Commands | `@cli.command("board")`, `@cli.command("notices")`, `@cli.command("qna")` -> Runner -> Rich/JSON output |
| [`tests/test_board_parser.py`](file:///D:/dev/kau-lxp-assistant/tests/test_board_parser.py) | Create | Unit Test (Scraper) | HTML fixtures -> `board_parser` functions -> Assert board classification, table columns, replies, secrets |
| [`tests/test_board_text_converter.py`](file:///D:/dev/kau-lxp-assistant/tests/test_board_text_converter.py) | Create | Unit Test (Text Converter) | Sample Moodle HTML -> `html_to_markdown` / `extract_summary_preview` -> Assert markdown formatting & CP949 safety |
| [`tests/test_board_read_state.py`](file:///D:/dev/kau-lxp-assistant/tests/test_board_read_state.py) | Create | Unit Test (Read State) | `tmp_path` -> `BoardReadStateManager` -> Assert persistence, atomic replacement, LRU cap, corrupted file recovery |
| [`tests/test_board_runner.py`](file:///D:/dev/kau-lxp-assistant/tests/test_board_runner.py) | Create | Integration Test (Runner) | Mocked session/HTTP clients -> `run_board_pipeline` -> Assert course error isolation, filters, auto-mark-read |
| [`tests/test_cli_board.py`](file:///D:/dev/kau-lxp-assistant/tests/test_cli_board.py) | Create | CLI Test (Click Runner) | CLI args -> Click `CliRunner` -> Assert exit codes, Rich table stdout, JSON contract `schema_version: 1` |

---

## Pattern Assignments

### 1. `src/kau_assistant/board/models.py`
- **Role:** Domain models and versioned JSON contract schemas (`schema_version: 1`).
- **Closest Analog:** [`src/kau_assistant/materials/models.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/materials/models.py#L7-L63) & [`src/kau_assistant/report_models.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/report_models.py#L6-L97)
- **Rationale:** `report_models.py` defines the canonical pattern for versioned envelopes (`SCHEMA_VERSION = 1`, `model_config = ConfigDict(extra="forbid")`, strong literal tags), while `materials/models.py` demonstrates per-item results and aggregate container structures.
- **Concrete Code Excerpt:**
  ```python
  # src/kau_assistant/report_models.py (lines 6-8, 85-97)
  SCHEMA_VERSION = 1

  class CheckReport(BaseModel):
      """Versioned `check` command JSON envelope, never a raw SyncTask dump (D-13)."""

      model_config = ConfigDict(extra="forbid")

      schema_version: Literal[1] = SCHEMA_VERSION
      command: Literal["check"] = "check"
      generated_at: datetime
      summary: ReportSummary
      items: BriefingSections
      errors: list[ErrorItem]
      notices: list[ReportNotice] = Field(default_factory=list)
  ```
- **Application:**
  - Define `BoardType(str, Enum)`: `NOTICE = "notice"`, `QNA = "qna"`, `OTHER = "other"`, `CUSTOM = "custom"`.
  - Define `BoardModuleInfo(BaseModel)`: `module_id: str`, `title: str`, `url: str`, `board_type: BoardType`.
  - Define `BoardAttachmentItem(BaseModel)`: `filename: str`, `download_url: str`, `filesize: int = 0`, `saved_path: str | None = None`.
  - Define `BoardReplyItem(BaseModel)`: `author: str`, `created_at: str`, `content: str`.
  - Define `BoardPostItem(BaseModel)`:
    - Identifiers: `post_id: str`, `bwid: str | None = None`, `board_id: str`, `board_type: BoardType`
    - Core: `title: str`, `author: str`, `created_at: str`, `hit_count: int = 0`, `url: str`
    - Status flags: `is_read: bool = False`, `is_my_question: bool = False`, `is_answered: bool | None = None`, `is_secret: bool = False`
    - Content: `summary_preview: str = ""`, `content: str | None = None`
    - Nested: `attachments: list[BoardAttachmentItem] = Field(default_factory=list)`, `replies: list[BoardReplyItem] = Field(default_factory=list)`
  - Define `CourseBoardGroup(BaseModel)`: `course_id: str`, `course_name: str`, `course_abbr: str`, `notices: list[BoardPostItem]`, `qna: list[BoardPostItem]`.
  - Define `BoardSummary(BaseModel)`: `total_courses: int`, `total_notices: int`, `unread_notices: int`, `total_questions: int`, `unanswered_questions: int`, `my_questions: int`.
  - Define `BoardReport(BaseModel)`: `schema_version: Literal[1] = 1`, `command: Literal["board", "notices", "qna"] = "board"`, `generated_at: datetime`, `summary: BoardSummary`, `courses: list[CourseBoardGroup]`, `errors: list[dict] = Field(default_factory=list)`.

---

### 2. `src/kau_assistant/scraper/board_parser.py`
- **Role:** Pure HTML parsing and AST inspection for Coursemos `ubboard` and `forum` modules.
- **Closest Analog:** [`src/kau_assistant/scraper/material_parser.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/scraper/material_parser.py#L13-L131)
- **Rationale:** `material_parser.py` demonstrates BeautifulSoup AST traversal, accesshide decomposition with `copy.deepcopy`, regex extraction of module IDs, and `urljoin` resolution.
- **Concrete Code Excerpt:**
  ```python
  # src/kau_assistant/scraper/material_parser.py (lines 76-113)
  activities = sec.find_all(
      lambda tag: tag.name == "li"
      and any(cls == "activity" for cls in tag.get("class", []))
      and any(cls in ("ubfile", "modtype_ubfile", "resource", "modtype_resource") for cls in tag.get("class", []))
  )

  for act in activities:
      a_el = act.find("a", href=re.compile(r"/mod/(?:ubfile|resource)/view\.php", re.I))
      ...
      # Clean title by removing accesshide spans
      name_el = a_el.find("span", class_="instancename") or a_el
      name_copy = copy.deepcopy(name_el)
      for ah in name_copy.find_all(class_="accesshide"):
          ah.decompose()
      raw_title = name_copy.get_text(strip=True)
      title = re.sub(r"\s+", " ", raw_title).strip()
  ```
- **Application:**
  - `extract_board_modules(html: str, base_url: str) -> list[BoardModuleInfo]`:
    - Finds `<li class="activity ... ubboard modtype_ubboard">` or `forum`.
    - Decomposes `.accesshide` spans inside `.instancename`.
    - Classifies board type using keywords: `"공지"|"notice"` -> `NOTICE`, `"q&a"|"질문"|"문의"|"질의"` -> `QNA`, else `OTHER`.
  - `parse_board_list_page(html: str, base_url: str, board_id: str, board_type: BoardType, current_user_name: str = "") -> list[BoardPostItem]`:
    - Finds `table.ubboard_table`, `table-hover`, or `generaltable`.
    - Dynamically maps `th`/`td` column names (`번호`, `상태`, `제목`, `작성자`, `작성일`, `조회`) to indices (Pitfall 3: 5 vs 6 columns).
    - Extracts `bwid` and post link via regex `re.search(r"bwid=(\d+)", href)`.
    - Decomposes comment count span `<span class="comment">[N]</span>` and badges (`.newicon`, `.secret`).
    - Detects answer status (`상태` column: "완료" vs "대기", or `[RE]` in title, or `comment_count > 0`).
    - Identifies `is_my_question` if `current_user_name` matches author.
    - Handles secret posts where anchor tag is absent (Pitfall 5).
    - Pulls full timestamps from `<span title="YYYY-MM-DD HH:MM:SS">`.
  - `parse_board_article_page(html: str, base_url: str) -> BoardArticleDetail`:
    - Container: `div.ubboard_view > div.well`.
    - Extracts title (`div.subject`), author (`div.writer`), date (`div.date`), hits (`div.hit`).
    - Extracts attachments: `ul.files li a` -> `BoardAttachmentItem(filename, download_url)`.
    - Extracts replies/comments: `div.comment_list`, `ul.comments` -> `BoardReplyItem(author, created_at, content)`.

---

### 3. `src/kau_assistant/board/text_converter.py`
- **Role:** Pure HTML-to-Markdown transformer and table summary preview generator.
- **Closest Analog:** [`src/kau_assistant/materials/filename_utils.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/materials/filename_utils.py#L9-L44)
- **Rationale:** Self-contained string sanitization utility with zero external CLI/network dependencies, ensuring safe terminal display and CP949 encoding compatibility.
- **Concrete Code Excerpt:**
  ```python
  # src/kau_assistant/materials/filename_utils.py (lines 20-30)
  def sanitize_filename(name: str, max_length: int = 200) -> str:
      if not name or not name.strip():
          return "unnamed_file"
      clean = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", name)
      clean = re.sub(r"\s+", " ", clean).strip()
      return clean[:max_length]
  ```
- **Application:**
  - `html_to_markdown(html_content: str) -> str`:
    - Decomposes `<script>`, `<style>`, `<meta>`, `<link>`, `.accesshide`.
    - Replaces `<br>` and `<hr>` with `\n`.
    - Converts `<a>` tags to `[text](href)` (ignoring javascript pseudo-links).
    - Converts `<strong>`/`<b>` to `**text**`, `<em>`/`<i>` to `*text*`.
    - Converts `<li>` to `\n- text`.
    - Adds newline padding (`\n\n`) around block elements (`<p>`, `<div>`, `<blockquote>`, headings).
    - Replaces non-breaking space `\xa0` with standard space `" "` to prevent Windows console CP949 crash (Pitfall 1).
    - Coalesces consecutive newlines with `re.sub(r"\n\s*\n\s*\n+", "\n\n", text)`.
  - `extract_summary_preview(text: str, max_lines: int = 2, max_chars: int = 140) -> str`:
    - Splits text into non-empty lines, selects first `max_lines`, joins with spaces, truncates at `max_chars - 3` + `...`.

---

### 4. `src/kau_assistant/board/read_state.py`
- **Role:** Local read state manager tracking viewed post IDs per course with atomic writes and LRU capping.
- **Closest Analog:** [`src/kau_assistant/player/state.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/state.py#L19-L67)
- **Rationale:** `WatchStateManager` demonstrates atomic file writes via `.tmp` and `replace`, safe corrupted JSON handling, and default cache directory path resolution.
- **Concrete Code Excerpt:**
  ```python
  # src/kau_assistant/player/state.py (lines 19-46)
  class WatchStateManager:
      """Manages atomic state tracking, stop signals, and completed watch history."""

      def __init__(self, cache_dir: Path | None = None, settings: Settings | None = None) -> None:
          self.settings = settings or get_settings()
          self.cache_dir = Path(cache_dir) if cache_dir else self.settings.session_cache_path.parent

      def get_state_file_path(self) -> Path:
          return self.cache_dir / "watch_state.json"

      def write_state(self, state: WatchState) -> None:
          path = self.get_state_file_path()
          path.parent.mkdir(parents=True, exist_ok=True)
          temp_path = path.with_suffix(".tmp")
          try:
              temp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
              temp_path.replace(path)
          except Exception as e:
              logger.error(f"Failed to write watch state: {e}")
              if temp_path.exists():
                  temp_path.unlink(missing_ok=True)
  ```
- **Application:**
  - Class `BoardReadStateManager`:
    - Defaults state file path to `.cache/board_read_state.json`.
    - `_load() -> BoardReadStateFile`: Reads and parses JSON; on exception, logs warning and returns fresh `BoardReadStateFile()`.
    - `save() -> None`: Atomically writes JSON using `temp_path = path.with_suffix(".tmp")` and `temp_path.replace(path)` with unlink on failure.
    - `is_read(course_id: str, post_id: str) -> bool`: Checks membership in `courses[course_id].read_post_ids`.
    - `mark_as_read(course_id: str, post_ids: list[str]) -> None`: Adds IDs, updates `last_read_at = datetime.now()`, caps list to `max_entries` (default 200) keeping the most recent entries, and triggers `save()`.

---

### 5. `src/kau_assistant/board/runner.py`
- **Role:** Execution orchestrator for multi-course collection, filtering, attachment downloading, and single article viewer.
- **Closest Analog:** [`src/kau_assistant/materials/runner.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/materials/runner.py#L171-L268) & [`src/kau_assistant/player/runner.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/runner.py#L32-L75)
- **Rationale:** `materials/runner.py` orchestrates browser session initialization via `SessionManager`, course extraction, course filtering via `find_target_course`, `httpx.Client` cookie authentication, progress reporting, and course-level error isolation.
- **Concrete Code Excerpt:**
  ```python
  # src/kau_assistant/materials/runner.py (lines 202-243)
  try:
      with SessionManager(settings=cfg, headful=headful) as sm:
          page = sm.get_authenticated_page()
          courses = extract_courses(page, cfg.lms_url)

          if course_query:
              mappings = load_course_mappings(cfg.course_mappings_path)
              target_course = find_target_course(courses, course_query, mappings)
              if not target_course:
                  raise ValueError(f"과목 검색어와 일치하는 강좌를 찾을 수 없습니다: '{course_query}'")
              target_courses = [target_course]
          else:
              target_courses = courses

          navigator = CourseNavigator()
          for c in target_courses:
              if progress_callback:
                  progress_callback(f"과목 진입 중: {c.clean_name}")
              navigator.navigate_to_course(page, c.url)
              html = page.content()
              ...
  finally:
      if client is not None:
          try:
              client.close()
          except Exception:
              pass
  ```
- **Application:**
  - `run_board_pipeline(...) -> BoardReport`:
    - Initializes `SessionManager` and extracts courses. Resolves course target via `find_target_course`.
    - Retrieves current user LMS name from header/profile (for `[내 질문]` tagging).
    - High-speed HTTP: Creates authenticated `httpx.Client` using `get_authenticated_httpx_client(cfg)`.
    - Traffic optimization (D-15-16): Only fetches `view.php` list tables by default.
    - Course-level exception isolation: Wraps each course iteration in `try...except` and appends to `report.errors`.
    - Applies filters:
      - `--limit N` (default 3) vs `--all`
      - `--unread-only` (filters out items where `read_state.is_read(course_id, post_id)` is True)
      - `--unanswered` (retains only Q&A items where `is_answered is False`)
      - `--my` (retains only Q&A items where `is_my_question is True`)
    - If `--detail`: fetches `article.php` for the filtered posts and populates full contents.
    - If `--mark-read`: marks all fetched posts as read.
    - Assembles and returns `BoardReport`.
  - `view_board_article(...) -> BoardPostItem`:
    - Directly fetches the specific `article.php?id={board_id}&bwid={view_id}` page.
    - Converts body to Markdown, parses attachments and replies.
    - Automatically marks article as read in `BoardReadStateManager` (D-15-15).
    - If `--download-attachments`: reuses `download_material_file` to save files into `downloads/<과목명>/notices/`.

---

### 6. `src/kau_assistant/board/reporter.py` (and re-exported via `src/kau_assistant/reporter.py`)
- **Role:** Rich Console formatting for board tables, status badges, and single article viewer.
- **Closest Analog:** [`src/kau_assistant/materials/reporter.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/materials/reporter.py#L22-L85) & [`src/kau_assistant/reporter.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/reporter.py#L350-L420)
- **Rationale:** Established Rich formatting conventions: color palette, table column layout, Panel wrapping, and separation of stdout (final output) from stderr (progress).
- **Concrete Code Excerpt:**
  ```python
  # src/kau_assistant/materials/reporter.py (lines 29-35, 71-79)
  table = Table(title="학습 자료 처리 현황", show_lines=True)
  table.add_column("과목", style="bold cyan")
  table.add_column("주차", style="magenta")
  table.add_column("자료명", style="white")
  table.add_column("상태", justify="center")
  table.add_column("크기 / 저장 경로", style="dim")
  ...
  console.print(table)
  console.print(Panel(summary_msg, title="요약", expand=False))
  ```
- **Application:**
  - `render_board_report(report: BoardReport, console: Console, detail: bool = False) -> None`:
    - Summary Header Panel: `총 과목: N | 공지사항: X (신규 Y) | Q&A: A (답변대기 B, 내 질문 C)`.
    - For courses with 0 notices and 0 Q&A: print compact 1-line muted text `[dim]• 과목명: 최근 공지 및 질문 없음[/dim]` (D-15-02).
    - For active courses: render Rich `Table(title=f"{course.course_name}", show_lines=True)`:
      - Columns: `구분` (공지 / Q&A), `번호`, `제목`, `작성자`, `작성일`, `상태`
      - Badges: `[bold red][NEW][/bold red]` for unread, `[bold green][답변완료][/bold green]`, `[bold yellow][답변대기][/bold yellow]`, `[bold cyan][내 질문][/bold cyan]`.
      - If `detail=True`: includes summary preview block below title.
    - If `report.errors`: render error table via `_render_errors(report.errors, console)`.
  - `render_article_viewer(post: BoardPostItem, console: Console) -> None`:
    - Renders detailed terminal viewer with Title, Author, Date, Views, LMS link.
    - Attachments panel listing filename and download path (if downloaded).
    - Content rendered using Rich `Markdown(post.content)`.
    - Replies/Answers rendered in separate highlighted sub-panels.

---

### 7. `src/kau_assistant/cli.py`
- **Role:** Click CLI command registration, parameter validation, stream configuration, and exit code handling.
- **Closest Analog:** [`src/kau_assistant/cli.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/cli.py#L505-L600) & [`src/kau_assistant/cli.py#L720-L741`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/cli.py#L720-L741)
- **Rationale:** Existing commands (`check`, `sync`, `materials`, `download-vod`) follow uniform Click decorator patterns, stream setup (`_configure_streams`), `Console(stderr=True)` for progress, and exit code mapping.
- **Concrete Code Excerpt:**
  ```python
  # src/kau_assistant/cli.py (lines 505-599)
  @cli.command("materials")
  @click.option("--course", "course_query", type=str, default=None, help="과목 이름, 약칭, 또는 과목 ID (생략 시 전체 과목)")
  @click.option("--json", "as_json", is_flag=True, help="결과를 JSON 형식으로 출력합니다.")
  @click.pass_context
  def materials_command(ctx: click.Context, course_query: str | None, as_json: bool, ...) -> None:
      err = Console(stderr=True)
      out = Console()
      def _on_progress(msg: str) -> None:
          err.print(msg, markup=False, highlight=False)
      try:
          result = run_materials_pipeline(...)
      except Exception as e:
          err.print(f"[오류] 학습자료 처리 실패: {e}", markup=False, highlight=False)
          ctx.exit(2)
      if as_json:
          click.echo(result.model_dump_json(indent=2))
      else:
          render_materials_report(result, out)
  ```
- **Application:**
  - Register `@cli.command("board")` (unified briefing):
    - Options: `--course`, `--limit` (default 3), `--all`, `--detail`, `--view`, `--unread-only`, `--unanswered`, `--my`, `--board-name`, `--mark-read`, `--download-attachments`, `--json`, `--relogin`, `--headed`.
  - Register `@cli.command("notices")` (convenience alias):
    - Subcommand pre-filtering to `board_type=BoardType.NOTICE`.
  - Register `@cli.command("qna")` (convenience alias):
    - Subcommand pre-filtering to `board_type=BoardType.QNA`.
  - Ensure `_configure_streams()` runs to enforce UTF-8 across parent pipes.

---

### 8. `tests/test_board_parser.py`
- **Role:** Unit tests for Coursemos HTML parsing (course home board discovery, table parsing, article detail extraction).
- **Closest Analog:** [`tests/test_material_parser.py`](file:///D:/dev/kau-lxp-assistant/tests/test_material_parser.py#L11-L64)
- **Rationale:** Uses realistic HTML fixtures (`lxp_board_course.html`, `lxp_board_list.html`, `lxp_board_article.html`) to verify AST parsing, `.accesshide` removal, column index mapping, and badge detection.
- **Concrete Code Excerpt:**
  ```python
  # tests/test_material_parser.py (lines 11-35)
  def test_parse_materials_from_course_sections():
      fixture_path = Path(__file__).parent / "fixtures" / "lxp_course_materials.html"
      html = fixture_path.read_text(encoding="utf-8")
      course = CourseItem(...)
      materials = parse_materials_from_course_sections(html, course)
      assert len(materials) == 5
      assert "학습자료" not in materials[0].title
  ```
- **Application:**
  - `test_extract_board_modules`: Verifies detection of `mod_ubboard` activities, stripping of `<span class="accesshide"> 게시판</span>`, and classification into `NOTICE` vs `QNA`.
  - `test_parse_notice_table_5_columns`: Verifies parsing of standard notice tables, `bwid` extraction, author, and timestamp from `span[title]`.
  - `test_parse_qna_table_6_columns`: Verifies status detection (`[답변완료]` vs `[답변대기]`), comment count decomposition, and `[내 질문]` tagging.
  - `test_parse_secret_post_without_link`: Verifies graceful handling of confidential inquiries where `a` tag is missing.
  - `test_parse_article_detail_page`: Verifies parsing of title, author, date, hit count, attachment download links, and reply threads.

---

### 9. `tests/test_board_text_converter.py`
- **Role:** Unit tests for HTML-to-Markdown conversion and summary preview generation.
- **Closest Analog:** [`tests/test_filename_utils.py`](file:///D:/dev/kau-lxp-assistant/tests/test_filename_utils.py#L1-L30)
- **Rationale:** Pure input-output transformation unit tests verifying text formatting, tag sanitization, and Unicode handling.
- **Application:**
  - `test_html_to_markdown_tags`: Verifies conversion of `<br>`, `<p>`, `<a>`, `<strong>`, `<em>`, `<ul><li>`.
  - `test_html_to_markdown_removes_unwanted`: Verifies decomposition of `<script>`, `<style>`, and `.accesshide`.
  - `test_non_breaking_space_replacement`: Verifies `\xa0` is replaced with standard space `" "` to prevent Windows CP949 errors.
  - `test_extract_summary_preview`: Verifies 2-line capping and 140 character limit with ellipsis.

---

### 10. `tests/test_board_read_state.py`
- **Role:** Unit tests for atomic state persistence and LRU capping.
- **Closest Analog:** [`tests/test_watch_state.py`](file:///D:/dev/kau-lxp-assistant/tests/test_watch_state.py#L13-L57)
- **Rationale:** `test_watch_state.py` validates `tmp_path` isolation, initial empty state, write/read lifecycle, and corrupted JSON file recovery.
- **Concrete Code Excerpt:**
  ```python
  # tests/test_watch_state.py (lines 13-25, 50-56)
  def test_watch_state_lifecycle(tmp_path: Path):
      manager = WatchStateManager(cache_dir=tmp_path)
      assert manager.read_state() is None
      ...
  def test_watch_state_corrupted_file(tmp_path: Path):
      manager = WatchStateManager(cache_dir=tmp_path)
      state_file = manager.get_state_file_path()
      state_file.write_text("invalid json content", encoding="utf-8")
      assert manager.read_state() is None
  ```
- **Application:**
  - `test_read_state_lifecycle`: Verifies `is_read` returns False initially, `mark_as_read` updates state, and state persists across manager re-instantiations.
  - `test_read_state_lru_cap`: Marks 250 post IDs and asserts only the most recent 200 IDs are retained.
  - `test_read_state_corrupted_file`: Writes invalid JSON string to `board_read_state.json` and verifies manager handles it safely by starting with an empty state.

---

### 11. `tests/test_board_runner.py`
- **Role:** Integration tests for the board runner orchestrator with mocked session/HTTP clients.
- **Closest Analog:** [`tests/test_materials_runner.py`](file:///D:/dev/kau-lxp-assistant/tests/test_materials_runner.py#L61-L160)
- **Rationale:** `test_materials_runner.py` demonstrates mocking `SessionManager`, `CourseNavigator`, `extract_courses`, and validating option filtering and course-level error isolation.
- **Application:**
  - `test_run_board_pipeline_multi_course`: Verifies discovery and parsing across multiple courses.
  - `test_run_board_pipeline_course_error_isolation`: Verifies that if one course throws an HTTP/DOM error, other courses are successfully parsed and the error is appended to `report.errors`.
  - `test_filters_limit_unread_unanswered_my`: Verifies `--limit`, `--unread-only`, `--unanswered`, and `--my` filtering logic.
  - `test_view_board_article_auto_mark_read`: Verifies fetching article detail automatically marks the post as read in `BoardReadStateManager`.

---

### 12. `tests/test_cli_board.py`
- **Role:** Click CLI command testing with `CliRunner`.
- **Closest Analog:** [`tests/test_cli_materials.py`](file:///D:/dev/kau-lxp-assistant/tests/test_cli_materials.py#L17-L75)
- **Rationale:** Demonstrates CLI option parsing validation, mock return verification, `--json` schema conformance testing (`schema_version: 1`), and exit code checking.
- **Concrete Code Excerpt:**
  ```python
  # tests/test_cli_materials.py (lines 17-27, 67-74)
  def test_materials_and_files_help():
      runner = CliRunner()
      res = runner.invoke(cli, ["materials", "--help"])
      assert res.exit_code == 0
      assert "--course" in res.output

  @patch("kau_assistant.materials.runner.run_materials_pipeline")
  def test_materials_dry_run_json(mock_run_pipeline):
      mock_run_pipeline.return_value = MaterialsRunResult(...)
      runner = CliRunner()
      result = runner.invoke(cli, ["materials", "--dry-run", "--json"])
      assert result.exit_code == 0
      data = json.loads(result.output)
      assert data["dry_run"] is True
  ```
- **Application:**
  - `test_cli_board_help`: Verifies `--help` on `board`, `notices`, and `qna`.
  - `test_cli_board_json_contract`: Verifies `kau-assistant board --json` output conforms to JSON contract v1 (`schema_version: 1`).
  - `test_cli_board_view_command`: Verifies `kau-assistant board --view 101` invokes viewer and outputs article detail.
  - `test_cli_board_exit_codes`: Verifies exit code 0 on success, exit code 1 on collection warnings/errors, exit code 2 on fatal crash.

---

## Shared Architectural Patterns

### 1. Standard Imports & Type Annotations
```python
from __future__ import annotations

import copy
import logging
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import click
import httpx
from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
```

### 2. Error Isolation & Course Isolation
- In `board/runner.py`, every course is processed within an isolated `try...except Exception as e:` block.
- A failure in one course (e.g. course board renamed, network timeout) produces an `ErrorItem(scope="course", ...)` in `report.errors` while remaining courses proceed uninterrupted.

### 3. Stream & Encoding Hygiene
- `Console(stderr=True)` is used for progress messages and navigational logs (`[자료구조] 게시판 확인 중...`).
- `Console()` is used strictly for final tabular reports and markdown viewing.
- When `--json` is supplied, `click.echo(report.model_dump_json(indent=2))` is printed to stdout without extraneous text.
- `_configure_streams()` reconfigures stdout/stderr to UTF-8 to prevent CP949 encoding errors on Windows.
- `text_converter.py` replaces `\xa0` with regular spaces before Rich rendering.

### 4. Atomic State Persistence (`board_read_state.json`)
- Writes to `board_read_state.json.tmp` first.
- Atomically replaces target file using `temp_path.replace(path)`.
- If an exception occurs, removes temp file with `unlink(missing_ok=True)`.
- Caps post ID history to 200 entries per course via FIFO/LRU slicing (`[-200:]`).

---

## Conclusion

All 14 target files have direct, verified architectural analogs in the repository. Downstream planner (`15-01-PLAN.md`) can directly reference the concrete code excerpts, line numbers, and implementation patterns established in this map.
