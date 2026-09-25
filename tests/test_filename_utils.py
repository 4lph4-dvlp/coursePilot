"""Unit tests for filename_utils module."""

from kau_assistant.materials.filename_utils import resolve_filename, sanitize_filename


def test_resolve_filename_rfc5987_utf8():
    header = "attachment; filename*=UTF-8''%EC%8B%A4%ED%97%98%EA%B5%90%EC%9E%AC.pdf"
    url = "https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001"
    resolved = resolve_filename(header, url, "기본자료")
    assert resolved == "실험교재.pdf"


def test_resolve_filename_standard_quoted():
    header = 'attachment; filename="lecture_01.pptx"'
    url = "https://lxp.kau.ac.kr/mod/resource/view.php?id=8002"
    resolved = resolve_filename(header, url, "기본자료")
    assert resolved == "lecture_01.pptx"


def test_resolve_filename_url_fallback():
    url = "https://lxp.kau.ac.kr/pluginfile.php/123/mod_ubfile/content/1/syllabus.pdf"
    resolved = resolve_filename(None, url, "기본자료")
    assert resolved == "syllabus.pdf"


def test_resolve_filename_url_encoded_path():
    url = "https://lxp.kau.ac.kr/pluginfile.php/123/mod_ubfile/content/1/%EC%8B%A4%ED%97%98.pdf"
    resolved = resolve_filename(None, url, "기본자료")
    assert resolved == "실험.pdf"


def test_resolve_filename_php_url_ignored():
    url = "https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001"
    resolved = resolve_filename(None, url, "강의자료", content_type="application/pdf")
    assert resolved == "강의자료.pdf"


def test_resolve_filename_mime_types():
    url = "https://lxp.kau.ac.kr/view.php"
    assert resolve_filename(None, url, "자료", content_type="application/x-hwp") == "자료.hwp"
    assert resolve_filename(None, url, "자료", content_type="application/zip") == "자료.zip"
    assert resolve_filename(None, url, "자료.pdf", content_type="application/pdf") == "자료.pdf"
    assert resolve_filename(None, url, "자료", content_type="unknown/octet-stream") == "자료.bin"


def test_sanitize_filename_reserved_windows_stems():
    assert sanitize_filename("CON.pdf") == "_CON.pdf"
    assert sanitize_filename("aux.hwp") == "_aux.hwp"
    assert sanitize_filename("com1.txt") == "_com1.txt"
    assert sanitize_filename("prn.zip") == "_prn.zip"
    assert sanitize_filename("normal.pdf") == "normal.pdf"


def test_sanitize_filename_illegal_characters():
    assert sanitize_filename("W1: Intro / Overview?.pdf") == "W1_ Intro _ Overview_.pdf"
    assert sanitize_filename('test<bad>"quote"|pipe*star.hwp') == "test_bad_quote_pipe_star.hwp"


def test_sanitize_filename_trailing_dots_and_spaces():
    assert sanitize_filename("sample.pdf. ") == "sample.pdf"
    assert sanitize_filename("   spaced_name.pdf   ") == "spaced_name.pdf"


def test_sanitize_filename_truncation_preserves_extension():
    long_name = "a" * 300 + ".pdf"
    sanitized = sanitize_filename(long_name, max_length=100)
    assert len(sanitized) == 100
    assert sanitized.endswith(".pdf")
    assert sanitized.startswith("a")


def test_sanitize_filename_empty_fallback():
    assert sanitize_filename("") == "downloaded_file"
    assert sanitize_filename("???") == "downloaded_file"
