# Phase 18: Selected Materials Contract and Attachment Manifest - Pattern Map

**Mapped:** 2026-10-09
**Files analyzed:** 18 proposed new/modified files
**Analogs found:** 18 / 18 structural matches; no existing implementation proves a closed attachment set or a source-bound receipt.

The new module names below are **planning candidates**, not approved public names. D-18-09 requires review of exact CLI flags and JSON before implementation. Only git-tracked source paths are named as analogs. The legacy `materials` / `files` path and its unversioned JSON remain the compatibility baseline.

## File Classification

| New/Modified File | Role | Data Flow | Closest Tracked Analog | Match Quality |
|---|---|---|---|---|
| `src/coursepilot/materials/models.py` | model | transform | `src/coursepilot/materials/models.py` | exact, legacy shapes must stay stable |
| `src/coursepilot/materials/manifest.py` (proposed) | service/utility | transform | `src/coursepilot/materials/models.py`, `src/coursepilot/scraper/material_parser.py` | partial; no digest/proof implementation |
| `src/coursepilot/materials/evidence.py` (proposed) | service/utility | file-I/O | `src/coursepilot/materials/downloader.py`, `src/coursepilot/config.py` | partial; no source-bound receipt |
| `src/coursepilot/materials/runner.py` | service | request-response, batch | `src/coursepilot/materials/runner.py` | exact for discovery/orchestration, not selection |
| `src/coursepilot/materials/downloader.py` | service | streaming, file-I/O | `src/coursepilot/materials/downloader.py` | exact for atomic binary storage only |
| `src/coursepilot/scraper/material_parser.py` | utility | transform | `src/coursepilot/scraper/material_parser.py` | exact for coarse modules, partial for detail inspection |
| `src/coursepilot/materials/reporter.py` | utility | transform | `src/coursepilot/materials/reporter.py` | role match |
| `src/coursepilot/cli.py` | controller | request-response | `src/coursepilot/cli.py` | exact |
| `skills/coursepilot/SKILL.md` | config/documentation | request-response | `skills/coursepilot/SKILL.md` | exact |
| `skills/coursepilot/JSON_CONTRACT.md` | config/documentation | transform | `skills/coursepilot/JSON_CONTRACT.md` | exact |
| `tests/test_material_models.py` | test | transform | `tests/test_material_models.py` | exact |
| `tests/test_material_parser.py` | test | transform | `tests/test_material_parser.py` | exact |
| `tests/test_material_downloader.py` | test | streaming, file-I/O | `tests/test_material_downloader.py` | exact |
| `tests/test_materials_runner.py` | test | request-response, batch | `tests/test_materials_runner.py` | exact |
| `tests/test_cli_materials.py` | test | request-response | `tests/test_cli_materials.py` | exact |
| `tests/test_reporter.py` | test | transform | `tests/test_reporter.py` | role match |
| `tests/test_contract_doc.py` | test | transform | `tests/test_contract_doc.py` | exact |
| `tests/fixtures/lms_material_detail_*.html` (proposed) | test fixture | transform | `tests/fixtures/lms_course_materials.html` | partial; course list fixture only |

## Pattern Assignments

### `src/coursepilot/materials/models.py` and proposed `manifest.py` (model/service, transform)

**Analog:** `src/coursepilot/materials/models.py:3-5,8-15,18-46,49-69`. Preserve `MaterialItem`, `MaterialDownloadResult`, and `MaterialsRunResult` serialization for bare legacy `materials` / `files`. Add separate selected-mode request, manifest, completeness, attachment and per-file result types; explicit version and discriminated complete/unknown state belong in the new contract. Do not infer complete from `is_completed`, `download_url`, or `saved_path`.

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class MaterialStatus(str, Enum):
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    VIEWED_ONLY = "viewed_only"
    FAILED = "failed"
    PLANNED = "planned"

class CourseMaterialsResult(BaseModel):
    course_id: str
    course_name: str
    target_week: str
    items: list[MaterialDownloadResult] = Field(default_factory=list)
```

**Core limit:** `MaterialItem` has exactly one `download_url` (`models.py:18-35`); `MaterialDownloadResult` has exactly one `saved_path` (`models.py:37-46`). An inspected module with two attachments needs a distinct attachment collection and file result, not reused one-file fields. No existing canonical JSON/digest function exists in `src/coursepilot/materials/`; planner must specify ordered digest fields and duplicate-identity rejection.

### `src/coursepilot/scraper/material_parser.py` and proposed detail fixtures (utility/fixture, transform)

**Analog:** `src/coursepilot/scraper/material_parser.py:11-31`; fixture `tests/fixtures/lms_course_materials.html:37-69`. Reuse course-section parsing for the bounded coarse manifest without visiting a module detail page:

```python
return [
    MaterialItem(
        course_id=course.course_id, course_name=course.clean_name,
        week_number=activity.week_number, module_id=activity.module_id,
        title=activity.title, url=activity.url,
        is_completed=activity.is_completed, start_date=activity.start_date,
        due_date=activity.due_date, raw_due_date=activity.raw_due_date,
        is_overdue=not activity.is_completed and is_past_deadline(activity.due_date),
        is_available=activity.is_available,
    )
    for activity in parse_course_activities(html, course)
    if activity.module_type in {"ubfile", "resource"}
]
```

**Parser/import pattern:** `material_parser.py:3-8` uses `re`, `urljoin`, BeautifulSoup and absolute `coursepilot.*` imports. For detail inspection, use a separate function that reports `complete` only for a recognized, closed attachment container; unresolved viewers, hidden/paginated content, duplicate IDs, truncation and unsupported layouts return `unknown` with a bounded reason. Existing `extract_pluginfile_url` uses `soup.find` and returns immediately on the first anchor/object/iframe/embed (`material_parser.py:34-61`), so it is **not** an enumeration pattern. The tracked fixture is a course page with module links and contains no detail-page attachment list.

**Ambiguity caveat:** `src/coursepilot/scraper/course_sections.py:76-97` silently skips duplicate module IDs with a `seen` set. The selected-mode identity check must detect ambiguity before constructing an approval digest; the coarse parser alone cannot prove uniqueness.

### `src/coursepilot/materials/runner.py` (service, request-response/batch)

**Analog:** `src/coursepilot/materials/runner.py:188-212,216-257,259-282`. Keep `SessionManager`, course lookup, `CourseNavigator` and course-page parsing as the discovery seam. Branch selected-mode work **before** the legacy batch call at `runner.py:235-250`:

```python
navigator.navigate_to_course(page, c)
html = page.content()
materials = parse_materials_from_course_sections(html, c)
target_week, selected_materials = resolve_candidate_materials(materials, week_query)

course_res = process_course_materials(
    course=c,
    materials=selected_materials,
    target_week=target_week,
    output_root=output_root,
    client=client,
    dry_run=dry_run,
    no_download=no_download,
    progress_callback=progress_callback,
    page=page,
)
```

**Existing whole-batch assumption:** `resolve_candidate_materials` selects all modules in the chosen week (`runner.py:38-67`); `process_course_materials` loops over **every** supplied material and invokes `download_material_file` or browser fallback (`runner.py:70-85,130-160`). `tests/test_materials_runner.py:97-128` explicitly expects three downloads from three items. Selected mode must resolve one exact course/module/file, re-observe only that module's complete attachment set, compare source identity and its **full module** digest, then execute only that file. A changed same-week sibling module must not stale the approved module.

**Effect/error pattern:** `runner.py:99-111` exits before view/download in dry-run; `runner.py:142-178` records per-item download errors while continuing. For selected mode, validate version, selector, bounds and effect approval before session/detail access; stale, incomplete and fatal schema/config failures stop before download. Item-level network failure can preserve already verified sibling outcomes. Detail inspection and selected reinspection may mark LMS viewed state because `downloader.py:60-66` performs an authenticated GET on `item.url`; expose that effect at the CLI boundary. `src/coursepilot/scraper/navigator.py:75-83` validates course-page activity coverage before returning content.

### `src/coursepilot/materials/downloader.py` and proposed `evidence.py` (service, streaming/file-I/O)

**Analog:** `src/coursepilot/materials/downloader.py:22-57,69-159`, `src/coursepilot/config.py:24-38`. Reuse authenticated `httpx.Client` and sanitized filename, length check, temporary file, atomic replacement and cleanup:

```python
resolved_name = resolve_filename(
    content_disposition=content_disposition,
    url=str(response.url),
    default_name=item.title,
    content_type=content_type,
)
safe_name = sanitize_filename(resolved_name)
target_dir.mkdir(parents=True, exist_ok=True)
target_path = target_dir / safe_name

temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
downloaded_bytes = 0
try:
    with open(temp_path, "wb") as f:
        for chunk in response.iter_bytes(chunk_size=chunk_size):
            f.write(chunk)
            downloaded_bytes += len(chunk)
    if expected_bytes is not None and downloaded_bytes != expected_bytes:
        raise IOError(f"Byte mismatch: expected {expected_bytes}, received {downloaded_bytes}")
    temp_path.replace(target_path)
    return (target_path, downloaded_bytes, False)
except Exception:
    temp_path.unlink(missing_ok=True)
    raise
```

**Do not copy the selection/skip shortcuts:** HTML recursion calls `extract_pluginfile_url` and follows its first result (`downloader.py:85-116`); browser fallback uses `viewer_link.first` and `button.first` (`downloader.py:162-186`). Neither binds action to a chosen attachment ID. The current duplicate guard considers only same filename and `Content-Length` (`downloader.py:130-139`); browser fallback likewise compares only byte size (`downloader.py:190-202`). Selected retry needs a receipt or equivalent evidence tied to course/module/file identity, full manifest digest and verified local bytes before returning `verified_existing`. Validate final URL/origin and destination confinement before write; `config.py:31-38` is the existing `Path.resolve()` / `is_relative_to()` guard shape, though its absolute-path policy is not sufficient for selected output containment.

### `src/coursepilot/cli.py` (controller, request-response)

**Analog:** `src/coursepilot/cli.py:694-795`. Keep existing `@click.option` names/defaults and alias, route legacy invocations to the current pipeline, serialize JSON once on stdout and progress to stderr:

```python
@cli.command("materials")
@click.option("--course", "course_query", type=str, default=None,
              help="과목 이름, 약칭, 또는 과목 ID (생략 시 전체 과목)")
@click.option("--week", "week_query", type=str, default="current", show_default=True,
              help="주차 ('current', 'all', 또는 주차 번호)")
@click.pass_context
def materials_command(ctx: click.Context, course_query: str | None, week_query: str, ...) -> None:
    ...

if as_json:
    click.echo(result.model_dump_json(indent=2))
else:
    render_materials_report(result, out)

if result.failed_count > 0:
    ctx.exit(1)
ctx.exit(0)

cli.add_command(materials_command, name="files")
```

The abbreviated signature above is a location guide; copy the full existing declaration from `cli.py:694-758`. Existing exception path exits 2 (`cli.py:780-782`), failed items exit 1, otherwise 0. Decide new selected-mode failure JSON/exit mapping at the publication checkpoint; unknown version and invalid selection must fail before session/file effects. `files` must still accept the old flags and output. If adding a Click group, prove bare `materials` behavior with the existing CLI tests before changing dispatch.

### `src/coursepilot/materials/reporter.py` (utility, transform)

**Analog:** `src/coursepilot/materials/reporter.py:22-84`. If selected mode gets human output, keep rendering separate from execution and display each actual file outcome, not merely module viewed state:

```python
for course_res in result.courses:
    for item_res in course_res.items:
        if item_res.status == MaterialStatus.DOWNLOADED:
            status_text = "[green]다운로드 완료[/green]"
        elif item_res.status == MaterialStatus.SKIPPED:
            status_text = "[cyan]건너뜀(동일)[/cyan]"
        elif item_res.status == MaterialStatus.VIEWED_ONLY:
            status_text = "[blue]열람 완료[/blue]"
        else:
            status_text = "[red]실패[/red]"
```

`reporter.py:53-84` assembles size/path details and a separate failure list. The selected reporter should label `unknown`/stale/error without claiming a saved file. JSON still comes directly from typed models in the CLI.

### `skills/coursepilot/SKILL.md` and `JSON_CONTRACT.md` (docs, request-response/transform)

**Analogs:** `skills/coursepilot/SKILL.md:26-35,165-174`; `skills/coursepilot/JSON_CONTRACT.md:99-115,176-190`. The skill gives concrete command routes, effect permissions, and evidence interpretation. Its existing instructions say:

```text
강의자료 목록 점검: materials --week all --dry-run --json
자료 다운로드를 사용자가 요청했을 때만 materials --course "과목명" --week N --json
```

Preserve those as legacy guidance and add reviewed versioned coarse → approved inspect → approved exact select examples. State inspection/reinspection can alter LMS viewed state; never equate `item.is_completed`, `planned`, `viewed_only`, or a planned path with saved bytes. `JSON_CONTRACT.md:99-115` has legacy normal/planned JSON examples; add the new versioned normal, partial, stale, unknown and verified-existing examples **after** D-18-09 names and schema review. `JSON_CONTRACT.md:188-190` requires exactly one JSON object on stdout and Click usage errors at exit 2.

### Focused tests and fixtures (test, matching flows)

**Model analog:** `tests/test_material_models.py:58-95` builds nested Pydantic results, calls `model_dump_json()`, parses with `json.loads`, and asserts exact key/status values. Add version discriminant, complete/unknown, bounded counts/text and legacy unchanged-shape checks.

**Parser analog:** `tests/test_material_parser.py:11-61` reads a tracked HTML fixture with `Path(__file__).parent / "fixtures"`, then asserts `module_id`, week, title, completion and URL. `:65-91` uses short HTML strings for anchor/object/iframe/embed. Add sanitized recognized one/two-file and indeterminate detail fixtures; assert unknown for unsupported/ambiguous/hidden/truncated layouts. No current detail fixture proves completeness.

**Downloader analog:** `tests/test_material_downloader.py:53-75` mocks `httpx.Client.stream` and verifies actual bytes under `tmp_path`; `:78-101` pins the unsafe legacy name/length skip; `:130-164` pins HTML redirect behavior; `:188-216` pins browser button fallback. Test selected file ID → exact URL binding, source-bound receipt/byte recheck, path containment, partial cleanup and no sibling stream. Keep the legacy skip test as compatibility evidence, not selected-mode evidence.

**Runner analog:** `tests/test_materials_runner.py:19-59,97-128,159-173,216-245` uses `pytest.fixture`, `MagicMock` and `@patch` to exercise multi-module processing, dry-run no-view and item error isolation. Add no-detail coarse manifest, explicit inspection effect, same-week sibling unchanged, stale added/missing/renamed/duplicate attachment rejection **before** download, and single-file retry checks.

**CLI analog:** `tests/test_cli_materials.py:17-31,34-73,76-121` uses `CliRunner` and patches `run_materials_pipeline` to assert `materials` and `files` help, flags, JSON and exit codes. Add version/selector validation before patched network calls, inspect approval, one-JSON-object stdout, and legacy alias parity.

**Reporter/docs analog:** `tests/test_reporter.py:316-362` asserts rendered labels and envelope fields; `tests/test_contract_doc.py:20-23,65-112,115-140` extracts fenced JSON, validates samples against Pydantic, checks field mentions, and pins skill routes. Extend to the selected contract version and sample matrix while retaining its explicit unversioned legacy-material assertion (`test_contract_doc.py:99-107`).

## Shared Patterns

### Session and viewed-state boundary

**Source:** `src/coursepilot/materials/runner.py:210-219`, `src/coursepilot/materials/downloader.py:22-66`. Reuse `SessionManager` for authenticated page discovery and `get_authenticated_httpx_client` for binary download. A GET of a material URL is potentially an LMS completion effect. The coarse manifest stops at course HTML; inspected/selected operations disclose and require the approved effect before detail navigation. Credentials/cookies stay inside the client construction and never enter JSON, receipts, docs or logs.

### Domain failure and output

**Source:** `src/coursepilot/materials/runner.py:142-178`, `src/coursepilot/cli.py:763-791`. Core returns typed file outcomes for recoverable item failures. CLI writes progress to stderr with `Console(stderr=True)` and JSON to stdout with `model_dump_json`; `ctx.exit` controls status. Do not copy `logger.exception("Failed to download material %s: %s", item.title, e)` into selected mode because LMS title and raw exception could expose personal or credential-bearing source text. Emit bounded safe error codes/messages.

### Local file safety

**Source:** `src/coursepilot/materials/downloader.py:118-159`, `src/coursepilot/config.py:24-38`. Sanitize remote filenames, check resolved path stays under the intended output root, stream to a temporary file, verify bytes, then atomically replace. Add source-bound content evidence for selected retries; a planned path or equal length does not prove ownership/current content.

## No Direct Analog Found

| File/behavior | Role | Data Flow | Gap for planner |
|---|---|---|---|
| Proposed `materials/manifest.py`: closed detail enumeration and full module digest | service/utility | transform | The parser returns one link; no tracked detail fixture proves a complete Coursemos attachment set. Use RESEARCH.md proof predicate and keep unproven layouts `unknown`. |
| Proposed `materials/evidence.py`: source-bound local receipt | service/utility | file-I/O | The only existing skip uses name/size. Design receipt identity, current-source check and byte hash before selected retry. |
| Proposed `tests/fixtures/lms_material_detail_*.html` | test fixture | transform | Current material fixture is a course section list only; create sanitized closed and indeterminate layouts without personal LMS payloads. |

## Metadata

**Analog search scope:** tracked `src/coursepilot/materials/`, `src/coursepilot/scraper/`, `src/coursepilot/cli.py`, `src/coursepilot/config.py`, `skills/coursepilot/`, material/contract tests, and the course HTML fixture.
**Files scanned:** 19 tracked source/doc/test files and 1 tracked fixture; candidate paths checked with `git ls-files --`.
**Pattern extraction date:** 2026-10-09.
**Scope:** Offline mapping only; no live LMS or account access. Phase 18 requirements MCON-01..03 and decisions D-18-01..09 govern the plan. Exact public flags/JSON require the D-18-09 review checkpoint before implementation.
