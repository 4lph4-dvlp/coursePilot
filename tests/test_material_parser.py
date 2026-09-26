"""Unit tests for material_parser module."""

from pathlib import Path
from coursepilot.scraper.material_parser import (
    extract_pluginfile_url,
    parse_materials_from_course_sections,
)
from coursepilot.scraper.models import CourseItem


def test_parse_materials_from_course_sections():
    fixture_path = Path(__file__).parent / "fixtures" / "lxp_course_materials.html"
    html = fixture_path.read_text(encoding="utf-8")

    course = CourseItem(
        course_id="12345",
        raw_name="자료구조 (001)",
        clean_name="자료구조",
        url="https://lxp.kau.ac.kr/course/view.php?id=12345",
    )

    materials = parse_materials_from_course_sections(html, course)

    # We expect 5 materials: 8000, 8001, 8002, 8003, 8004 (VOD 7001 excluded)
    assert len(materials) == 5

    # 1. Section 0 (OT)
    m0 = materials[0]
    assert m0.module_id == "8000"
    assert m0.week_number == 0
    assert m0.title == "강의계획서 및 오리엔테이션 자료"
    assert "학습자료" not in m0.title
    assert m0.is_completed is False
    assert m0.url == "https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8000"

    # 2. Section 1 (1주차 ubfile)
    m1 = materials[1]
    assert m1.module_id == "8001"
    assert m1.week_number == 1
    assert m1.title == "1주차 강의자료.pdf"
    assert m1.is_completed is False

    # 3. Section 1 (1주차 resource)
    m2 = materials[2]
    assert m2.module_id == "8002"
    assert m2.week_number == 1
    assert m2.title == "1주차 보충자료.zip"
    assert m2.is_completed is True

    # 4. Section 2 (2주차 ubfile complete with iscompleted)
    m3 = materials[3]
    assert m3.module_id == "8003"
    assert m3.week_number == 2
    assert m3.title == "2주차 실습자료.hwp"
    assert m3.is_completed is True

    # 5. Section 3 (3주차 ubfile)
    m4 = materials[4]
    assert m4.module_id == "8004"
    assert m4.week_number == 3
    assert m4.title == "3주차 과제안내.docx"
    assert m4.is_completed is False


def test_extract_pluginfile_url():
    base_url = "https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001"

    # 1. Anchor tag
    html_a = '<div><p>문서 다운로드: <a href="/pluginfile.php/123/mod_ubfile/content/1/doc.pdf">다운로드</a></p></div>'
    url_a = extract_pluginfile_url(html_a, base_url=base_url)
    assert url_a == "https://lxp.kau.ac.kr/pluginfile.php/123/mod_ubfile/content/1/doc.pdf"

    # 2. Object tag
    html_obj = '<div class="resourcecontent"><object data="/pluginfile.php/456/mod_resource/content/1/slides.pptx" type="application/pdf"></object></div>'
    url_obj = extract_pluginfile_url(html_obj, base_url=base_url)
    assert url_obj == "https://lxp.kau.ac.kr/pluginfile.php/456/mod_resource/content/1/slides.pptx"

    # 3. Iframe tag
    html_iframe = '<iframe src="https://lxp.kau.ac.kr/pluginfile.php/789/viewer.html"></iframe>'
    url_iframe = extract_pluginfile_url(html_iframe, base_url=base_url)
    assert url_iframe == "https://lxp.kau.ac.kr/pluginfile.php/789/viewer.html"

    # 4. Embed tag
    html_embed = '<embed src="/pluginfile.php/999/file.pdf" />'
    url_embed = extract_pluginfile_url(html_embed, base_url=base_url)
    assert url_embed == "https://lxp.kau.ac.kr/pluginfile.php/999/file.pdf"

    # 5. No pluginfile link
    html_none = '<div><p>내용이 없습니다.</p></div>'
    assert extract_pluginfile_url(html_none, base_url=base_url) is None
    assert extract_pluginfile_url("", base_url=base_url) is None
