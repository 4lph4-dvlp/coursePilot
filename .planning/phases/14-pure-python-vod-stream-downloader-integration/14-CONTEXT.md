# Phase 14: Pure-Python VOD Stream Downloader Integration - Context

**Gathered:** 2026-09-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 14 delivers a pure-Python HLS/m3u8 stream sniffer, segment downloader, and local MP4 assembler without requiring system `ffmpeg`:
1. 시스템에 `ffmpeg` 설치 없이 순수 파이썬만으로 동작하는 HLS/m3u8 파서 및 TS 세그먼트 다운로더/병합기 구현.
2. VOD 시청(`watch`) 시 `--download` 옵션을 지정하면 1.0배속 출석 인정 하트비트와 백그라운드 영상 다운로드를 동시에 완수.
3. 1.0배속 실시간 시청 대기 없이 영상 파일만 고속으로 로컬 저장할 수 있는 단독 서브커맨드 `coursepilot download-vod` 제공.
4. `#EXT-X-KEY:METHOD=AES-128` 암호화 스트림에 대해 세션 인증 기반 키 취득 및 세그먼트별 투명 복호화 내장.
5. 저장 경로 `downloads/<과목명>/W{주차}/W{주차}-{영상순번}_{영상제목}.mp4` 및 중복 시 건너뛰기(Skip), 임시 캐시를 통한 원자적 저장(Atomic Save).
6. Rich CLI 진행 바(stderr) 및 에이전트 연동용 `--json` 출력 지원.

</domain>

<decisions>
## Implementation Decisions

### 1. 다운로드 실행 트리거 및 출석 연동 정책
- **D-14-01:** `coursepilot watch` 실행 시 `--download` 플래그 명시 시에만 다운로드를 병행한다. 기본 `watch`는 1.0배속 출석 하트비트 시청만 수행하여 불필요한 디스크 용량 낭비를 방지한다.
- **D-14-02:** 출석 1.0배속 실시간 대기 없이 영상 파일만 즉시 고속으로 다운로드하는 단독 서브커맨드 `coursepilot download-vod`를 제공한다 (m3u8 스트림 감지 후 브라우저를 닫고 고속 세그먼트 병렬 다운로드).
- **D-14-03:** `watch --download` 실행 시 재생 시작 즉시 스트림 URL을 감지하여 백그라운드 스레드에서 최대 대역폭으로 세그먼트들을 고속 다운로드 완료한다.
- **D-14-04:** 출석 인정 격리 보장: 다운로드가 네트워크 일시 장애로 실패하더라도 브라우저 출석 재생은 절대 중단하지 않고 끝까지 완수한 뒤 경고/에러 로그만 보고한다.

### 2. 순수 파이썬 HLS 처리 및 파일 포맷
- **D-14-05:** 시스템에 `ffmpeg`가 없는 환경에서 수집된 다수의 HLS TS 세그먼트들을 순수 파이썬 바이너리 순차 결합(Concatenation) 후 `.mp4` 확장자로 저장한다. (추가 무거운 외부 바이너리 없이 가장 빠르고 안정적이며 팟플레이어/VLC/대부분의 미디어 플레이어에서 즉시 호환 재생 가능).
- **D-14-06:** AES-128 복호화 내장 지원: HLS 플레이리스트의 EXT-X-KEY 및 IV를 파싱하고 키 URL을 LXP 세션 인증으로 fetch하여 세그먼트별 투명 복호화 후 결합한다.
- **D-14-07:** 경량 표준 라이브러리 `m3u8` 패키지를 채택하여 마스터/미디어 플레이리스트, 세그먼트 URI, 암호화 키 등 표준 규격을 안정적으로 파싱한다.
- **D-14-08:** 마스터 플레이리스트에 다중 화질(1080p, 720p 등)이 존재할 경우, 강의 슬라이드/판서 가독성을 위해 최고 해상도/비트레이트 스트림을 자동 선택하며, CLI에 `--quality` 옵션을 제공한다.

### 3. 저장 경로 및 파일 네이밍 규칙
- **D-14-09:** 다운로드된 VOD 영상 파일의 기본 저장 디렉터리는 Phase 13과 통일된 `downloads/<과목명>/W{주차}/` 경로를 사용하여 학습자료 문서와 동영상을 통합 보관하고, `.env`의 `DOWNLOAD_DIR` 및 `--output-dir` 설정을 공유한다.
- **D-14-10:** 영상 파일명은 `W{주차}-{영상순번}_{영상제목}.mp4` (예: `W02-01_어휘분석기 구현.mp4`) 규칙을 적용하여 주차/순번 정렬과 강의 주제 식별을 동시에 만족한다. 파일명 특수문자는 Phase 13의 sanitization 유틸리티를 재사용한다.
- **D-14-11:** 이미 완료된 동일 파일명의 영상이 로컬에 존재할 경우 다운로드를 건너뛰며(Skip), 강제 재다운로드를 위해 `--overwrite` 플래그를 지원한다.
- **D-14-12:** 원자적 저장(Atomic Save): 세그먼트 다운로드 및 병합이 100% 완료된 후에만 최종 `.mp4` 파일명으로 확정/이동하여, 네트워크 중단이나 강제 종료 시 불완전하게 깨진 영상 파일이 남지 않도록 방지한다.

### 4. 네트워크 스니핑 및 스트림 다운로드 신뢰성
- **D-14-13:** 브라우저 m3u8 스트림 주소 감지는 Playwright 네트워크 응답 감시(`page.on('response')`)를 우선 인터셉트하고, blob URL 등으로 미감지 시 DOM video 속성을 보조 확인하는 하이브리드 스니핑 전략을 적용한다.
- **D-14-14:** `httpx` 기반 멀티스레드 병렬 다운로드(기본 4~8 워커 풀)를 채택하여 세그먼트들을 고속 병렬 수신하며, Playwright 세션 쿠키 및 User-Agent/Referer 헤더를 재사용한다.
- **D-14-15:** 세그먼트별 지수 백오프 자동 재시도(최대 3회, 1초/2초/4초 간격)를 적용하여 일시적 네트워크 장애를 복구한다.
- **D-14-16:** 다운로드 진행 상태는 Rich 실시간 프로그레스 바(stderr)로 시각화하고, 자동화 에이전트 연동을 위한 `--json` 머신 리포트 출력을 지원한다.

### the agent's Discretion
- 병렬 다운로드 기본 워커 풀 크기(4 vs 8) 세부 튜닝 및 HTTP 커넥션 풀 타임아웃 세부 파라미터.
- 임시 캐시 디렉터리 위치 (`downloads/.cache/...` 등) 및 정리 주기.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Roadmap & Requirements
- `.planning/ROADMAP.md` § Phase 14 — Pure-Python VOD Stream Downloader Integration
- `.planning/REQUIREMENTS.md` § VDL-01, VDL-02 — VOD stream downloader requirements

### Existing Code & Architecture
- `src/coursepilot/player/vod_player.py` — Playwright VOD navigation, heartbeat loop, dialog handling
- `src/coursepilot/player/runner.py` — Watch execution pipeline and targeting logic
- `src/coursepilot/session_manager.py` — Playwright session storage and authentication cookies
- `src/coursepilot/materials/filename_utils.py` — Filename sanitization utilities
- `src/coursepilot/config.py` — Application configuration and `.env` handling

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SessionManager`: 세션 쿠키 추출 및 HTTP 헤더 주입.
- `find_target_course`: 자연어 과목명 및 약어 퍼지 매칭.
- `sanitize_filename`: 파일명 내 OS 예약 문자 제거 및 정규화.
- `VodPlayer`: Playwright 기반 VOD 자동 진입 및 Video.js 요소 감지.

### Established Patterns
- Rich CLI 출력 분리: `Console(stderr=True)`로 진행 상태 및 프로그레스 바 출력, stdout은 최종 결과 리포트 또는 JSON만 출력.
- CLI 플래그 일관성: `--course`, `--week`, `--output-dir`, `--overwrite`, `--dry-run`, `--json`.

### Integration Points
- `src/coursepilot/stream/` (신규): HLS m3u8 파서, 세그먼트 다운로더, AES-128 복호화기, TS 병합기.
- `src/coursepilot/player/vod_player.py`: m3u8 스트림 응답 스니핑 리스너 등록.
- `src/coursepilot/player/runner.py`: watch 파이프라인 내 백그라운드 다운로드 스레드 연동.
- `src/coursepilot/cli.py`: `watch --download` 플래그 및 `download-vod` 신규 서브커맨드 등록.

</code_context>

<specifics>
## Specific Ideas

- 사용자가 `coursepilot watch --course "컴파일러" --week 2 --download` 실행 시:
  - 1.0배속으로 출석 인정 하트비트가 유지되면서, 백그라운드에서 HLS 세그먼트가 최대 속도로 병렬 다운로드되어 `downloads/컴파일러/W02/W02-01_어휘분석기.mp4`로 원자적 저장.
- 사용자가 `coursepilot download-vod --course "공수2" --week 3` 실행 시:
  - 출석 1.0배속 시청 없이 즉시 스트림 주소만 획득 후 브라우저를 닫고 고속으로 다운로드 완료.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-pure-python-vod-stream-downloader-integration*
*Context gathered: 2026-09-25*
