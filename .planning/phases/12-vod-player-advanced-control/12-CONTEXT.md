# Phase 12: VOD Player Advanced Control & Retroactive Notion Sync - Context

**Gathered:** 2026-09-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 12 builds upon the Phase 09-11 VOD player and CLI runner to deliver precise user-driven targeting, live state visibility, execution lifecycle management (pause/stop), and retroactive Notion synchronization:

1. **정밀 타겟팅 (`--video-index`)**: 특정 주차의 N번째 영상만 지정하여 시청할 수 있는 인덱스 필터링.
2. **과목명 퍼지 매칭**: `기초전자정보실험`과 같은 유사어/약칭을 공식 과목명으로 유연하게 매핑.
3. **실시간 상태 파일 기반 진행률 추적**: `watch_state.json`을 통한 5초 단위 상태 기록 (상태, 과목, 주차, 영상 제목, 인덱스/전체, 시간, 진행률, 남은 시간, PID).
4. **진행률 조회 및 중단 명령어**: `coursepilot watch status`, `coursepilot watch stop`.
5. **사후 Notion 완료 처리**: `coursepilot watch sync-notion`을 통해 시청 완료 후 나중에 요청해도 최근 시청 영상을 노션에 '완료'로 동기화.

</domain>

<decisions>
## Implementation Decisions

### 1. 재생 배속 및 동시성 원칙
- **D-12-01:** **1.0배속 정속 및 단일 순차 재생 원칙 엄수**. 1회차 수강은 배속 재생 시 Coursemos 서버에서 출석 인정을 무효화하며, 다중 영상 병렬 재생은 동일 계정 중복 접속 충돌을 유발하므로 1.0배속 단일 순차 재생 큐를 확고히 유지한다.

### 2. 정밀 타겟팅 및 과목명 해석
- **D-12-02:** `--video-index` (1-based int, e.g. `--video-index 2`) 옵션을 추가한다. 지정 시 해당 주차의 N번째 영상만 필터링하여 재생한다.
- **D-12-03:** 과목명 해석기(`find_target_course`)에 퍼지/부분 토큰 매칭 알고리즘을 강화하여, `기초전자정보실험`처럼 사용자가 부정확한 명칭을 입력해도 공식 과목명(`기초전자실험`)으로 안정적으로 해석한다.

### 3. 실시간 상태 추적 및 수명 주기 제어
- **D-12-04:** 재생 중 5초 간격으로 캐시 디렉터리(`~/.cache/coursepilot/watch_state.json`)에 현재 재생 스냅샷(status: `idle`|`running`|`completed`|`stopped`|`error`, course_name, target_week, video_title, video_index, total_videos, duration, current_time, progress_percent, remaining_seconds, pid)을 원자적으로 기록한다.
- **D-12-05:** `coursepilot watch status [--json]` 서브커맨드를 추가한다. 다른 대화 세션이나 에이전트가 백그라운드 프로세스를 방해하지 않고 현재 진행률과 남은 시간을 즉시 확인할 수 있다.
- **D-12-06:** `coursepilot watch stop [--json]` 서브커맨드를 추가한다. 상태 파일의 PID를 읽어 백그라운드 재생 프로세스에 종료 신호를 전달하고, 브라우저를 안전하게 닫고 상태를 `stopped`로 갱신한다.

### 4. 사후 Notion 완료 처리
- **D-12-07:** 시청이 완료된 영상들의 메타데이터(과목명, 주차, 영상 제목, 완료 시각)를 `watch_history.json`에 보관한다.
- **D-12-08:** `coursepilot watch sync-notion [--course <name>] [--json]` 서브커맨드를 구현한다. 처음에 `--update-notion` 없이 시청했더라도, 나중에 사용자가 "방금 본 영상 노션 완료해줘"라고 요청하면 최근 시청된 영상들을 Notion Scheduler DB에서 찾아 `상태 = "완료"`로 업데이트한다.

### 5. 엣지 케이스 복원력 (Resilience)
- **D-12-09:** 버퍼링/네트워크 멈춤 시 15초 이상 진도 미진행 감지 시 `video.play()` 재시도(최대 3회), 해결 불가 시 `page.reload()` 후 이어보기(Resume) 다이얼로그 자동 승인.
- **D-12-10:** 절전 모드 복귀 시 wall-clock 오차에 휘둘리지 않고 DOM `currentTime`과 세션 쿠키 상태를 검증하여 이어서 재생.
- **D-12-11:** 장시간 재생 중 Moodle 세션 만료 시 로그인 창 리다이렉트를 감지하여 자동 재로그인 후 해당 영상 이어보기로 복구.

</decisions>

<specifics>
## Specific Requirements & Behaviors

- **Status Query Response**:
  - `status`: 진행 중인 영상의 제목, 남은 분/초, 전체 N개 중 현재 M번째 영상 진행 중임을 콘솔 및 JSON으로 제공.
- **Stop Command Behavior**:
  - 프로세스 종료 시 열려 있는 브라우저 인스턴스가 좀비로 남지 않도록 Playwright 및 브라우저 프로세스 안전 정리.
- **Sync-notion Command Behavior**:
  - Notion Scheduler DB에서 해당 작업명을 정확히 조회하여 이미 '완료'인 작업은 skip, 미완료인 작업만 '완료'로 갱신.

</specifics>
