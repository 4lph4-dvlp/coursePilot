# Phase 17: Universal Skill Packaging, Multi-Agent Deployment & End-to-End Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-26
**Phase:** 17-universal-skill-packaging-multi-agent-deployment-end-to-end-verification
**Areas discussed:** SKILL.md 구조화 및 에이전트 트리거 설계, E2E 실사이트 검증 범위 및 라이브 테스트 전략, 5개 에이전트 배포 및 링크 무결성 검증, JSON_CONTRACT.md 확장 및 자동 계약 검증 테스트

---

## SKILL.md 구조화 및 에이전트 트리거 설계

### Q1: 본문 섹션 구조 구성 방식
| Option | Description | Selected |
|--------|-------------|:--------:|
| 기능/인텐트별 독립 섹션 구성 | 기존 §4(check), §5(sync), §6(watch)에 이어 §7 종합 진도율(progress), §8 공지/Q&A(board), §9 학습자료(materials), §10 VOD 다운로드(download-vod)로 명확히 분리 | ✓ |
| 조회형 vs 실행형 2대 그룹화 | [조회/브리핑](check, progress, board)과 [동기화/다운로드/재생](sync, watch, materials, download-vod)의 2대 대분류 체계로 구성 | |
| You decide | 에이전트 토큰 효율과 가독성을 고려해 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 기능/인텐트별 독립 섹션 구성
**Notes:** 각 기능의 목적과 사용법이 명확히 분리되어 에이전트가 오판단하지 않도록 독립 섹션 유지.

### Q2: 자연어 트리거 발화 및 description 확장 방식
| Option | Description | Selected |
|--------|-------------|:--------:|
| 대표 한국어 발화 8~10개 엄선 + 인텐트 매핑 가이드 | 프롬프트 토큰을 절약하면서 '진도율 확인', '공지/Q&A', '자료 다운', '영상 다운' 등 상황별 최적 커맨드 분기 명시 | ✓ |
| 최대 키워드 나열형 | frontmatter description에 가능한 모든 한국어/영어 동의어와 문장 변형을 포괄적으로 수록 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 대표 한국어 발화 8~10개 엄선 + 인텐트 매핑 가이드
**Notes:** 불필요한 토큰 낭비를 줄이고 모호한 사용자 질문을 올바른 서브커맨드로 유도.

### Q3: 대화창 마크다운 렌더링 지침 정의
| Option | Description | Selected |
|--------|-------------|:--------:|
| 서브커맨드별 마크다운 렌더링 템플릿 명시 | check, sync처럼 progress(3단 대시보드), board(과목별 공지 표), materials(다운로드 목록/경로)의 표준 출력 레이아웃을 SKILL.md에 구체적으로 규정 | ✓ |
| 유연한 상황별 자유 요약 | 에이전트가 JSON 결과 데이터를 바탕으로 사용자의 질문 맥락에 맞춰 자유롭게 구성하여 응답하도록 지침만 제시 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 서브커맨드별 마크다운 렌더링 템플릿 명시
**Notes:** 에이전트 간 일관된 사용자 경험 제공 및 3단 대시보드 가시성 확보.

### Q4: 실행 모드(동기 vs 비동기) 지침 정의
| Option | Description | Selected |
|--------|-------------|:--------:|
| 작업 특성별 실행 모드 분리 | 실시간 재생(watch)만 비동기 백그라운드 태스크로 위임하고, 고속 다운로드(download-vod) 및 자료(materials), 제어(watch status/stop)는 동기 즉시 실행으로 명시 | ✓ |
| 미디어 관련 일괄 백그라운드화 | watch뿐 아니라 download-vod, materials 대량 다운로드까지 모두 백그라운드 비동기 태스크로 실행하도록 안내 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 작업 특성별 실행 모드 분리
**Notes:** 실제 재생이 걸리는 watch만 비동기로 넘기고, 고속 처리 작업은 즉시 응답하도록 분리.

---

## E2E 실사이트 검증 범위 및 라이브 테스트 전략

### Q1: 실사이트 읽기/대시보드/공지 조회 검증 범위
| Option | Description | Selected |
|--------|-------------|:--------:|
| 7개 전 과목 전수 조회 검증 | check, progress, notices, qna를 7개 수강 과목 전체에 대해 실행하여 모든 파서 및 3단 대시보드 무결성 입증 | ✓ |
| 2~3개 대표 과목 선별 검증 | 네트워크 지연을 줄이기 위해 활동이 많은 대표 과목을 지정해 스모크 테스트 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 7개 전 과목 전수 조회 검증
**Notes:** 전체 수강 과목에서 파싱 실패나 예외 없이 0-defect 동작하는지 전수 확인.

### Q2: 파일 및 비디오 다운로드 실사이트 검증 수위
| Option | Description | Selected |
|--------|-------------|:--------:|
| 1개 대표 과목 핀포인트 스모크 다운로드 | download-vod 및 materials를 1개 과목 1개 항목에 한해 실제로 다운로드하여 파일 생성 및 스트림 결합 무결성 검증 | ✓ |
| 드라이런/매니페스트 파싱 위주 검증 | 실제 대용량 파일 다운로드는 생략하고 URL 스니핑 및 매니페스트 유효성까지만 확인 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 1개 대표 과목 핀포인트 스모크 다운로드
**Notes:** 네트워크 부하를 줄이면서도 실제 다운로드 완료 및 로컬 파일 유효성을 1회 핀포인트 입증.

### Q3: VOD 자동 재생(watch) 실사이트 라이브 검증 방식
| Option | Description | Selected |
|--------|-------------|:--------:|
| 드라이런 + 라이브 시작/진행/중단(status/stop) 라이프사이클 검증 | dry-run 목록 검증 후, 실제 1개 영상 재생을 시작하여 status 확인 후 stop으로 안전 중단 검증 | ✓ |
| 초단기 영상 1편 실제 100% 완강 검증 | 길이가 가장 짧은 클립을 찾아 1.0배속으로 실제 끝까지 완강 및 출석 인정 반영 검증 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 드라이런 + 라이브 시작/진행/중단(status/stop) 라이프사이클 검증
**Notes:** 장시간 대기 없이 재생 세션 시작, 상태 갱신, 안전 종료 전체 라이프사이클을 안전하게 검증.

### Q4: Notion Scheduler DB 연동 검증 수위
| Option | Description | Selected |
|--------|-------------|:--------:|
| 실데이터 조회 + 순수 드라이런(0건 쓰기 보장) 검증 | 실제 Scheduler DB 스키마와 페이지는 정상 쿼리하되, 쓰기는 드라이런으로 차단하여 0건 생성/수정 무결성 검증 | ✓ |
| 단일 항목 실반영 후 롤백 검증 | 1개 작업을 실제로 동기화한 뒤 변경 확인 및 원복 수행 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 실데이터 조회 + 순수 드라이런(0건 쓰기 보장) 검증
**Notes:** 학생의 기존 개인 노션 스케줄러 데이터베이스가 테스트 쓰기로 오염되지 않도록 철저히 보호.

---

## 5개 에이전트 배포 및 링크 무결성 검증

### Q1: 5개 지원 에이전트 배포 방식
| Option | Description | Selected |
|--------|-------------|:--------:|
| --link 심볼릭 링크 유지 및 5개 에이전트 링크 무결성 검증 | 소스 변경이 즉시 모든 에이전트에 반영되도록 링크 상태를 점검하고 필요시 갱신 | ✓ |
| 완전 독립 복사본(copy) 배포 | 각 에이전트 홈 폴더에 실제 파일들을 독립 복사하여 심볼릭 링크 의존성 제거 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) --link 심볼릭 링크 유지 및 5개 에이전트 링크 무결성 검증
**Notes:** 저장소 개발 변경 사항이 실시간으로 5개 에이전트에 반영되는 개발용 링크 모드 유지.

### Q2: 배포 명령 실행 방식 (CLI 옵션 확장 여부)
| Option | Description | Selected |
|--------|-------------|:--------:|
| --agent all 일괄 배포 옵션 추가 | install-skill에 'all' 키워드를 지원하여 5개 에이전트 전체에 한 번에 링크/설치되도록 CLI 개선 및 테스트 반영 | ✓ |
| 기존 CLI 유지 (5회 순차 호출) | installer.py의 단일 agent 인자 구조를 유지하고 루프 또는 순차 커맨드로 5개 에이전트 개별 설치 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) --agent all 일괄 배포 옵션 추가
**Notes:** 단일 명령어로 5개 에이전트 전체를 원터치 일괄 배포/링크 가능하도록 지원.

### Q3: 미존재 에이전트 홈 디렉터리 처리 정책
| Option | Description | Selected |
|--------|-------------|:--------:|
| 부모 홈 폴더 자동 생성 및 5개 에이전트 선제 배포 | 디렉터리가 없더라도 생성하여 링크를 걸어둠으로써 향후 에이전트 실행 시 즉시 스킬 활성화 보장 | ✓ |
| 존재하는 에이전트 홈에만 배포 및 미존재 시 건너뛰기 | 사용자의 실제 머신에 홈 폴더가 이미 존재하는 에이전트에만 링크하고 나머지는 안내 후 스킵 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 부모 홈 폴더 자동 생성 및 5개 에이전트 선제 배포
**Notes:** 향후 새로운 에이전트를 설치하더라도 즉시 coursepilot 스킬이 감지되도록 선제 링크 구성.

### Q4: 배포 후 파일 및 링크 무결성 검증 자동화
| Option | Description | Selected |
|--------|-------------|:--------:|
| pytest 검증 테스트 스위트 추가 | test_installer.py에 5개 에이전트 전체 경로의 SKILL.md, JSON_CONTRACT.md, repo-root.txt 링크 유효성을 검증하는 자동 테스트 추가 | ✓ |
| CLI 실행 콘솔 결과로만 확인 | 별도 pytest 추가 없이 install-skill 실행 결과 테이블로 성공 여부 검증 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) pytest 검증 테스트 스위트 추가
**Notes:** CI 및 회귀 테스트 단계에서 5개 에이전트 타깃 경로의 파일 무결성을 기계적으로 보장.

---

## JSON_CONTRACT.md 확장 및 자동 계약 검증 테스트

### Q1: 신규 서브커맨드 모델 명세 범위
| Option | Description | Selected |
|--------|-------------|:--------:|
| 신규 4대 서브커맨드 모델 및 필드 테이블 전수 기술 | progress, board, materials, download-vod의 모든 DTO 모델(필드명, 타입, Nullable, 설명)을 check/sync 수준으로 완전 문서화 | ✓ |
| 최상위 Report 모델 위주 요약 기술 | 하위 중첩 모델은 대표 구조만 요약하고 최상위 Report envelope 위주로 간결하게 수록 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 신규 4대 서브커맨드 모델 및 필드 테이블 전수 기술
**Notes:** 에이전트가 JSON 출력을 안전하게 파싱할 수 있도록 모든 모델/필드 완전 문서화.

### Q2: 가상 예시 JSON 페이로드 수록 수준
| Option | Description | Selected |
|--------|-------------|:--------:|
| 4개 신규 서브커맨드 각각 완전한 가상 JSON 예시 블록 수록 | progress, board, materials, download-vod 모두 실제 출력과 일치하는 현실적인 가상 JSON 수록 | ✓ |
| 핵심 조회형(progress, board) 2개만 예시 수록 | 다운로드/자료 등은 모델 필드 표로만 안내하고 핵심 브리핑 커맨드 2개만 JSON 블록 수록 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 4개 신규 서브커맨드 각각 완전한 가상 JSON 예시 블록 수록
**Notes:** 에이전트 프롬프트 참조 및 pytest 계약 테스트를 위한 실제 규격의 예시 페이로드 제공.

### Q3: tests/test_contract_doc.py 자동 검증 범위 확장
| Option | Description | Selected |
|--------|-------------|:--------:|
| 신규 4개 보고서 모델 전체로 pytest 자동 검증 확장 | ProgressReport, BoardReport, MaterialReport, DownloadVodReport의 모든 필드 백틱 누락 검사 및 예시 JSON 자동 모델 검증 적용 | ✓ |
| 예시 JSON 유효성만 확장 | 필드 백틱 전수 검사는 제외하고 4개 예시 JSON의 Pydantic 검증만 테스트에 추가 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) 신규 4개 보고서 모델 전체로 pytest 자동 검증 확장
**Notes:** 문서와 코드 간 단 하나의 필드 오차도 허용하지 않도록 100% 기계적 일관성 검증.

### Q4: 스키마 버전 규칙 및 공통 필드 정책
| Option | Description | Selected |
|--------|-------------|:--------:|
| schema_version: 1 통일 및 비파괴 확장 정책 명시 | 모든 신규 서브커맨드가 공통 envelope(schema_version: 1, command, errors 등)을 준수하며 필드 추가 시 v1 유지 명시 | ✓ |
| 서브커맨드별 개별 버전 관리 | 기능별로 독립된 스키마 버전 필드 도입 | |
| You decide | 에이전트 재량에 위임 | |

**User's choice:** (Recommended) schema_version: 1 통일 및 비파괴 확장 정책 명시
**Notes:** 에이전트 파싱 규칙을 단일화하고 v1 규격 내에서 안정적인 호환성 유지.

---

## the agent's Discretion

- SKILL.md 내 세부 자연어 발화 문구의 정밀 튜닝.
- 5개 에이전트 배포 시 Windows 환경(symlink vs junction) 세부 플래그 처리.
- 스모크 테스트 대상 1개 대표 과목(예: 기전실 등)의 구체적 선정.

## Deferred Ideas

- None — discussion stayed within phase scope.
