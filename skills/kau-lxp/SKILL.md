---
name: kau-lxp
description: "Checks the student's KAU LMS (LXP) for incomplete lectures, assignments, and quizzes and their deadlines, and previews or applies a deadline sync to the student's Notion Scheduler through the local kau_assistant CLI. Use when the user asks about coursework status, pending lectures or assignments, upcoming or overdue deadlines, or uploading deadlines to Notion — for example '과제 확인해줘', '미완료 강의 알려줘', '노션에 올려줘'."
---

# kau-lxp

## 1. 저장소 위치

Repository root: `{{KAU_LXP_REPO}}`

위 Repository root 줄이 여전히 `{{KAU_LXP_REPO}}`라는 글자 그대로라면(개발용 `--link` 설치인 경우), 이 스킬 폴더 안의 `repo-root.txt` 파일에 적힌 한 줄짜리 경로를 대신 읽어서 사용하세요.

## 2. 실행 규칙

항상 다음 형태로 명령을 실행하세요:

```
uv --directory "{{KAU_LXP_REPO}}" run python -m kau_assistant <check|sync> --json
```

- 표준출력(stdout)만 JSON으로 파싱하세요. 표준에러(stderr)는 진행 상황/로그 텍스트이므로 절대 파싱하지 마세요.
- 터미널에 표시되는 Rich(색상/테두리) 리포트를 그대로 채팅에 붙여넣지 마세요. 항상 JSON을 다시 마크다운으로 구성해서 보여주세요.
- 종료 코드: `0` 성공 / `1` 부분 실패(결과는 여전히 유효하며 오류도 함께 표시) / `2` 치명적 오류(`errors[].message`를 보여주고 중단).
