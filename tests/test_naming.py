"""Unit tests for task naming rules and smart title cleaning engine."""

import pytest
from coursepilot.domain.models import TaskType
from coursepilot.domain.naming import (
    clean_task_title,
    extract_week_and_title,
    format_task_title,
)

MAPPINGS = {"공학수학2": "공수2", "자료구조": "자구"}


def test_lecture_naming_convention():
    """D-01: Verify fixed format '[{과목약어}] {N}주차 {M}차시 강의 시청'."""
    title = format_task_title(
        "공학수학2",
        "1차시: 라플라스",
        TaskType.LECTURE,
        week_number=3,
        clip_number=1,
        course_mappings=MAPPINGS,
    )
    assert title == "[공수2] 3주차 1차시 강의 시청"

    # Default week/clip to 1 if None or <=0
    title_default = format_task_title(
        "공학수학2",
        "소개 영상",
        TaskType.LECTURE,
        week_number=None,
        clip_number=None,
        course_mappings=MAPPINGS,
    )
    assert title_default == "[공수2] 1주차 1차시 강의 시청"


def test_assignment_naming_conventions():
    """D-02 & D-03: Verify assignment naming with week and without week."""
    # D-02: With week number parameter
    title = format_task_title(
        "공학수학2",
        "행렬 연산 과제",
        TaskType.ASSIGNMENT,
        week_number=3,
        course_mappings=MAPPINGS,
    )
    assert title == "[공수2] 3주차 행렬 연산 과제 제출"

    # D-02: Week embedded in title
    title_embedded = format_task_title(
        "공학수학2",
        "3주차: 미분방정식 과제",
        TaskType.ASSIGNMENT,
        course_mappings=MAPPINGS,
    )
    assert title_embedded == "[공수2] 3주차 미분방정식 과제 제출"

    # D-03: Fallback without week
    title_no_week = format_task_title(
        "자료구조",
        "기말 프로젝트",
        TaskType.ASSIGNMENT,
        course_mappings=MAPPINGS,
    )
    assert title_no_week == "[자구] 기말 프로젝트 제출"


def test_quiz_and_forum_naming_conventions():
    """D-02: Verify Quiz uses '[퀴즈] {이름} 응시' and Forum uses '[토론] {이름} 참여'."""
    # Quiz with week
    q_title = format_task_title(
        "공학수학2",
        "쪽지시험",
        TaskType.QUIZ,
        week_number=2,
        course_mappings=MAPPINGS,
    )
    assert q_title == "[공수2] 2주차 [퀴즈] 쪽지시험 응시"

    # Forum without week
    f_title = format_task_title(
        "자료구조",
        "정렬 알고리즘 토론",
        TaskType.FORUM,
        course_mappings=MAPPINGS,
    )
    assert f_title == "[자구] [토론] 정렬 알고리즘 토론 참여"

    # Forum with week
    f_title_week = format_task_title(
        "자료구조",
        "그래프 탐색 토론",
        TaskType.FORUM,
        week_number=5,
        course_mappings=MAPPINGS,
    )
    assert f_title_week == "[자구] 5주차 [토론] 그래프 탐색 토론 참여"


def test_smart_title_cleaning():
    """D-04: HTML entity decoding, whitespace normalization, bracket tag stripping."""
    # HTML entities
    assert clean_task_title("과제 &amp; 실습 #1") == "과제 & 실습 #1"
    assert clean_task_title("알고리즘&#39;s 복잡도 &lt;O(n)&gt;") == "알고리즘's 복잡도 <O(n)>"
    assert clean_task_title("시스템&nbsp;프로그래밍") == "시스템 프로그래밍"

    # Redundant bracket tags
    assert clean_task_title("[과제] 2주차 연습문제") == "2주차 연습문제"
    assert clean_task_title("[HW]   네트워크 프로그래밍   ") == "네트워크 프로그래밍"
    assert clean_task_title("[Assignment] Project 1") == "Project 1"
    assert clean_task_title("[퀴즈] 중간 퀴즈") == "중간 퀴즈"
    assert clean_task_title("[토론] 토픽 토론") == "토픽 토론"

    # Multiple consecutive tags
    assert clean_task_title("[과제] [HW] 1주차 과제") == "1주차 과제"

    # Empty string safety
    assert clean_task_title("") == ""
    assert clean_task_title(None) == ""


def test_double_verb_prevention():
    """Verify trailing activity verbs are stripped to prevent redundant verbs like '제출 제출'."""
    # Title ends with '제출'
    title = format_task_title(
        "공학수학2",
        "2주차 실습과제 제출",
        TaskType.ASSIGNMENT,
        week_number=2,
        course_mappings=MAPPINGS,
    )
    assert title == "[공수2] 2주차 실습과제 제출"
    assert "제출 제출" not in title

    # Title ends with '응시'
    title_quiz = format_task_title(
        "공학수학2",
        "쪽지시험 응시",
        TaskType.QUIZ,
        week_number=1,
        course_mappings=MAPPINGS,
    )
    assert title_quiz == "[공수2] 1주차 [퀴즈] 쪽지시험 응시"
    assert "응시 응시" not in title_quiz

    # Title ends with '참여'
    title_forum = format_task_title(
        "자료구조",
        "토론 참여",
        TaskType.FORUM,
        week_number=4,
        course_mappings=MAPPINGS,
    )
    assert title_forum == "[자구] 4주차 [토론] 토론 참여"
    assert "참여 참여" not in title_forum


def test_unmapped_course_fallback():
    """Verify that unmapped courses safely use the original course name."""
    title = format_task_title(
        "우주항공학개론",
        "1차 과제",
        TaskType.ASSIGNMENT,
        week_number=1,
        course_mappings=MAPPINGS,
    )
    assert title == "[우주항공학개론] 1주차 1차 과제 제출"


def test_empty_remainder_fallback():
    """Verify that stripping week or tags does not result in an empty task name."""
    week_num, remainder = extract_week_and_title("[과제] 3주차")
    assert week_num == 3
    assert remainder == "과제"

    title = format_task_title(
        "공학수학2",
        "[과제] 3주차",
        TaskType.ASSIGNMENT,
        course_mappings=MAPPINGS,
    )
    assert title == "[공수2] 3주차 과제 제출"
