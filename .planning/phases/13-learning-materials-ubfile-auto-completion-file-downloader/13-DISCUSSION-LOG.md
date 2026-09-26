# Phase 13: Learning Materials (ubfile) Auto-Completion & File Downloader - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-25
**Phase:** 13-learning-materials-ubfile-auto-completion-file-downloader
**Areas discussed:** 저장 경로 및 폴더 구조, 열람 및 다운로드 실행 정책, CLI 명령어 인터페이스 설계

---

## 저장 경로 및 폴더 구조

| Option | Description | Selected |
|--------|-------------|----------|
| 프로젝트 하위 `downloads/<과목명>/W{주차}/` | 프로젝트 하위에 저장하고 `.env`의 `DOWNLOAD_DIR` 설정 및 에이전트/CLI 프롬프트 경로 요청 반영 | ✓ |
| `~/Downloads/KAU/<과목명>/W{주차}/` | 사용자 PC 기본 다운로드 폴더에 일괄 저장 | |
| `downloads/<과목명>/` | 주차 구분 없이 평탄하게 저장 | |

**User's choice:** 프로젝트 하위 `downloads/<과목명>/W{주차}/`에 저장하고, `.env`의 `DOWNLOAD_DIR` 설정으로 경로 커스텀 지원하고, 에이전트에서 프롬프트를 통해 특정 조건과 저장위치를 요청하면 요청을 따른다.
**Notes:** 로컬 중복 파일 존재 시 파일 크기를 비교하여 동일 시 Skip, 불일치/변경 시 덮어쓰기 선택.

---

## 열람 및 다운로드 실행 정책

| Option | Description | Selected |
|--------|-------------|----------|
| 열람 + 다운로드 기본 동시 수행 | 기본적으로 둘 다 수행하되 `--no-download`(열람만) 지원 | ✓ |
| 다운로드만 기본 수행 | 별도 옵션(`--read`) 지정 시만 LXP 열람 처리 | |
| 열람만 기본 수행 | 별도 옵션(`--download`) 지정 시만 파일 다운로드 | |

**User's choice:** 기본적으로 열람(LXP 진도율 이수)과 파일 다운로드를 함께 수행하되, 옵션으로 `--no-download`(열람만) 지원.
**Notes:** 스마트 처리 채택 — LXP 열람(방문) 처리는 '미열람' 자료만 방문하고, 다운로드는 로컬에 파일이 없는 모든 자료를 받아줌.

---

## CLI 명령어 인터페이스 설계

| Option | Description | Selected |
|--------|-------------|----------|
| `coursepilot materials` | 약칭 `files` 및 `download` 별칭도 함께 지원 | ✓ |
| `coursepilot download` | 단일 다운로드 명령어 | |
| `coursepilot resources` | 단일 리소스 명령어 | |

**User's choice:** `coursepilot materials` (약칭 `files` 및 `download` 별칭도 함께 지원).
**Notes:**
- `--course` 생략 시 전체 수강 과목 순차 처리, 지정 시 해당 과목만 처리 (기존 `check`와 동일한 패턴).
- Notion Scheduler 연동 제외: 학습자료는 마감 기한이 없으므로 Notion DB 오염 방지를 위해 제외.

---

## Agent Discretion

- Playwright 쿠키 기반 `httpx` 또는 `urllib` 직접 스트림 다운로드 vs Playwright `download` 이벤트 활용 방식 선정.
- 파일명 특수문자/공백 정규화 및 HTTP `Content-Disposition` 헤더 처리 구현 상세.

## Deferred Ideas

- None — discussion stayed within phase scope.
