"""Filename resolution (RFC 5987 / RFC 6266) and cross-platform sanitization utilities."""

import mimetypes
from pathlib import Path
import re
import urllib.parse

_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_MIME_FALLBACK_EXTENSIONS = {
    "application/x-hwp": ".hwp",
    "application/haansofthwp": ".hwp",
    "application/vnd.hancom.hwp": ".hwp",
    "application/vnd.hancom.hwpx": ".hwpx",
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


def resolve_filename(
    content_disposition: str | None,
    url: str,
    default_name: str,
    content_type: str | None = None,
) -> str:
    """Extracts a filename with RFC 5987 / 6266 priority, URL fallback, and MIME type inference."""
    if content_disposition:
        # Priority 1: RFC 5987 / RFC 6266 filename*=UTF-8''...
        m_star = re.search(
            r"filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)",
            content_disposition,
            re.I,
        )
        if m_star:
            raw_val = m_star.group(1).strip("\"' ")
            decoded = urllib.parse.unquote(raw_val)
            if decoded:
                return decoded

        # Priority 2: Standard filename="..."
        m_fn = re.search(r'filename\s*=\s*"?([^;"]+)"?', content_disposition, re.I)
        if m_fn:
            raw_val = m_fn.group(1).strip("\"' ")
            decoded = urllib.parse.unquote(raw_val)
            if decoded:
                return decoded

    # Priority 3: URL path basename (if it has an extension and does not end with .php)
    try:
        url_path = urllib.parse.urlsplit(url).path
        path_name = Path(url_path).name
        if path_name and "." in path_name and not path_name.lower().endswith(".php"):
            decoded_path_name = urllib.parse.unquote(path_name)
            if decoded_path_name:
                return decoded_path_name
    except Exception:
        pass

    # Priority 4: Default name with extension inferred from content_type
    ext: str | None = None
    if content_type:
        clean_mime = content_type.split(";")[0].strip().lower()
        ext = _MIME_FALLBACK_EXTENSIONS.get(clean_mime)
        if not ext:
            if "hwp" in clean_mime:
                ext = ".hwp"
            elif "hwpx" in clean_mime:
                ext = ".hwpx"
            elif "pdf" in clean_mime:
                ext = ".pdf"
            elif "zip" in clean_mime:
                ext = ".zip"
            else:
                ext = mimetypes.guess_extension(clean_mime)

    ext = ext or ".bin"
    if not default_name.lower().endswith(ext.lower()):
        return f"{default_name}{ext}"
    return default_name


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitizes filename removing illegal filesystem characters and Windows reserved stems."""
    if not filename:
        return "downloaded_file"

    # Replace illegal filesystem characters [<>:"/\\|?*\x00-\x1f] with _
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", filename)

    # Collapse consecutive whitespace into a single space
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Strip trailing dots and spaces
    cleaned = cleaned.rstrip(". ")

    if not cleaned or not cleaned.strip("_. "):
        return "downloaded_file"

    # Check for Windows reserved stems
    file_path = Path(cleaned)
    stem_upper = file_path.stem.upper()
    if stem_upper in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"

    # Truncate to max_length while preserving extension
    if len(cleaned) > max_length:
        suffix = Path(cleaned).suffix
        stem = Path(cleaned).stem
        available_stem_len = max_length - len(suffix)
        if available_stem_len > 0:
            cleaned = f"{stem[:available_stem_len]}{suffix}"
        else:
            cleaned = cleaned[:max_length]

    return cleaned or "downloaded_file"
