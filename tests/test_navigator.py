from unittest.mock import MagicMock, patch
import pytest

from kau_assistant.config import Settings
from kau_assistant.exceptions import CourseAccessDeniedError
from kau_assistant.scraper.models import CourseItem
from kau_assistant.scraper.navigator import CourseNavigator


@pytest.fixture
def settings():
    return Settings(
        lms_url="https://canvas.kau.ac.kr",
        timeout_ms=5000,
    )


@pytest.fixture
def course():
    return CourseItem(
        course_id="10101",
        raw_name="공학수학2(01분반) [2026-1학기]",
        clean_name="공학수학2",
        url="https://canvas.kau.ac.kr/course/view.php?id=10101",
    )


def test_polite_delay(settings):
    navigator = CourseNavigator(settings, min_delay=0.01, max_delay=0.02)
    with patch("time.sleep") as mock_sleep:
        navigator.polite_delay()
        mock_sleep.assert_called_once()
        delay_arg = mock_sleep.call_args[0][0]
        assert 0.01 <= delay_arg <= 0.02


def test_navigate_to_course_success(settings, course):
    navigator = CourseNavigator(settings, min_delay=0, max_delay=0)
    mock_page = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<div id='course-content'>Course Normal Content</div>"
    mock_page.wait_for_selector.side_effect = Exception("Not found")

    html = navigator.navigate_to_course(mock_page, course)
    assert "Course Normal Content" in html
    mock_page.goto.assert_called_once_with(course.url, wait_until="domcontentloaded")


def test_navigate_to_course_http_403_raises_access_denied(settings, course):
    navigator = CourseNavigator(settings, min_delay=0, max_delay=0)
    mock_page = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 403
    mock_page.goto.return_value = mock_response

    with pytest.raises(CourseAccessDeniedError, match="HTTP 403 access denied"):
        navigator.navigate_to_course(mock_page, course)


def test_navigate_to_course_restricted_content_raises_access_denied(settings, course):
    navigator = CourseNavigator(settings, min_delay=0, max_delay=0)
    mock_page = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<div class='alert-danger'>접근 권한이 없습니다. 관리자에게 문의하세요.</div>"

    with pytest.raises(CourseAccessDeniedError, match="Access denied or course restricted"):
        navigator.navigate_to_course(mock_page, course)


def test_navigate_progress_page_success(settings, course):
    navigator = CourseNavigator(settings, min_delay=0, max_delay=0)
    mock_page = MagicMock()
    mock_page.content.return_value = "<table class='generaltable progress-report'><tr><td>학습현황</td></tr></table>"
    mock_page.wait_for_selector.return_value = True

    html = navigator.navigate_progress_page(mock_page, course)
    assert html is not None
    assert "progress-report" in html
    mock_page.goto.assert_called_once_with(
        "https://canvas.kau.ac.kr/report/ubcompletion/progress.php?id=10101",
        wait_until="domcontentloaded",
    )


def test_navigate_progress_page_accepts_user_progress_table(settings, course):
    navigator = CourseNavigator(settings, min_delay=0, max_delay=0)
    mock_page = MagicMock()
    mock_page.content.return_value = "<table class='user_progress generaltable'><tr><td>출석인정 요구시간</td></tr></table>"
    mock_page.wait_for_selector.return_value = True

    html = navigator.navigate_progress_page(mock_page, course)
    assert html is not None
    assert "user_progress" in html


def test_navigate_progress_page_fallback_to_none(settings, course):
    navigator = CourseNavigator(settings, min_delay=0, max_delay=0)
    mock_page = MagicMock()
    mock_page.content.return_value = "<div id='page-error'>페이지를 찾을 수 없습니다.</div>"
    mock_page.wait_for_selector.side_effect = Exception("Selector timeout")

    html = navigator.navigate_progress_page(mock_page, course)
    assert html is None


def test_navigate_assessment_page_success(settings, course):
    navigator = CourseNavigator(settings, min_delay=0, max_delay=0)
    mock_page = MagicMock()
    mock_page.content.return_value = "<table class='generaltable'><tr><td>과제 1</td></tr></table>"
    mock_page.wait_for_selector.return_value = True

    html = navigator.navigate_assessment_page(mock_page, course, item_type="assign")
    assert html is not None
    assert "과제 1" in html
    mock_page.goto.assert_called_once_with(
        "https://canvas.kau.ac.kr/mod/assign/index.php?id=10101",
        wait_until="domcontentloaded",
    )
