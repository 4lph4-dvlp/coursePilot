---
phase: "14"
slug: "pure-python-vod-stream-downloader-integration"
status: ready
nyquist_compliant: true
wave_0_complete: false
created: "2026-09-25"
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-mock |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_stream_*.py tests/test_watch_download.py tests/test_cli_download_vod.py` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~12 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_stream_*.py tests/test_watch_download.py tests/test_cli_download_vod.py`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | VDL-01 | T-14-02 | In-memory key usage & PKCS7 unpad | unit | `uv run pytest tests/test_stream_crypto.py` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | VDL-01 | — | N/A | unit | `uv run pytest tests/test_stream_parser.py` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | VDL-01 | T-14-01, T-14-03 | Safe index filenames & atomic replace | unit/integration | `uv run pytest tests/test_stream_downloader.py` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 2 | VDL-02 | — | Hybrid network & DOM sniffing | unit/integration | `uv run pytest tests/test_stream_sniffer.py` | ❌ W0 | ⬜ pending |
| 14-02-02 | 02 | 2 | VDL-02 | — | Attendance isolation on failure | integration | `uv run pytest tests/test_watch_download.py` | ❌ W0 | ⬜ pending |
| 14-02-03 | 02 | 2 | VDL-02 | — | Rich stderr and clean stdout | integration | `uv run pytest tests/test_cli_download_vod.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_stream_parser.py` — stubs for VDL-01 playlist parsing
- [ ] `tests/test_stream_crypto.py` — stubs for VDL-01 AES-128 decryptor
- [ ] `tests/test_stream_downloader.py` — stubs for VDL-01 parallel segment downloader
- [ ] `tests/test_stream_sniffer.py` — stubs for VDL-02 Playwright network/DOM sniffer
- [ ] `tests/test_watch_download.py` — stubs for VDL-02 watch runner background download integration
- [ ] `tests/test_cli_download_vod.py` — stubs for VDL-02 CLI command and options
- [ ] Dependencies: `uv add m3u8 cryptography`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real LMS video download & VLC playback | VDL-01, VDL-02 | Requires real live student credentials and active course enrolment | Run `coursepilot download-vod --course <과목명> --week 1` and open the generated `.mp4` file in VLC or PotPlayer to confirm video and audio play smoothly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending 2026-09-25
