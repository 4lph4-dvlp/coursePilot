# Phase 14: Pure-Python VOD Stream Downloader Integration - Pattern Map

**Mapped:** 2026-09-25
**Files analyzed:** 17
**Analogs found:** 15 (2 novel domains with established architectural analogs)

---

## File Classification

| File Path | Action | Role | Data Flow |
|---|---|---|---|
| [`pyproject.toml`](file:///D:/dev/kau-lxp-assistant/pyproject.toml) | Modify | Dependency Manifest | Specification -> Dependency Resolver -> Virtualenv |
| [`src/kau_assistant/stream/__init__.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/stream/__init__.py) | Create | Package Init & Public API | Internal symbols -> `__all__` export table -> External callers |
| [`src/kau_assistant/stream/models.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/stream/models.py) | Create | Domain Data Models | Raw parser/download state -> Pydantic Schema -> Validated typed objects / JSON |
| [`src/kau_assistant/stream/parser.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/stream/parser.py) | Create | M3U8 Playlist Parser | Raw M3U8 text + URL -> `m3u8` AST parsing -> `StreamInfo` / `StreamSegment` |
| [`src/kau_assistant/stream/crypto.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/stream/crypto.py) | Create | RFC 8216 AES-128 Decryptor | Encrypted TS bytes + Key + IV -> AES-128-CBC decipher + PKCS7 unpad -> Plaintext TS |
| [`src/kau_assistant/stream/downloader.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/stream/downloader.py) | Create | Segment Downloader & TS Merger | Media playlist segments -> ThreadPool HTTP GET -> Decrypt -> Temp TS -> Atomic `.mp4` |
| [`src/kau_assistant/stream/sniffer.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/stream/sniffer.py) | Create | Playwright Stream Sniffer | Playwright `page.on("response")` + DOM probe -> Detected stream URL -> Thread callback |
| [`src/kau_assistant/stream/runner.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/stream/runner.py) | Create | Standalone Downloader Orchestrator | CLI options -> Course/VOD discovery -> Sniff stream -> Download -> `VodDownloadRunResult` |
| [`src/kau_assistant/player/vod_player.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/vod_player.py) | Modify | Playwright Player Automation | Page navigation -> Heartbeat loop -> Sniffer hook trigger -> Attendance completion |
| [`src/kau_assistant/player/runner.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/runner.py) | Modify | Watch Pipeline Orchestrator | `watch --download` -> Sniff stream -> Background download thread -> Isolated completion |
| [`src/kau_assistant/cli.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/cli.py) | Modify | CLI Entry Points & Commands | User CLI args -> Click validation -> Orchestrator dispatch -> Rich / JSON render |
| [`tests/test_stream_parser.py`](file:///D:/dev/kau-lxp-assistant/tests/test_stream_parser.py) | Create | Unit Test (Parser) | Mock M3U8 manifest strings -> Parser functions -> Assert variants/segments/keys |
| [`tests/test_stream_crypto.py`](file:///D:/dev/kau-lxp-assistant/tests/test_stream_crypto.py) | Create | Unit Test (Crypto) | Synthetic ciphertext + AES keys/IVs -> Decryptor -> Assert plaintext / padding recovery |
| [`tests/test_stream_downloader.py`](file:///D:/dev/kau-lxp-assistant/tests/test_stream_downloader.py) | Create | Unit Test (Downloader) | Mock `httpx.Client` + tmp_path -> SegmentDownloader -> Assert atomic file / skip / retries |
| [`tests/test_stream_sniffer.py`](file:///D:/dev/kau-lxp-assistant/tests/test_stream_sniffer.py) | Create | Unit Test (Sniffer) | Mock Playwright Page/Response -> Sniffer -> Assert stream URL detection & DOM fallback |
| [`tests/test_watch_download.py`](file:///D:/dev/kau-lxp-assistant/tests/test_watch_download.py) | Create | Integration Test (Watch + Download) | Mock Page & Downloader -> `watch_course_vods` -> Assert background download + attendance isolation |
| [`tests/test_cli_download_vod.py`](file:///D:/dev/kau-lxp-assistant/tests/test_cli_download_vod.py) | Create | CLI Test (Click Runner) | CLI args -> Click CliRunner -> Assert stdout JSON / exit codes / option plumbing |

---

## Pattern Assignments

### 1. `pyproject.toml`
- **Role:** Project dependency specifications
- **Closest Analog:** [`pyproject.toml`](file:///D:/dev/kau-lxp-assistant/pyproject.toml#L7-L19)
- **Rationale:** Existing project configuration file specifying runtime dependencies.
- **Concrete Code Excerpt:**
  ```toml
  dependencies = [
      "playwright>=1.42.0",
      "pydantic>=2.6.0",
      "pydantic-settings>=2.2.0",
      "python-dotenv>=1.0.0",
      "rich>=13.7.0",
      "click>=8.1.0",
      "notion-client>=2.2.1",
      "python-dateutil>=2.9.0",
      "pytz>=2024.1",
      "beautifulsoup4>=4.12.0",
      "lxml>=5.2.0",
  ]
  ```
- **Application:** Append `"m3u8>=6.0.0"`, `"cryptography>=50.0.0"`, and `"httpx>=0.28.0"` to `project.dependencies`.

---

### 2. `src/kau_assistant/stream/__init__.py`
- **Role:** Package entrypoint and explicit export boundary
- **Closest Analog:** [`src/kau_assistant/player/__init__.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/__init__.py#L1-L21)
- **Rationale:** `player/__init__.py` cleanly defines package docstrings, selective model/runner imports, and an explicit `__all__` list.
- **Concrete Code Excerpt:**
  ```python
  """VOD playback automation package."""

  from kau_assistant.player.models import PlaybackOptions, PlaybackProgress
  from kau_assistant.player.runner import (
      WatchResult,
      find_target_course,
      resolve_candidate_vods,
      watch_course_vods,
  )
  from kau_assistant.player.vod_player import VodPlayer

  __all__ = [
      "PlaybackOptions",
      "PlaybackProgress",
      "VodPlayer",
      "WatchResult",
      "find_target_course",
      "resolve_candidate_vods",
      "watch_course_vods",
  ]
  ```
- **Application:**
  ```python
  """Pure-Python HLS/M3U8 streaming, decryption, and video download subsystem."""

  from kau_assistant.stream.downloader import SegmentDownloader
  from kau_assistant.stream.models import (
      DownloadProgress,
      StreamInfo,
      VodDownloadItemResult,
      VodDownloadRunResult,
  )
  from kau_assistant.stream.runner import run_vod_download_pipeline
  from kau_assistant.stream.sniffer import StreamSniffer

  __all__ = [
      "DownloadProgress",
      "SegmentDownloader",
      "StreamInfo",
      "StreamSniffer",
      "VodDownloadItemResult",
      "VodDownloadRunResult",
      "run_vod_download_pipeline",
  ]
  ```

---

### 3. `src/kau_assistant/stream/models.py`
- **Role:** Pydantic domain models for stream metadata, download items, progress events, and run results
- **Closest Analog:** [`src/kau_assistant/materials/models.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/materials/models.py#L7-L63) & [`src/kau_assistant/player/models.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/models.py#L19-L30)
- **Rationale:** `materials/models.py` defines enums for file statuses (`DOWNLOADED`, `SKIPPED`, `FAILED`), per-item result schemas, and aggregated run schemas with counts. `player/models.py` defines real-time progress snapshots.
- **Concrete Code Excerpt:**
  ```python
  from enum import Enum
  from pydantic import BaseModel, Field

  class MaterialStatus(str, Enum):
      DOWNLOADED = "downloaded"
      SKIPPED = "skipped"
      VIEWED_ONLY = "viewed_only"
      FAILED = "failed"

  class MaterialDownloadResult(BaseModel):
      item: MaterialItem
      status: MaterialStatus
      filename: str = ""
      saved_path: str = ""
      filesize: int = 0
      view_success: bool = False
      error_message: str | None = None

  class MaterialsRunResult(BaseModel):
      total_courses: int = 0
      total_materials: int = 0
      downloaded_count: int = 0
      skipped_count: int = 0
      failed_count: int = 0
      dry_run: bool = False
      courses: list[CourseMaterialsResult] = Field(default_factory=list)
  ```
- **Application:** Define:
  - `StreamVariant`: `bandwidth: int`, `resolution: tuple[int, int] | None`, `uri: str`
  - `StreamKeyInfo`: `method: str`, `uri: str`, `iv: bytes | None`
  - `StreamSegment`: `uri: str`, `duration: float`, `sequence_number: int`, `key_info: StreamKeyInfo | None`
  - `StreamInfo`: `master_url: str`, `media_url: str`, `is_direct_mp4: bool`, `variants: list[StreamVariant]`, `segments: list[StreamSegment]`, `total_duration: float`
  - `VodDownloadStatus(str, Enum)`: `DOWNLOADED = "downloaded"`, `SKIPPED = "skipped"`, `FAILED = "failed"`
  - `DownloadProgress`: `current_segment: int`, `total_segments: int`, `downloaded_bytes: int`, `percent: float`
  - `VodDownloadItemResult`: `course_name: str`, `week_number: int`, `clip_number: int`, `title: str`, `status: VodDownloadStatus`, `saved_path: str`, `filesize: int`, `duration: float`, `error_message: str | None`
  - `CourseVodDownloadResult`: `course_id: str`, `course_name: str`, `target_week: str`, `items: list[VodDownloadItemResult]`
  - `VodDownloadRunResult`: `total_courses: int`, `total_vods: int`, `downloaded_count: int`, `skipped_count: int`, `failed_count: int`, `dry_run: bool`, `courses: list[CourseVodDownloadResult]`

---

### 4. `src/kau_assistant/stream/parser.py`
- **Role:** Pure-Python HLS manifest parser leveraging `m3u8`
- **Closest Analog:** [`src/kau_assistant/scraper/material_parser.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/scraper/material_parser.py#L1-L15) and [`14-RESEARCH.md#L279-L321`](file:///D:/dev/kau-lxp-assistant/.planning/phases/14-pure-python-vod-stream-downloader-integration/14-RESEARCH.md#L279-L321)
- **Rationale:** Pure parsing logic extracting structured data from raw content; URL joining via `urllib.parse.urljoin`.
- **Concrete Code Excerpt:**
  ```python
  import m3u8
  from urllib.parse import urljoin

  def resolve_media_playlist_url(
      master_content: str,
      master_url: str,
      preferred_quality: str = "best",
  ) -> str:
      parsed = m3u8.loads(master_content, uri=master_url)
      if not parsed.is_variant:
          return master_url
      ...
  ```
- **Application:** Implement:
  - `parse_master_or_media_playlist(content: str, base_url: str, preferred_quality: str = "best") -> StreamInfo`
  - `select_variant_by_quality(variants: list[StreamVariant], preferred_quality: str) -> StreamVariant`
  - Supports RFC 8216 sequence numbers: fallback `media_sequence` if segments lack explicit numbers.
  - Correctly extracts `#EXT-X-KEY` attributes (`METHOD`, `URI`, `IV`).

---

### 5. `src/kau_assistant/stream/crypto.py`
- **Role:** Pure-Python RFC 8216 AES-128-CBC decryption and IV derivation
- **Closest Analog:** [`src/kau_assistant/materials/filename_utils.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/materials/filename_utils.py#L93-L126) & [`14-RESEARCH.md#L248-L275`](file:///D:/dev/kau-lxp-assistant/.planning/phases/14-pure-python-vod-stream-downloader-integration/14-RESEARCH.md#L248-L275)
- **Rationale:** Functional utility module with robust error handling and fallbacks.
- **Concrete Code Excerpt:**
  ```python
  from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
  from cryptography.hazmat.primitives import padding

  def decrypt_aes_128_segment(
      encrypted_data: bytes,
      key: bytes,
      iv: bytes,
  ) -> bytes:
      if len(key) != 16:
          raise ValueError(f"AES-128 key must be exactly 16 bytes, got {len(key)}")
      if len(iv) != 16:
          raise ValueError(f"AES-128 IV must be exactly 16 bytes, got {len(iv)}")

      cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
      decryptor = cipher.decryptor()
      decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()

      try:
          unpadder = padding.PKCS7(128).unpadder()
          return unpadder.update(decrypted_padded) + unpadder.finalize()
      except ValueError:
          return decrypted_padded
  ```
- **Application:** Implement `decrypt_aes_128_segment` and `derive_implicit_iv(sequence_number: int) -> bytes`:
  - `derive_implicit_iv(sequence_number: int) -> bytes`: `sequence_number.to_bytes(16, byteorder="big")` per RFC 8216 §5.2.
  - Robust exception handling retaining raw data if PKCS7 unpadding throws (handling TS streams already 16-byte block aligned).

---

### 6. `src/kau_assistant/stream/downloader.py`
- **Role:** Multi-threaded segment downloader, key cache, exponential backoff, and atomic TS merger
- **Closest Analog:** [`src/kau_assistant/materials/downloader.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/materials/downloader.py#L14-L50) & [`src/kau_assistant/materials/downloader.py#L61-L131`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/materials/downloader.py#L61-L131)
- **Rationale:** `materials/downloader.py` demonstrates session-cookie authenticated `httpx.Client`, atomic writing to `.tmp`, duplicate detection, and file cleanup upon error.
- **Concrete Code Excerpt:**
  ```python
  def get_authenticated_httpx_client(
      settings: Settings,
      session_manager: SessionManager | None = None,
  ) -> httpx.Client:
      cookies: dict[str, str] = {}
      cache_path = settings.session_cache_path
      if cache_path.exists():
          try:
              with open(cache_path, "r", encoding="utf-8") as f:
                  data = json.load(f)
                  for cookie in data.get("cookies", []):
                      cookies[cookie["name"]] = cookie["value"]
          except Exception:
              cookies = {}

      return httpx.Client(
          cookies=cookies,
          headers={
              "User-Agent": (
                  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
              ),
              "Referer": settings.lms_url,
          },
          follow_redirects=True,
          timeout=30.0,
      )

  # Atomic streaming write via .tmp
  temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
  try:
      with open(temp_path, "wb") as f:
          for chunk in response.iter_bytes(chunk_size=chunk_size):
              f.write(chunk)
      temp_path.replace(target_path)
      return (target_path, downloaded_bytes, False)
  except Exception:
      temp_path.unlink(missing_ok=True)
      raise
  ```
- **Application:** Implement `SegmentDownloader`:
  - `download_stream(stream_info: StreamInfo, target_file: Path, overwrite: bool = False, on_progress: Callable[[DownloadProgress], None] | None = None) -> tuple[Path, int, bool]`
  - `_download_segment_with_retry(segment: StreamSegment, cache_dir: Path) -> Path` (with exponential backoff 1s/2s/4s up to 3 retries).
  - In-memory thread-safe `_key_cache: dict[str, bytes]` to fetch AES-128 keys once per unique URL.
  - Direct `.mp4` handling: streams straight to `.tmp` file and atomically replaces.
  - Atomic assembly `assemble_ts_segments_atomic(segment_paths, target_file)`. Cache located in `target_file.parent.parent / ".cache"` (ensuring same filesystem volume, avoiding `WinError 17`).

---

### 7. `src/kau_assistant/stream/sniffer.py`
- **Role:** Playwright network interceptor and DOM video fallback
- **Closest Analog:** [`src/kau_assistant/player/vod_player.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/vod_player.py#L28-L63) & [`src/kau_assistant/player/vod_player.py#L92-L113`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/vod_player.py#L92-L113)
- **Rationale:** `vod_player.py` attaches event listeners to Playwright `page` (`page.on("dialog")`), uses `page.evaluate` to inspect DOM elements, and removes listeners in `finally:`.
- **Concrete Code Excerpt:**
  ```python
  def _on_dialog(dialog: Dialog) -> None:
      logger.info(f"VOD auto-accepting popup: '{dialog.message}'")
      try:
          dialog.accept()
      except Exception as e:
          logger.debug(f"Failed to accept dialog: {e}")

  page.on("dialog", _on_dialog)
  ...
  finally:
      try:
          page.remove_listener("dialog", _on_dialog)
      except Exception:
          pass
  ```
- **Application:** Implement `StreamSniffer`:
  - Attach `page.on("response", _on_response)` listener.
  - `_on_response(response: Response)`: Checks if `.m3u8` in URL or content-type is `application/vnd.apple.mpegurl` or direct `.mp4` in video player requests. Stores candidate in thread-safe variable and triggers `threading.Event`.
  - DOM Fallback probe: `page.evaluate("""() => { const v = document.querySelector('video'); return v ? (v.currentSrc || v.src) : null; }""")`.
  - Context manager pattern or `start_sniffing(page)` / `stop_sniffing(page)` ensuring cleanup.

---

### 8. `src/kau_assistant/stream/runner.py`
- **Role:** Standalone `download-vod` pipeline orchestrator
- **Closest Analog:** [`src/kau_assistant/materials/runner.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/materials/runner.py#L171-L268) & [`src/kau_assistant/player/runner.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/runner.py#L161-L243)
- **Rationale:** `materials/runner.py` manages session authentication, course discovery, week filtering, progress callbacks, and result aggregation.
- **Concrete Code Excerpt:**
  ```python
  def run_materials_pipeline(
      course_query: str | None = None,
      week_query: str | int | None = "current",
      output_dir: Path | str | None = None,
      dry_run: bool = False,
      relogin: bool = False,
      headful: bool = False,
      settings: Settings | None = None,
      progress_callback: Callable[[str], None] | None = None,
  ) -> MaterialsRunResult:
      cfg = settings or get_settings()
      output_root = Path(output_dir) if output_dir else cfg.download_dir
      ...
      with SessionManager(settings=cfg, headful=headful) as sm:
          page = sm.get_authenticated_page()
          courses = extract_courses(page, cfg.lms_url)
          target_course = find_target_course(courses, course_query, mappings)
          ...
  ```
- **Application:** Implement `run_vod_download_pipeline`:
  - Filters candidate VODs for the week. Crucial distinction: standalone `download-vod` includes already-completed lectures by default (Assumption A-14-03 / D-14-02), while `video_index` selects a single lecture if given.
  - Path formatting: `output_root / course.clean_name / f"W{item.week_number:02d}" / f"W{item.week_number:02d}-{item.clip_number:02d}_{safe_title}.mp4"`.
  - Dry-run check: verifies if target `.mp4` already exists; marks `SKIPPED` or `DOWNLOADED` without launching browser.
  - Fast capture: launches Playwright, navigates to VOD, sniffs stream URL via `StreamSniffer` (taking ~2–3s), closes page immediately, then initiates high-speed multi-threaded download.
  - Progress reporting: utilizes Rich multi-progress bar (stderr) and constructs `VodDownloadRunResult`.

---

### 9. `src/kau_assistant/player/vod_player.py` (Modify)
- **Role:** Playwright player automation engine
- **Closest Analog:** [`src/kau_assistant/player/vod_player.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/vod_player.py#L64-L95)
- **Rationale:** Modifying the existing `play_vod` method to register stream sniffing without disrupting attendance heartbeat polling or modal handling.
- **Concrete Code Excerpt:**
  ```python
  def play_vod(
      self,
      page: Page,
      vod_url: str,
      title: str = "",
      options: PlaybackOptions | None = None,
      session_manager: SessionManager | None = None,
      on_progress: Callable[[PlaybackProgress], None] | None = None,
  ) -> PlaybackProgress:
      ...
      page.on("dialog", _on_dialog)
      try:
          page.goto(vod_url, wait_until="domcontentloaded")
          ...
      finally:
          try:
              page.remove_listener("dialog", _on_dialog)
          except Exception:
              pass
  ```
- **Application:**
  - Add parameter `on_stream_detected: Callable[[str], None] | None = None` to `play_vod`.
  - Inside `play_vod`, if `on_stream_detected` is provided, attach `_on_response` listener for `.m3u8` / `.mp4` stream URLs.
  - Once detected, invoke `on_stream_detected(stream_url)` exactly once (guarded by boolean flag) and do NOT block playback.
  - Cleanly remove response listener in `finally:`.

---

### 10. `src/kau_assistant/player/runner.py` (Modify)
- **Role:** Watch pipeline orchestrator
- **Closest Analog:** [`src/kau_assistant/player/runner.py`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/runner.py#L161-L177) & [`src/kau_assistant/player/runner.py#L292-L300`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/player/runner.py#L292-L300)
- **Rationale:** Connects `watch` execution to the background download thread when `--download` is active.
- **Concrete Code Excerpt:**
  ```python
  def watch_course_vods(
      settings: Settings,
      course_query: str,
      week_query: str | int | None = "current",
      video_index: int | None = None,
      *,
      dry_run: bool = False,
      update_notion: bool = False,
      player: VodPlayer | None = None,
      ...
  ) -> WatchResult:
  ```
- **Application:**
  - Add parameters `download: bool = False`, `preferred_quality: str = "best"`, `overwrite: bool = False`, `output_dir: Path | str | None = None`.
  - When `download` is True:
    - Prepare target path `output_root / target_course.clean_name / f"W{vod.week_number:02d}" / f"W{vod.week_number:02d}-{vod.clip_number:02d}_{safe_title}.mp4"`.
    - Hook `on_stream_detected` in `vod_player.play_vod`.
    - Launch download in a background daemon thread (`threading.Thread(target=_bg_download, daemon=True)`).
    - In `_bg_download`, wrap execution in `try-except Exception` so that download network failures NEVER interrupt the attendance loop (Decision D-14-04).
    - Wait for background thread completion before returning or advancing if video completes first.

---

### 11. `src/kau_assistant/cli.py` (Modify)
- **Role:** CLI option handling and command routing
- **Closest Analog:** [`src/kau_assistant/cli.py#L190-L255`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/cli.py#L190-L255) (`watch_group`) & [`src/kau_assistant/cli.py#L470-L535`](file:///D:/dev/kau-lxp-assistant/src/kau_assistant/cli.py#L470-L535) (`materials_command`)
- **Rationale:** Demonstrates Click option definitions, Console output, progress messages, and error handling.
- **Concrete Code Excerpt:**
  ```python
  @cli.command("materials")
  @click.option("--course", "course_query", type=str, default=None, help="...")
  @click.option("--week", "week_query", type=str, default="current", show_default=True, help="...")
  @click.option("--output-dir", "output_dir", type=click.Path(), default=None, help="...")
  @click.option("--dry-run", "dry_run", is_flag=True, help="...")
  @click.option("--json", "as_json", is_flag=True, help="...")
  @click.pass_context
  def materials_command(ctx, ...):
      err = Console(stderr=True)
      out = Console()
      ...
      if as_json:
          click.echo(result.model_dump_json(indent=2))
      else:
          render_materials_report(result, out)
  ```
- **Application:**
  - In `watch_group`:
    - Add `@click.option("--download", "download", is_flag=True, help="출석 시청과 함께 고속 백그라운드 영상 다운로드를 병행합니다.")`
    - Add `@click.option("--quality", "quality", type=str, default="best", help="다운로드 영상 화질 ('best', '1080p', '720p', 'worst')")`
    - Add `@click.option("--output-dir", "output_dir", type=click.Path(), default=None, help="다운로드 저장 디렉터리")`
    - Add `@click.option("--overwrite", "overwrite", is_flag=True, help="이미 존재하는 영상 파일도 덮어쓰기하여 새로 다운로드합니다.")`
    - Pass options to `watch_course_vods`.
  - Add `download-vod` standalone command:
    - Same options plus `--dry-run`, `--json`, `--relogin`, `--headed`.
    - Dispatches to `run_vod_download_pipeline`.
    - Outputs Rich table summary (or JSON when `--json` is active).

---

### 12. `tests/test_stream_parser.py`
- **Role:** Unit test for M3U8 parsing and quality selection
- **Closest Analog:** [`tests/test_filename_utils.py`](file:///D:/dev/kau-lxp-assistant/tests/test_filename_utils.py#L6-L44)
- **Rationale:** Test module checking string input against parsed objects with various edge cases.
- **Concrete Code Excerpt:**
  ```python
  def test_resolve_filename_rfc5987_utf8():
      header = "attachment; filename*=UTF-8''%EC%8B%A4%ED%97%98%EA%B5%90%EC%9E%AC.pdf"
      url = "https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001"
      resolved = resolve_filename(header, url, "기본자료")
      assert resolved == "실험교재.pdf"
  ```
- **Application:** Test master playlist parsing (multiple bandwidths/resolutions), quality selection (`1080p`, `720p`, `best`, `worst`), media playlist parsing (segments, durations, relative URIs with `urljoin`), and `#EXT-X-KEY` extraction.

---

### 13. `tests/test_stream_crypto.py`
- **Role:** Unit test for AES-128-CBC decryption and IV derivation
- **Closest Analog:** [`tests/test_filename_utils.py`](file:///D:/dev/kau-lxp-assistant/tests/test_filename_utils.py#L46-L75)
- **Rationale:** Pure unit tests validating cryptographic transforms with explicit and implicit inputs.
- **Application:** Test:
  - Encryption-decryption roundtrip using standard AES-128-CBC.
  - Implicit sequence number IV calculation per RFC 8216: sequence `1` -> `b'\x00'*15 + b'\x01'`.
  - Non-standard PKCS7 fallback: data with invalid padding doesn't raise exception, returns unpadded bytes.

---

### 14. `tests/test_stream_downloader.py`
- **Role:** Unit test for segment downloader, key caching, retry backoff, and TS merge
- **Closest Analog:** [`tests/test_material_downloader.py`](file:///D:/dev/kau-lxp-assistant/tests/test_material_downloader.py#L51-L185)
- **Rationale:** Tests HTTP client interactions, temporary files, skipping duplicates, and error cleanup using `tmp_path` fixture.
- **Concrete Code Excerpt:**
  ```python
  def test_download_material_file_direct_binary(tmp_path: Path, sample_item):
      mock_client = MagicMock(spec=httpx.Client)
      ...
      target_dir = tmp_path / "자료구조" / "W1"
      saved_path, size, is_skipped = download_material_file(mock_client, sample_item, target_dir)
      assert saved_path.exists()
      assert is_skipped is False

  def test_download_material_file_cleanup_on_error(tmp_path: Path, sample_item):
      mock_client = MagicMock(spec=httpx.Client)
      ...
      # .tmp file must be cleaned up
      tmp_files = list(target_dir.glob("*.tmp"))
      assert len(tmp_files) == 0
  ```
- **Application:** Test:
  - Multi-threaded segment download with mocked `httpx.Client`.
  - Key cache: verify key URL is fetched only once across 10 segments.
  - Atomic rename: `.mp4.tmp` renamed to `.mp4` upon 100% completion.
  - Skip duplicate: existing `.mp4` skipped unless `overwrite=True`.
  - Retry backoff: segment network error retried 3 times.

---

### 15. `tests/test_stream_sniffer.py`
- **Role:** Unit test for Playwright response interception and DOM fallback
- **Closest Analog:** [`tests/test_vod_player.py`](file:///D:/dev/kau-lxp-assistant/tests/test_vod_player.py#L25-L68)
- **Rationale:** Tests Playwright page events, `evaluate` callbacks, and timeout conditions using mocked `Page`.
- **Concrete Code Excerpt:**
  ```python
  def test_vod_player_successful_play_to_completion():
      player = VodPlayer()
      mock_page = MagicMock()
      mock_page.title.return_value = "4주차 1차시 강의 | 한국항공대학교 LXP"
      mock_page.url = "https://lxp.kau.ac.kr/mod/vod/view.php?id=8967"
      ...
      mock_page.evaluate.side_effect = mock_evaluate
  ```
- **Application:** Test:
  - `StreamSniffer` triggers callback when response URL contains `.m3u8`.
  - DOM probe triggers when response interception does not match.
  - Handlers cleanly deregistered after sniffing completion.

---

### 16. `tests/test_watch_download.py`
- **Role:** Integration test for `watch --download` background downloading and attendance fault isolation
- **Closest Analog:** [`tests/test_watch_runner.py`](file:///D:/dev/kau-lxp-assistant/tests/test_watch_runner.py#L122-L175)
- **Rationale:** Tests orchestration of `watch_course_vods` with mocked dependencies.
- **Concrete Code Excerpt:**
  ```python
  def test_watch_course_vods_playback_and_notion_update(monkeypatch, sample_courses, tmp_path):
      ...
      mock_player = MagicMock()
      mock_player.play_vod.return_value = PlaybackProgress(
          vod_url="https://lxp.kau.ac.kr/mod/vod/view.php?id=10",
          title="4주차 1차시",
          duration=60.0,
          current_time=60.0,
          progress_percent=100.0,
          is_completed=True,
      )
      result = watch_course_vods(...)
      assert result.completed_vods == 1
  ```
- **Application:** Test:
  - `watch_course_vods(download=True)` triggers background download when stream URL is sniffed.
  - Download failure (e.g. mock HTTP exception) logs warning, does NOT abort playback, and attendance finishes 100% (Decision D-14-04).

---

### 17. `tests/test_cli_download_vod.py`
- **Role:** CLI test for `download-vod` command and `watch` options
- **Closest Analog:** [`tests/test_cli_materials.py`](file:///D:/dev/kau-lxp-assistant/tests/test_cli_materials.py#L17-L104)
- **Rationale:** Tests Click CLI commands using `CliRunner` with `--json`, `--dry-run`, and option verification.
- **Concrete Code Excerpt:**
  ```python
  def test_materials_and_files_help():
      runner = CliRunner()
      res_materials = runner.invoke(cli, ["materials", "--help"])
      assert res_materials.exit_code == 0
      assert "--course" in res_materials.output
      assert "--week" in res_materials.output

  @patch("kau_assistant.materials.runner.run_materials_pipeline")
  def test_materials_dry_run_json(mock_run_pipeline):
      mock_run_pipeline.return_value = MaterialsRunResult(...)
      runner = CliRunner()
      result = runner.invoke(cli, ["materials", "--dry-run", "--json"])
      assert result.exit_code == 0
      data = json.loads(result.output)
      assert data["dry_run"] is True
  ```
- **Application:** Test:
  - `kau-assistant download-vod --help` displays all flags.
  - `kau-assistant download-vod --course "..." --dry-run --json` outputs expected JSON structure.
  - `kau-assistant watch --download --quality 1080p` passes options to runner.

---

## Shared Patterns

### 1. Pydantic Modeling & JSON Contract
- Models subclass `pydantic.BaseModel` with explicit type annotations.
- Statuses represented as `str, Enum` for straightforward JSON serialization (`model_dump_json(indent=2)`).
- Fields with mutable default values use `Field(default_factory=list)`.

### 2. Rich CLI Progress & Output Separation
- Ephemeral progress updates, spinners, and transfer speeds output exclusively to `Console(stderr=True)`.
- Final human-readable report tables and structured `--json` outputs go to standard stdout (`Console()` / `click.echo`).
- Enables clean piping: `kau-assistant download-vod --json | jq .` without stderr progress clutter corrupting stdout JSON.

### 3. Atomic File Assembly & Volume Isolation
- Temporary data during segment assembly or direct streaming is written to `<filename>.tmp` or `.cache/`.
- All temporary directories are created within the target `output_dir` (e.g. `downloads/.cache/...`) ensuring operations stay on the same filesystem volume.
- Finalization occurs via `Path.replace()` (`os.replace`), providing atomic metadata swap without cross-volume `WinError 17` risks.
- Errors trigger immediate cleanup via `temp_path.unlink(missing_ok=True)` in `except` blocks.

### 4. Session Cookie Reuse & HTTP Authentication
- Authenticated `httpx.Client` extracts cookies from `settings.session_cache_path` (storing Playwright `storage_state`).
- Sets identical `User-Agent` and `Referer` (`settings.lms_url`) headers to mirror browser traffic.

### 5. Concurrency & Error Isolation
- In `watch --download`, download tasks run in a background worker thread, decoupling line-rate segment downloads from the 1.0x real-time Coursemos attendance heartbeat.
- Download network interruptions are caught and logged as warnings; attendance playback loop continues unhindered (D-14-04).

### 6. Path Formatting & Filename Sanitization
- Naming format: `downloads/<과목명>/W{week:02d}/W{week:02d}-{clip:02d}_{sanitized_title}.mp4` (Decision D-14-10).
- Filenames sanitized via `kau_assistant.materials.filename_utils.sanitize_filename` to remove OS reserved characters (`<>:"/\\|?*`) and Windows reserved stems (`CON`, `PRN`, `AUX`).

---

## No Analog Found

### 1. Pure-Python RFC 8216 AES-128-CBC Decryption
- **Domain:** Cryptographic HLS segment deciphering.
- **Why no analog exists:** Previous phases handled direct PDF/document downloads or browser-rendered video playback; no cryptographic byte-manipulation previously existed in the codebase.
- **Architecture alignment:**
  - Implemented using `cryptography.hazmat.primitives.ciphers` (PyCA standard).
  - Designed as pure functional transforms with explicit typing (`bytes -> bytes`).
  - RFC 8216 §5.2 compliant: implicit IV calculated as `sequence_number.to_bytes(16, byteorder="big")`.
  - PKCS7 unpadding fallback to tolerate non-padded or block-aligned streams.

### 2. M3U8 Playlist Parsing & Quality Resolution
- **Domain:** HLS master and media playlist grammar parsing.
- **Why no analog exists:** HTML and JSON parsers existed (`BeautifulSoup`, `pydantic`), but no streaming manifest parser existed.
- **Architecture alignment:**
  - Implemented using official `m3u8` library (`m3u8.loads`).
  - Adapts `m3u8` variant streams and segments into strongly-typed Pydantic domain models (`StreamInfo`, `StreamVariant`, `StreamSegment`).

---

## Metadata

- **Files analyzed:** 17
- **Analogs mapped:** 15 existing code analogs
- **Newly introduced components:** 2 (AES-128 Decryptor, M3U8 Parser) with strict adherence to repository code conventions
- **Confidence rating:** HIGH

---

## PATTERN MAPPING COMPLETE
