# Phase 17: Universal Skill Packaging, Multi-Agent Deployment & End-to-End Verification - Discussion Log

> Audit trail only. Research, planning, and execution use 17-CONTEXT.md; this file records the alternatives and user selections.

**Date:** 2026-10-04
**Phase:** 17-universal-skill-packaging-multi-agent-deployment-end-to-end
**Areas discussed:** 자연어 요청과 브리핑, JSON 계약 문서, 5개 에이전트 배포, 실사이트 검증 경계

---

## 자연어 요청과 브리핑

### 1. 넓은 '이번 주 학업 현황' 요청에서 어떤 명령을 우선할까?

| Option | Selected |
|--------|----------|
| progress 우선 | yes |
| check 우선 |  |
| 둘 다 실행 |  |

**User choice:** progress 우선. 마감·과제를 명시하면 check를 사용한다.

### 2. 공지·질문·게시판 요청을 어떤 명령으로 연결할까?

| Option | Selected |
|--------|----------|
| 요청에 맞춰 분기 | yes |
| 항상 board |  |
| 애매하면 질문 |  |

**User choice:** 공지→notices, 질문·답변→qna, 넓은 게시판→board로 분기한다.

### 3. 명시적 자료·VOD 다운로드 요청의 결과를 어떻게 보고할까?

| Option | Selected |
|--------|----------|
| 항목별 결과와 저장 경로 | yes |
| 건수 요약 중심 |  |
| 상태별 묶음 |  |

**User choice:** 각 항목의 다운로드 성공·열람만 성공(viewed_only)·실패 상태와 실제 저장 경로를 표시한다.

### 4. 일부 과목 수집 실패 또는 활동 0건을 어떻게 알릴까?

| Option | Selected |
|--------|----------|
| 경고를 먼저 표시 | yes |
| 요약 뒤에 경고 |  |
| 과목별로 함께 표시 |  |

**User choice:** 확인하지 못한 과목·활동을 브리핑 전에 경고하고, 뒤이어 유효한 결과를 보여준다. 0건을 모두 완료로 해석하지 않는다.

---

## JSON 계약 문서

### 1. 신규 명령의 JSON 계약을 어떤 구조로 정리할까?

| Option | Selected |
|--------|----------|
| 명령별 독립 섹션 | yes |
| 공통 모델 목록 확장 |  |
| 빠른 안내 + 모델 목록 |  |

**User choice:** 명령별 독립 섹션에 호출법, 결과 필드, 상태 해석, 예시를 함께 배치한다.

### 2. 새 명령의 예시 JSON은 어느 상황까지 담을까?

| Option | Selected |
|--------|----------|
| 정상 + 주의 사례 | yes |
| 정상 예시만 |  |
| 상태별 전체 예시 |  |

**User choice:** 각 명령에 정상 예시와 혼동하기 쉬운 부분 실패·누락·열람만 성공 등의 주의 사례를 담는다.

### 3. 독립 notion-scheduler 계약을 CoursePilot 문서에서 얼마나 다룰까?

| Option | Selected |
|--------|----------|
| 경계와 참조만 명시 | yes |
| 자주 쓰는 필드 요약 |  |
| 전체 계약 복제 |  |

**User choice:** CoursePilot 학업 sync·시청 완료 결과의 경계를 설명하고 일반 작업 필드는 독립 스킬 계약 문서로 연결한다.

### 4. 신규 JSON 계약 설명의 언어는 무엇일까?

| Option | Selected |
|--------|----------|
| 한국어 중심 | yes |
| 한영 병기 |  |
| 영어 중심 |  |

**User choice:** 한국어 중심으로 설명하고 JSON 필드명과 명령어는 원문 그대로 유지한다.

---

## 5개 에이전트 배포

### 1. 일괄 배포에서 한 에이전트의 설치가 실패하면?

| Option | Selected |
|--------|----------|
| 나머지는 계속 설치 | yes |
| 전체 중단·되돌리기 |  |
| 사전 점검 후 시작 |  |

**User choice:** 나머지 설치를 계속하고 에이전트별 성공·실패 및 경로를 보고한다.

### 2. 재배포의 기본 형태는?

| Option | Selected |
|--------|----------|
| 링크로 재배포 | yes |
| 복사로 재배포 |  |
| 기존 방식 유지 |  |

**User choice:** 설치된 5개 에이전트에 저장소 스킬 폴더를 가리키는 링크를 사용한다.

### 3. 홈 폴더가 없는 에이전트는?

| Option | Selected |
|--------|----------|
| 스킬 폴더를 미리 생성 |  |
| 없는 에이전트는 건너뛰기 | yes |
| 배포 전에 멈추기 |  |

**User choice:** 건너뛰고 이유를 보고한다. 로드맵의 5개 배포 성공 기준은 유지하므로 건너뛴 에이전트가 있으면 배포 검증은 미완료다.

### 4. 설치된 에이전트를 어디까지 확인할까?

| Option | Selected |
|--------|----------|
| 파일·실행 모두 확인 | yes |
| 파일만 확인 |  |
| 5개 실행 필수 |  |

**User choice:** 링크와 문서 접근을 검사하고 실행 가능한 에이전트에서 자연어 호출을 시험한다. 실행할 수 없는 항목은 미검증으로 기록한다.

### 5. 기존 CoursePilot 복사본을 링크로 교체할까?

| Option | Selected |
|--------|----------|
| 확인된 CoursePilot 복사본은 링크로 교체 | yes |
| 복사본은 유지 |  |
| 교체 전 확인 요청 |  |

**User choice:** SKILL.md 이름으로 확인된 CoursePilot 복사본은 링크로 교체한다. 다른 스킬은 보호한다.

### 6. 자연어 호출 시험의 폭은?

| Option | Selected |
|--------|----------|
| 에이전트마다 읽기 요청 3개 | yes |
| 에이전트마다 대표 요청 1개 |  |
| 기본 요청만 |  |

**User choice:** 실행 가능한 에이전트마다 새 세션에서 진도율, 공지, Q&A 읽기 요청을 각각 시험한다.

### 7. 검증 결과는 어느 수준으로 남길까?

| Option | Selected |
|--------|----------|
| 에이전트별 결과표 | yes |
| 통과·실패만 기록 |  |
| 전체 대화 기록 |  |

**User choice:** 에이전트별 요청·선택 CLI 명령·성공/실패 이유를 표로 기록하고 개인 학업 데이터 전문은 보존하지 않는다.

### 8. 저장소 이동으로 링크가 끊기면?

| Option | Selected |
|--------|----------|
| 진단하고 재연결 방법 안내 | yes |
| 자동으로 새 위치 탐색 |  |
| 일반 설치 오류만 표시 |  |

**User choice:** 끊긴 링크를 진단하고 현재 저장소 위치에서 다시 설치하도록 안내한다.

### 9. 독립 notion-scheduler 스킬의 설치 상태도 확인할까?

| Option | Selected |
|--------|----------|
| 별도 상태로 확인 | yes |
| 문서 안내만 |  |

**User choice:** 별도 상태로 확인하되 선택 사항이므로 없어도 CoursePilot 배포 실패로 보지 않고 설치를 추천하는 안내만 한다.

### 10. GitHub 원격 주소가 없는 독립 스킬의 설치법을 지금 어떻게 안내할까?

| Option | Selected |
|--------|----------|
| 이름과 독립 설치 문서 참조 |  |
| 현재 로컬 경로 명시 |  |
| GitHub 공개 후 추가 | yes |

**User choice:** 현재 CoursePilot 배포 문서에는 이름과 역할만 언급하고, 설치 안내는 GitHub 신규 저장소 공개 준비가 끝난 뒤 추가한다. 현재 머신의 절대 경로를 배포 문서에 넣지 않는다.

**Additional context:** The user wants the independent notion-scheduler skill prepared for a new GitHub repository. Read-only inspection found its clean Git repository already at D:/dev/notion-scheduler outside CoursePilot, with no configured remote. GitHub publication was deferred from Phase 17.
**Clarification:** A missing standalone Scheduler Agent Skill is optional and should prompt a recommendation, not fail CoursePilot deployment.

---

## 실사이트 검증 경계

### 1. 읽기 전용 명령은 어느 수강 과목 범위까지 검증할까?

| Option | Selected |
|--------|----------|
| 현재 수강 과목 전체 | yes |
| 대표 과목 2~3개 |  |
| 명령당 한 과목 |  |

**User choice:** 실행 시점에 확인되는 현재 수강 과목 전체에 check, progress, notices, qna를 실행하고 과목별 성공·실패 건수를 기록한다. 과거의 7개 과목 수를 고정 가정하지 않는다.

### 2. materials와 download-vod 실제 다운로드를 어디까지 검증할까?

| Option | Selected |
|--------|----------|
| 각각 한 항목 실제 실행 | yes |
| 계획·탐색만 확인 |  |
| 여러 항목 실제 실행 |  |

**User choice:** 대표 과목의 자료 1개와 VOD 1개를 실제 다운로드하여 파일·상태를 확인하고 생성한 로컬 시험 파일을 정리한다. 자료 방문은 LXP 열람 상태를 바꿀 수 있음을 인지한다.

### 3. watch 실제 재생은 어디까지 검증할까?

| Option | Selected |
|--------|----------|
| 시작·상태·중단 시험 | yes |
| 드라이런만 |  |
| 영상 하나 완료 |  |

**User choice:** 대상 목록 드라이런 후 영상 하나를 짧게 재생하고 watch status를 확인한 다음 watch stop으로 중단한다. 일부 LXP 시청 진도가 남을 수 있다.

### 4. Notion 실데이터 검증은 어디까지 실행할까?

| Option | Selected |
|--------|----------|
| 실제 조회 + 미리보기만 | yes |
| 로컬 모의 데이터만 |  |
| 통제된 실제 수정 1건 |  |

**User choice:** 독립 패키지 경유 실제 Scheduler 조회와 sync 및 시청 이력 완료 처리 드라이런만 수행한다. 실제 생성·수정 0건을 보장한다.

---

## Agent Discretion

- Representative live test items, safe local temporary paths, command internals, and concise evidence format within the decisions in 17-CONTEXT.md.

## Deferred Ideas

- 독립 notion-scheduler 스킬을 GitHub 신규 저장소로 공개할 준비를 별도 작업으로 진행한다. 2026-10-04 확인: 저장소는 이미 D:/dev/notion-scheduler에 있으며 CoursePilot 디렉터리 밖이고 Git 작업 트리는 깨끗하지만 remote는 없다. Phase 17의 CoursePilot 스킬 배포와 별도 범위다.
