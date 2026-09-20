"""Tests for course mapping module (CONF-02)."""

import json
import logging
from pathlib import Path
from kau_assistant.course_mapping import (
    DEFAULT_MAPPINGS,
    get_abbreviation,
    load_course_mappings,
)


def test_normal_mapping():
    """Verify known course names map to their abbreviations."""
    mappings = {"공학수학2": "공수2", "자료구조": "자구"}
    assert get_abbreviation("공학수학2", mappings) == "공수2"
    assert get_abbreviation("자료구조", mappings) == "자구"


def test_whitespace_handling():
    """Verify course names with leading or trailing whitespace are properly trimmed and matched."""
    mappings = {"자료구조": "자구"}
    assert get_abbreviation("  자료구조  ", mappings) == "자구"


def test_unregistered_course_fallback_and_logging(caplog):
    """Verify unregistered course returns original name and logs guidance."""
    mappings = {"공학수학2": "공수2"}
    with caplog.at_level(logging.INFO):
        result = get_abbreviation("우주항공공학개론", mappings)

    assert result == "우주항공공학개론"
    assert "신규 과목 '우주항공공학개론' 발견" in caplog.text
    assert "config/course_mappings.json" in caplog.text


def test_load_existing_mapping_file(tmp_path: Path):
    """Verify load_course_mappings loads JSON correctly."""
    mapping_file = tmp_path / "course_mappings.json"
    data = {"신호및시스템": "신시", "운영체제": "운체"}
    mapping_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    loaded = load_course_mappings(mapping_file)
    assert loaded == data


def test_load_missing_file_fallback(tmp_path: Path, caplog):
    """Verify missing file logs warning and returns DEFAULT_MAPPINGS."""
    missing_file = tmp_path / "non_existent.json"
    with caplog.at_level(logging.WARNING):
        loaded = load_course_mappings(missing_file)

    assert loaded == DEFAULT_MAPPINGS
    assert "찾을 수 없습니다" in caplog.text


def test_load_corrupted_json_fallback(tmp_path: Path, caplog):
    """Verify corrupted JSON logs warning and returns DEFAULT_MAPPINGS."""
    corrupted_file = tmp_path / "bad.json"
    corrupted_file.write_text("{broken json", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        loaded = load_course_mappings(corrupted_file)

    assert loaded == DEFAULT_MAPPINGS
    assert "오류 발생" in caplog.text


def test_load_non_dict_json_fallback(tmp_path: Path, caplog):
    """Verify non-dict JSON (e.g. list) logs warning and returns DEFAULT_MAPPINGS."""
    list_file = tmp_path / "list.json"
    list_file.write_text(json.dumps(["item1", "item2"]), encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        loaded = load_course_mappings(list_file)

    assert loaded == DEFAULT_MAPPINGS
    assert "형식이 올바르지 않습니다" in caplog.text
