"""Course name abbreviation mapping loader and fallback engine (CONF-02)."""

import json
import logging
from pathlib import Path

from coursepilot.config import PROJECT_ROOT

logger = logging.getLogger("coursepilot.course_mapping")

DEFAULT_MAPPINGS: dict[str, str] = {
    "공학수학2": "공수2",
    "공학수학II": "공수2",
    "자료구조": "자구",
    "자료구조및실습": "자구",
    "디지털시스템설계": "디시설",
    "확률및랜덤변수": "확랜",
    "기초전자실험": "기전실",
    "항공우주산업개론": "항산개",
    "항공산업우주개론": "항산개",
}


def load_course_mappings(path: Path | str | None = None) -> dict[str, str]:
    """Load course name to abbreviation mapping from a JSON file.

    Falls back to default mappings gracefully if the file is missing or invalid.
    """
    file_path = Path(path) if path is not None else PROJECT_ROOT / "config/course_mappings.json"
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path
    if not file_path.exists():
        logger.warning(f"과목 매핑 파일({file_path})을 찾을 수 없습니다. 기본 매핑을 사용합니다.")
        return DEFAULT_MAPPINGS.copy()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            logger.warning(f"매핑 파일({file_path}) 형식이 올바르지 않습니다 (dict 필요). 기본 매핑을 사용합니다.")
            return DEFAULT_MAPPINGS.copy()
    except Exception as e:
        logger.warning(f"매핑 파일({file_path}) 로드 중 오류 발생: {e}. 기본 매핑을 사용합니다.")
        return DEFAULT_MAPPINGS.copy()


def get_abbreviation(course_name: str, mappings: dict[str, str]) -> str:
    """Retrieve the abbreviated course name from mappings.

    If not found, returns the original stripped course name and logs a helpful guidance message.
    """
    clean_name = course_name.strip()
    if clean_name in mappings:
        return mappings[clean_name]

    logger.info(
        f"신규 과목 '{clean_name}' 발견: 축약어가 등록되어 있지 않아 원본 이름을 유지합니다. "
        "원하는 경우 'config/course_mappings.json'에 약칭을 등록하여 주십시오."
    )
    return clean_name
