from datetime import datetime
import pytest

from coursepilot.scraper.date_parser import (
    KST,
    is_past_deadline,
    parse_lms_date,
)


def test_parse_standard_iso_and_dots():
    # Format: YYYY-MM-DD HH:MM:SS
    dt, fb = parse_lms_date("2026-09-25 23:59:00")
    assert not fb
    assert dt == datetime(2026, 9, 25, 23, 59, 0, tzinfo=KST)

    # Format: YYYY.MM.DD (금) HH:MM
    dt, fb = parse_lms_date("2026.09.25 (금) 23:59")
    assert not fb
    assert dt == datetime(2026, 9, 25, 23, 59, 0, tzinfo=KST)

    # Format: YYYY/MM/DD HH:MM
    dt, fb = parse_lms_date("2026/09/25 23:59")
    assert not fb
    assert dt == datetime(2026, 9, 25, 23, 59, 0, tzinfo=KST)


def test_parse_korean_text_formats():
    # Format: 2026년 9월 25일 23:59
    dt, fb = parse_lms_date("2026년 9월 25일 23:59")
    assert not fb
    assert dt == datetime(2026, 9, 25, 23, 59, 0, tzinfo=KST)

    # Format with weekday: 2026년 09월 25일 (금) 23:59:30
    dt, fb = parse_lms_date("2026년 09월 25일 (금) 23:59:30")
    assert not fb
    assert dt == datetime(2026, 9, 25, 23, 59, 30, tzinfo=KST)


def test_parse_range_formats():
    # Range format with tilde: extracts the second (due date) part
    dt, fb = parse_lms_date("2026-09-01 00:00 ~ 2026-09-07 23:59")
    assert not fb
    assert dt == datetime(2026, 9, 7, 23, 59, 0, tzinfo=KST)

    # Tilde with date only
    dt, fb = parse_lms_date("~ 2026-09-15 18:00")
    assert not fb
    assert dt == datetime(2026, 9, 15, 18, 0, 0, tzinfo=KST)


def test_parse_sunday_fallback():
    # Term starts on Monday, 2026-09-07 (Week 1)
    term_start = datetime(2026, 9, 7, 0, 0, 0, tzinfo=KST)

    # Week 1 Sunday should be 2026-09-13 23:59:59
    dt, fb = parse_lms_date("unparseable date string", fallback_week=1, term_start_date=term_start)
    assert fb is True
    assert dt == datetime(2026, 9, 13, 23, 59, 59, tzinfo=KST)

    # Week 3 Sunday should be 2026-09-27 23:59:59
    dt, fb = parse_lms_date("", fallback_week=3, term_start_date=term_start)
    assert fb is True
    assert dt == datetime(2026, 9, 27, 23, 59, 59, tzinfo=KST)

    # If no fallback info is given, returns (None, False)
    dt, fb = parse_lms_date("invalid")
    assert dt is None
    assert fb is False


def test_is_past_deadline():
    due = datetime(2026, 9, 20, 23, 59, 0, tzinfo=KST)

    # Earlier reference time -> not past deadline
    assert not is_past_deadline(due, now=datetime(2026, 9, 20, 12, 0, 0, tzinfo=KST))

    # Later reference time -> past deadline
    assert is_past_deadline(due, now=datetime(2026, 9, 21, 0, 0, 0, tzinfo=KST))

    # None due date -> returns False
    assert not is_past_deadline(None)


def test_parse_moodle_long_form_korean():
    dt, fb = parse_lms_date("화요일, 6 10월 2026, 1:00 PM")
    assert not fb
    assert dt == datetime(2026, 10, 6, 13, 0, 0, tzinfo=KST)

    dt, fb = parse_lms_date("월요일, 14 9월 2026, 3:20 PM")
    assert not fb
    assert dt == datetime(2026, 9, 14, 15, 20, 0, tzinfo=KST)

    dt, fb = parse_lms_date("6 10월 2026, 23:59")
    assert not fb
    assert dt == datetime(2026, 10, 6, 23, 59, 0, tzinfo=KST)


def test_parse_moodle_long_form_english():
    dt, fb = parse_lms_date("Tuesday, 6 October 2026, 1:00 PM")
    assert not fb
    assert dt == datetime(2026, 10, 6, 13, 0, 0, tzinfo=KST)

    dt, fb = parse_lms_date("Fri, 25 Sep 2026, 11:30 AM")
    assert not fb
    assert dt == datetime(2026, 9, 25, 11, 30, 0, tzinfo=KST)


def test_parse_korean_am_pm():
    dt, fb = parse_lms_date("2026년 10월 6일 (화) 오후 1:00")
    assert not fb
    assert dt == datetime(2026, 10, 6, 13, 0, 0, tzinfo=KST)

    dt, fb = parse_lms_date("2026년 10월 6일 화요일 오전 9:05")
    assert not fb
    assert dt == datetime(2026, 10, 6, 9, 5, 0, tzinfo=KST)


def test_parse_twelve_hour_edges():
    dt, fb = parse_lms_date("일요일, 4 10월 2026, 12:00 AM")
    assert not fb
    assert dt == datetime(2026, 10, 4, 0, 0, 0, tzinfo=KST)

    dt, fb = parse_lms_date("목요일, 1 10월 2026, 12:30 PM")
    assert not fb
    assert dt == datetime(2026, 10, 1, 12, 30, 0, tzinfo=KST)

