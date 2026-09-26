from datetime import datetime, timedelta, timezone
import re

try:
    from zoneinfo import ZoneInfo
    try:
        KST = ZoneInfo("Asia/Seoul")
    except Exception:
        KST = timezone(timedelta(hours=9), name="KST")
except ImportError:
    KST = timezone(timedelta(hours=9), name="KST")


def get_current_kst_time() -> datetime:
    """Returns the current datetime in Asia/Seoul timezone."""
    return datetime.now(KST)


def parse_lms_date(
    date_str: str,
    fallback_week: int | None = None,
    term_start_date: datetime | None = None,
) -> tuple[datetime | None, bool]:
    """Parses various LMS date-time formats into a KST datetime object.

    If parsing succeeds, returns (datetime, False).
    If all patterns fail and fallback_week + term_start_date are provided,
    returns (sunday_fallback_datetime, True).
    Otherwise returns (None, False).

    Supports:
        - '2026-09-25 23:59:00', '2026.09.25 (금) 23:59', '2026/09/25 23:59'
        - '2026년 9월 25일 23:59', '2026년 09월 25일 (금) 23:59'
        - Korean format with weekday and AM/PM: '2026년 10월 6일 (화) 오후 1:00', '2026년 10월 6일 화요일 오전 9:05'
        - Range dates: '2026-09-01 00:00 ~ 2026-09-07 23:59' (takes the end date)
        - '~ 09-07 23:59', '9월 25일 23:59'
        - Moodle long-form: '화요일, 6 10월 2026, 1:00 PM', 'Tuesday, 6 October 2026, 1:00 PM'
    """
    if not date_str:
        return _apply_fallback(fallback_week, term_start_date)

    text = date_str.strip()

    # If date is given as a range separated by '~', take the due date (end part)
    if "~" in text:
        parts = text.split("~")
        if len(parts) >= 2 and parts[1].strip():
            text = parts[1].strip()

    # Clean out day-of-week strings in parentheses e.g. (금), (월), [금]
    cleaned = re.sub(r"[\(\[]\s*[월화수목금토일]\s*[\)\]]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    current_year = datetime.now(KST).year

    # Pattern 1: YYYY[-./]MM[-./]DD HH:MM(:SS)?
    m1 = re.search(
        r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
        cleaned,
    )
    if m1:
        y, m, d, hh, mm, ss = m1.groups()
        dt = datetime(
            int(y),
            int(m),
            int(d),
            int(hh),
            int(mm),
            int(ss or 0),
            tzinfo=KST,
        )
        return dt, False

    # Pattern 2: YYYY년 M월 D일 [weekday] [AM/PM/오전/오후] HH:MM(:SS)? [AM/PM/오전/오후]
    m2 = re.search(
        r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일(?:\s*[월화수목금토일]요일)?\s*(?:(오전|오후|AM|PM)\s*)?(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?(?:\s*(오전|오후|AM|PM))?",
        cleaned,
        re.IGNORECASE,
    )
    if m2:
        y, m, d, am_pm1, hh, mm, ss, am_pm2 = m2.groups()
        am_pm = am_pm1 or am_pm2
        hour = _adjust_12_hour(int(hh), am_pm)
        dt = datetime(
            int(y),
            int(m),
            int(d),
            hour,
            int(mm),
            int(ss or 0),
            tzinfo=KST,
        )
        return dt, False

    # Pattern 3: M월 D일 HH:MM(:SS)?
    m3 = re.search(
        r"(\d{1,2})\s*월\s*(\d{1,2})\s*일\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
        cleaned,
    )
    if m3:
        m, d, hh, mm, ss = m3.groups()
        dt = datetime(
            current_year,
            int(m),
            int(d),
            int(hh),
            int(mm),
            int(ss or 0),
            tzinfo=KST,
        )
        return dt, False

    # Pattern 4: MM[-./]DD HH:MM(:SS)?
    m4 = re.search(
        r"(\d{1,2})[-./](\d{1,2})\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
        cleaned,
    )
    if m4:
        m, d, hh, mm, ss = m4.groups()
        dt = datetime(
            current_year,
            int(m),
            int(d),
            int(hh),
            int(mm),
            int(ss or 0),
            tzinfo=KST,
        )
        return dt, False

    # Pattern 5: Moodle long-form [Weekday[,]] D M월|Month YYYY[,] [AM/PM/오전/오후] H:MM[:SS] [AM/PM/오전/오후]
    m5 = re.search(
        r"(?:(?:[월화수목금토일]요일|[A-Za-z]+)\s*,?\s*)?"
        r"(\d{1,2})\s+"
        r"(?:(\d{1,2})\s*월|([a-zA-Z]+))\s+"
        r"(\d{4})\s*,?\s*"
        r"(?:(오전|오후|AM|PM)\s+)?(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?(?:\s*(오전|오후|AM|PM))?",
        cleaned,
        re.IGNORECASE,
    )
    if m5:
        d, m_num, m_str, y, am_pm1, hh, mm, ss, am_pm2 = m5.groups()
        if m_num:
            month = int(m_num)
        elif m_str and m_str.lower() in _ENGLISH_MONTHS:
            month = _ENGLISH_MONTHS[m_str.lower()]
        else:
            month = None

        if month is not None:
            am_pm = am_pm1 or am_pm2
            hour = _adjust_12_hour(int(hh), am_pm)
            dt = datetime(
                int(y),
                month,
                int(d),
                hour,
                int(mm),
                int(ss or 0),
                tzinfo=KST,
            )
            return dt, False

    # All direct patterns failed -> attempt fallback
    return _apply_fallback(fallback_week, term_start_date)


_ENGLISH_MONTHS: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _adjust_12_hour(hour: int, am_pm: str | None) -> int:
    """Adjust hour according to 12-hour AM/PM rules."""
    if not am_pm:
        return hour
    marker = am_pm.strip().upper()
    if marker in ("PM", "오후"):
        if hour < 12:
            return hour + 12
        return hour  # 12 PM remains 12
    elif marker in ("AM", "오전"):
        if hour == 12:
            return 0
        return hour
    return hour


def _apply_fallback(
    fallback_week: int | None,
    term_start_date: datetime | None,
) -> tuple[datetime | None, bool]:
    """Calculates fallback deadline as Sunday 23:59:59 KST of the given week."""
    if fallback_week is not None and term_start_date is not None:
        # term_start_date is assumed to be the Monday (or start) of Week 1
        # Target week starts at term_start_date + (fallback_week - 1) weeks
        week_start = term_start_date + timedelta(weeks=fallback_week - 1)
        # Find the Sunday of that week (assuming Monday is weekday 0, Sunday is weekday 6)
        days_to_sunday = 6 - week_start.weekday()
        if days_to_sunday < 0:
            days_to_sunday += 7
        sunday = week_start + timedelta(days=days_to_sunday)
        fallback_dt = datetime(
            sunday.year,
            sunday.month,
            sunday.day,
            23,
            59,
            59,
            tzinfo=KST,
        )
        return fallback_dt, True

    return None, False


def is_past_deadline(due_date: datetime | None, now: datetime | None = None) -> bool:
    """Returns True if due_date is set and strictly in the past relative to now (default: current KST)."""
    if due_date is None:
        return False

    current_time = now if now is not None else get_current_kst_time()
    # Normalize comparison to have matching timezone
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=KST)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=KST)

    return current_time > due_date
