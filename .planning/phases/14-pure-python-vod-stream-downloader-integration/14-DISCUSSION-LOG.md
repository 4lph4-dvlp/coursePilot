# Phase 14: Pure-Python VOD Stream Downloader Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-25
**Phase:** 14-pure-python-vod-stream-downloader-integration
**Areas discussed:** 다운로드 실행 트리거 및 출석 연동 정책, 순수 파이썬 HLS 처리 및 파일 포맷, 저장 경로 및 파일 네이밍 규칙, 네트워크 스니핑 및 스트림 다운로드 신뢰성

---

## 다운로드 실행 트리거 및 출석 연동 정책

| Option | Description | Selected |
|--------|-------------|----------|
| `--download` 옵션 지정 시에만 병행 | 기본 `watch`는 출석 하트비트 시청만 수행하여 디스크 용량 낭비 방지 | ✓ |
| `watch` 실행 시 항상 기본 다운로드 | `--no-download` 플래그로 비활성화 | |
| `.env` 설정 기반 | `VOD_AUTO_DOWNLOAD=true/false`에 따라 기본 동작 결정 | |

**User's choice:** `--download` 옵션을 지정할 때만 다운로드 병행
**Notes:** 동영상 파일의 대용량 특성을 고려하여 명시적 플래그로만 저장

| Option | Description | Selected |
|--------|-------------|----------|
| 단독 다운로드 서브커맨드 `download-vod` | 1.0배속 시청 대기 없이 스트림 URL 감지 후 브라우저를 닫고 고속 세그먼트 다운로드 | ✓ |
| `watch --only-download` 플래그 | watch 명령어 내부에서 출석 하트비트 생략 | |
| 단독 다운로드 미지원 | 오직 `watch --download`로만 출석 중 다운로드 허용 | |

**User's choice:** 단독 다운로드 서브커맨드 `coursepilot download-vod` 제공
**Notes:** 이미 출석 완료된 영상이거나 오프라인 소장용으로 빠른 다운로드가 필요한 경우 지원

| Option | Description | Selected |
|--------|-------------|----------|
| 백그라운드 병렬 다운로드 | 재생 시작 즉시 스트림 URL을 감지하여 백그라운드 스레드에서 최대 대역폭으로 세그먼트 고속 다운로드 | ✓ |
| 실시간 청크 캡처 | 1.0배속 재생 시간 동안 스트리밍 요청을 순차 가로채기 | |
| 재생 완료 후 다운로드 | 1.0배속 출석 완료 후 다운로드 실행 | |

**User's choice:** 백그라운드 병렬 다운로드
**Notes:** 1.0배속 재생이 끝나는 동안 백그라운드에서 미리 다운로드를 완료하여 사용자 대기 시간 최소화

| Option | Description | Selected |
|--------|-------------|----------|
| 출석 인정 분리 보장 | 다운로드 실패 시에도 브라우저 출석 재생은 절대 중단하지 않고 끝까지 완수한 뒤 경고 보고 | ✓ |
| 다운로드 실패 시 즉시 중단 | 출석과 다운로드가 모두 성공해야 정상 종료 | |
| 다운로드 실패 시 완료 후 재시도 | 출석 완료 후 1회 재시도 | |

**User's choice:** 출석 인정 분리 보장
**Notes:** 다운로드 오류로 인해 학생의 출석 인정이 누락되는 사태 방지

---

## 순수 파이썬 HLS 처리 및 파일 포맷

| Option | Description | Selected |
|--------|-------------|----------|
| 순수 파이썬 TS 바이너리 순차 결합 후 `.mp4` 저장 | 외부 바이너리 없이 가장 빠르고 안정적이며 대부분의 플레이어에서 즉시 호환 재생 가능 | ✓ |
| 엄격한 ISO MP4 규격 패키징 | 순수 파이썬 MP4 remuxer 로직 채택 | |
| `.ts` 확장자로 결합 저장 | 원본 규격 유지 | |

**User's choice:** 순수 파이썬 TS 바이너리 순차 결합 후 `.mp4` 저장
**Notes:** `ffmpeg` 설치 없이도 팟플레이어, VLC 등 표준 미디어 플레이어에서 즉시 재생 가능

| Option | Description | Selected |
|--------|-------------|----------|
| AES-128 복호화 자동 처리 내장 | EXT-X-KEY 및 IV 파싱, 키 URL 세션 인증 fetch, 세그먼트별 투명 복호화 후 결합 | ✓ |
| 에이전트 재량 위임 | 리서처 분석 후 결정 | |
| 비암호화 HLS만 지원 | 암호화 감지 시 스킵 및 경고 | |

**User's choice:** AES-128 복호화 자동 처리 내장
**Notes:** 암호화된 스트림도 완벽하게 복호화하여 재생 가능한 비디오로 저장

| Option | Description | Selected |
|--------|-------------|----------|
| 경량 표준 라이브러리 `m3u8` 패키지 채택 | 플레이리스트, 세그먼트 URI, 암호화 키 등 표준 규격 완벽 지원 | ✓ |
| 외부 의존성 제로 자체 정규식 파서 | 내장 모듈만으로 파싱 | |
| 에이전트 재량 위임 | 의존성 복잡도 고려 결정 | |

**User's choice:** 경량 표준 라이브러리 `m3u8` 패키지 채택
**Notes:** 파이썬 표준 m3u8 파서로 파싱 안정성 확보

| Option | Description | Selected |
|--------|-------------|----------|
| 최고 해상도/비트레이트 스트림 자동 선택 | 강의 슬라이드/판서 가독성을 최우선으로 확보하고 `--quality` 옵션 지원 | ✓ |
| 720p(HD) 화질 기본 다운로드 | 속도와 용량 절충 | |
| 에이전트 재량 위임 | 자동 최적화 | |

**User's choice:** 최고 해상도/비트레이트 스트림 자동 선택
**Notes:** 칠판 판서 및 소스 코드 글씨 가독성을 위해 최고 화질 보장

---

## 저장 경로 및 파일 네이밍 규칙

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 13과 통일된 `downloads/<과목명>/W{주차}/` 경로 | 해당 주차 학습자료 문서와 동영상을 통합 보관하고 설정 공유 | ✓ |
| 동영상 전용 서브폴더 `downloads/<과목명>/videos/W{주차}/` | 자료 문서와 물리적 분리 | |
| 별도 루트 `videos/<과목명>/W{주차}/` | 완전히 독립된 루트 | |

**User's choice:** Phase 13과 통일된 `downloads/<과목명>/W{주차}/` 경로
**Notes:** 동일 주차 학습자료와 강의 영상을 한 폴더에서 편리하게 관리

| Option | Description | Selected |
|--------|-------------|----------|
| `W{주차}-{영상순번}_{영상제목}.mp4` | 주차/순번 정렬 및 파일명만으로 강의 주제 파악 가능 | ✓ |
| `W{주차}-{영상순번}.mp4` | 로드맵 명시 간결형 | |
| `[{과목약어}]_W{주차}-{영상순번}_{영상제목}.mp4` | 단독 이동 시에도 과목명 보존 | |

**User's choice:** `W{주차}-{영상순번}_{영상제목}.mp4` (예: `W02-01_어휘분석기 구현.mp4`)
**Notes:** 윈도우 탐색기에서 정렬과 내용 식별이 가장 최적화된 형식

| Option | Description | Selected |
|--------|-------------|----------|
| 이미 완료된 영상 파일 존재 시 건너뛰기(Skip) | 대용량 중복 트래픽 방지, 강제 재다운로드 시 `--overwrite` 지원 | ✓ |
| 항상 새로 다운로드하여 덮어쓰기 | 무조건 갱신 | |
| 파일명 넘버링 추가 | ` (1).mp4` 붙여 중복 보관 | |

**User's choice:** 이미 완료된 영상 파일 존재 시 건너뛰기(Skip)
**Notes:** 대역폭 및 디스크 용량 절약, 필요 시 `--overwrite`로 강제 다운로드

| Option | Description | Selected |
|--------|-------------|----------|
| 원자적 저장(Atomic Save) 처리 | 모든 세그먼트 다운로드 및 병합 완료 후 최종 확정하여 깨진 영상 잔존 방지 | ✓ |
| 최종 파일에 직접 append 및 실패 시 삭제 | 중간 파일 직접 기록 | |
| 에이전트 재량 위임 | 캐시 관리 구조 설계 | |

**User's choice:** 원자적 저장(Atomic Save) 처리
**Notes:** 다운로드 중단 시 불완전한 재생 불가 파일이 생기지 않도록 방지

---

## 네트워크 스니핑 및 스트림 다운로드 신뢰성

| Option | Description | Selected |
|--------|-------------|----------|
| 네트워크 이벤트 인터셉트 우선 + DOM 조회 보조 결합 | Playwright `page.on('response')` 우선, blob 미감지 시 DOM 속성 보조 | ✓ |
| 오직 Playwright 네트워크 응답 감시만 사용 | `.m3u8` 확장자 및 Content-Type 감지 | |
| 에이전트 재량 위임 | 렌더링 방식 분석 후 결정 | |

**User's choice:** 네트워크 이벤트 인터셉트 우선 + DOM 조회 보조 결합
**Notes:** Video.js의 다양한 비디오 초기화 패턴에 가장 안정적으로 대응

| Option | Description | Selected |
|--------|-------------|----------|
| `httpx` 기반 멀티스레드 병렬 다운로드 | 기본 4~8 워커로 고속 병렬 수신, Playwright 세션 쿠키/헤더 재사용 | ✓ |
| 단일 스레드 순차 다운로드 | 안정성과 CDN 서버 부하 최소화 | |
| 에이전트 재량 위임 | 워커 풀 크기 최적화 | |

**User's choice:** `httpx` 기반 멀티스레드 병렬 다운로드
**Notes:** 수십 초 내로 다운로드를 마칠 수 있는 고속 전송 속도 확보

| Option | Description | Selected |
|--------|-------------|----------|
| 세그먼트별 지수 백오프 자동 재시도 | 1초/2초/4초 간격 최대 3회 재시도로 일시 장애 극복 | ✓ |
| 세그먼트 1회 실패 시 즉시 중단 | 에러 즉시 보고 | |
| 에이전트 재량 위임 | 파라미터 최적화 | |

**User's choice:** 세그먼트별 지수 백오프 자동 재시도
**Notes:** 네트워크 순간 끊김에도 다운로드 성공률 극대화

| Option | Description | Selected |
|--------|-------------|----------|
| Rich 실시간 프로그레스 바(stderr) + `--json` 머신 리포트 지원 | CLI 표준 준수 및 세그먼트 수/진행률 시각화 | ✓ |
| 간결한 텍스트 로그만 출력 | 10% 단위 출력 | |
| 에이전트 재량 위임 | 통합 리포터 사용 | |

**User's choice:** Rich 실시간 프로그레스 바(stderr) + `--json` 머신 리포트 지원
**Notes:** 터미널 사용자와 AI 에이전트 호출 환경 모두 만족

---

## the agent's Discretion

- 병렬 다운로드 기본 워커 풀 크기(4~8) 및 세부 HTTP 커넥션 타임아웃 파라미터.
- 임시 캐시 디렉터리 경로 및 정리 정책.

## Deferred Ideas

- None — discussion stayed within phase scope.
