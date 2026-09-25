"""Board collection pipeline and single article viewer orchestrator."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal
import httpx

from kau_assistant.board.models import (
    BoardArticleDetail,
    BoardAttachmentItem,
    BoardPostItem,
    BoardReport,
    BoardSummary,
    BoardType,
    CourseBoardGroup,
)
from kau_assistant.board.read_state import BoardReadStateManager
from kau_assistant.board.text_converter import extract_summary_preview
from kau_assistant.config import Settings, get_settings
from kau_assistant.course_mapping import load_course_mappings
from kau_assistant.materials.downloader import (
    download_material_file,
    get_authenticated_httpx_client,
)
from kau_assistant.materials.models import MaterialItem
from kau_assistant.player.runner import find_target_course
from kau_assistant.scraper.board_parser import (
    extract_board_modules,
    parse_board_article_page,
    parse_board_list_page,
)
from kau_assistant.scraper.course_list import extract_courses
from kau_assistant.session_manager import SessionManager

logger = logging.getLogger(__name__)


def run_board_pipeline(
    course_query: str | None = None,
    command_scope: Literal["board", "notices", "qna"] = "board",
    limit: int | None = 3,
    fetch_all: bool = False,
    detail: bool = False,
    unread_only: bool = False,
    unanswered: bool = False,
    my_only: bool = False,
    board_name: str | None = None,
    mark_read: bool = False,
    relogin: bool = False,
    headful: bool = False,
    settings: Settings | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> BoardReport:
    """Orchestrates bulletin board collection across courses with error isolation and filters."""
    cfg = settings or get_settings()

    if relogin and cfg.session_cache_path.exists():
        try:
            cfg.session_cache_path.unlink()
        except Exception:
            pass

    read_state_path = cfg.session_cache_path.parent / "board_read_state.json"
    read_state_mgr = BoardReadStateManager(state_file_path=read_state_path)

    client = get_authenticated_httpx_client(cfg)
    course_groups: list[CourseBoardGroup] = []
    errors: list[dict] = []

    try:
        with SessionManager(settings=cfg, headful=headful) as sm:
            page = sm.get_authenticated_page()
            courses = extract_courses(page, cfg.lms_url)

            # Detect current LMS user name for [내 질문] detection
            current_user_name = ""
            try:
                user_el = page.locator(".usermenu .usertext, .user-name, .myinfo").first
                if user_el.count() > 0:
                    current_user_name = (user_el.text_content() or "").strip()
            except Exception:
                current_user_name = ""

            if course_query:
                mappings = load_course_mappings(cfg.course_mappings_path)
                target_course = find_target_course(courses, course_query, mappings)
                if not target_course:
                    raise ValueError(f"과목 검색어와 일치하는 강좌를 찾을 수 없습니다: '{course_query}'")
                target_courses = [target_course]
            else:
                target_courses = courses

            for course in target_courses:
                if progress_callback:
                    progress_callback(f"[{course.clean_name}] 게시판 확인 중...")

                try:
                    # 1. Fetch course home
                    home_resp = client.get(course.url)
                    home_resp.raise_for_status()
                    all_modules = extract_board_modules(home_resp.text, course.url)

                    # 2. Filter modules by name and scope
                    modules = all_modules
                    if board_name:
                        modules = [m for m in modules if board_name.lower() in m.title.lower()]

                    if command_scope == "notices":
                        modules = [
                            m
                            for m in modules
                            if m.board_type == BoardType.NOTICE
                            or (board_name and m.board_type == BoardType.CUSTOM)
                        ]
                    elif command_scope == "qna":
                        modules = [
                            m
                            for m in modules
                            if m.board_type == BoardType.QNA
                            or (board_name and m.board_type == BoardType.CUSTOM)
                        ]

                    course_notices: list[BoardPostItem] = []
                    course_qna: list[BoardPostItem] = []

                    # 3. For each board module, fetch view.php
                    for mod in modules:
                        list_resp = client.get(mod.url)
                        list_resp.raise_for_status()

                        posts = parse_board_list_page(
                            list_resp.text,
                            mod.url,
                            board_id=mod.module_id,
                            board_type=mod.board_type,
                            current_user_name=current_user_name,
                        )

                        # Attach is_read from local state
                        for p in posts:
                            p.is_read = read_state_mgr.is_read(course.course_id, p.post_id)

                        # Apply filters
                        if unread_only:
                            posts = [p for p in posts if not p.is_read]

                        if unanswered:
                            posts = [
                                p
                                for p in posts
                                if p.board_type != BoardType.QNA or p.is_answered is False
                            ]

                        if my_only:
                            posts = [
                                p
                                for p in posts
                                if p.board_type != BoardType.QNA or p.is_my_question
                            ]

                        # Apply limit
                        if not fetch_all and limit is not None:
                            posts = posts[:limit]

                        # Detail / article content fetch on demand (D-15-16)
                        if detail:
                            for p in posts:
                                if p.url:
                                    try:
                                        art_resp = client.get(p.url)
                                        art_resp.raise_for_status()
                                        detail_item = parse_board_article_page(
                                            art_resp.text, p.url
                                        )
                                        p.content = detail_item.content
                                        p.attachments = detail_item.attachments
                                        p.replies = detail_item.replies
                                        p.summary_preview = extract_summary_preview(
                                            detail_item.content
                                        )
                                        # Auto mark read when detail is fetched (D-15-15)
                                        read_state_mgr.mark_as_read(course.course_id, [p.post_id])
                                        p.is_read = True
                                    except Exception as ex:
                                        logger.debug(
                                            f"Failed to fetch detail for post {p.post_id}: {ex}"
                                        )

                        # Batch mark read if requested
                        if mark_read and posts:
                            read_state_mgr.mark_as_read(
                                course.course_id, [p.post_id for p in posts]
                            )
                            for p in posts:
                                p.is_read = True

                        # Split into notices vs qna
                        if mod.board_type == BoardType.NOTICE:
                            course_notices.extend(posts)
                        elif mod.board_type == BoardType.QNA:
                            course_qna.extend(posts)
                        else:
                            if command_scope == "qna":
                                course_qna.extend(posts)
                            else:
                                course_notices.extend(posts)

                    course_groups.append(
                        CourseBoardGroup(
                            course_id=course.course_id,
                            course_name=course.clean_name,
                            course_abbr=getattr(course, "raw_name", course.clean_name),
                            notices=course_notices,
                            qna=course_qna,
                        )
                    )

                except Exception as e:
                    logger.warning(f"Error fetching boards for course {course.clean_name}: {e}")
                    errors.append(
                        {
                            "course_id": course.course_id,
                            "course_name": course.clean_name,
                            "error": str(e),
                        }
                    )
    finally:
        client.close()

    total_courses = len(target_courses) if course_query else len(course_groups) + len(errors)
    total_notices = sum(len(g.notices) for g in course_groups)
    unread_notices = sum(1 for g in course_groups for p in g.notices if not p.is_read)
    total_questions = sum(len(g.qna) for g in course_groups)
    unanswered_questions = sum(1 for g in course_groups for p in g.qna if p.is_answered is False)
    my_questions = sum(1 for g in course_groups for p in g.qna if p.is_my_question)

    summary = BoardSummary(
        total_courses=total_courses,
        total_notices=total_notices,
        unread_notices=unread_notices,
        total_questions=total_questions,
        unanswered_questions=unanswered_questions,
        my_questions=my_questions,
    )

    return BoardReport(
        schema_version=1,
        command=command_scope,
        generated_at=datetime.now(),
        summary=summary,
        courses=course_groups,
        errors=errors,
    )


def view_board_article(
    post_id_or_bwid: str,
    course_query: str | None = None,
    download_attachments: bool = False,
    output_dir: Path | str | None = None,
    relogin: bool = False,
    headful: bool = False,
    settings: Settings | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> BoardPostItem:
    """Fetches a single article detail, marks it as read, and optionally downloads attachments."""
    cfg = settings or get_settings()

    if relogin and cfg.session_cache_path.exists():
        try:
            cfg.session_cache_path.unlink()
        except Exception:
            pass

    read_state_path = cfg.session_cache_path.parent / "board_read_state.json"
    read_state_mgr = BoardReadStateManager(state_file_path=read_state_path)

    client = get_authenticated_httpx_client(cfg)

    try:
        with SessionManager(settings=cfg, headful=headful) as sm:
            page = sm.get_authenticated_page()
            courses = extract_courses(page, cfg.lms_url)

            if course_query:
                mappings = load_course_mappings(cfg.course_mappings_path)
                target_course = find_target_course(courses, course_query, mappings)
                if not target_course:
                    raise ValueError(f"과목 검색어와 일치하는 강좌를 찾을 수 없습니다: '{course_query}'")
                candidate_courses = [target_course]
            else:
                candidate_courses = courses

            target_post: BoardPostItem | None = None
            found_course = None

            # Search candidate courses for the target post
            for course in candidate_courses:
                if target_post:
                    break

                if progress_callback:
                    progress_callback(f"[{course.clean_name}] 게시글 검색 중...")

                try:
                    home_resp = client.get(course.url)
                    home_resp.raise_for_status()
                    modules = extract_board_modules(home_resp.text, course.url)

                    for mod in modules:
                        list_resp = client.get(mod.url)
                        list_resp.raise_for_status()
                        posts = parse_board_list_page(
                            list_resp.text,
                            mod.url,
                            board_id=mod.module_id,
                            board_type=mod.board_type,
                        )
                        for p in posts:
                            if p.post_id == str(post_id_or_bwid) or p.bwid == str(post_id_or_bwid):
                                target_post = p
                                found_course = course
                                break
                        if target_post:
                            break
                except Exception as e:
                    logger.debug(f"Failed searching course {course.clean_name}: {e}")

            if not target_post or not found_course:
                raise ValueError(f"게시글 ID 또는 번호 '{post_id_or_bwid}'를 찾을 수 없습니다.")

            # Fetch full article details
            if not target_post.url:
                raise ValueError(f"게시글 '{target_post.title}'의 열람 URL이 존재하지 않습니다 (비공개 글).")

            art_resp = client.get(target_post.url)
            art_resp.raise_for_status()
            detail = parse_board_article_page(art_resp.text, target_post.url)

            # Auto mark read upon viewing (D-15-15)
            read_state_mgr.mark_as_read(found_course.course_id, [target_post.post_id])
            target_post.is_read = True
            target_post.content = detail.content
            target_post.attachments = detail.attachments
            target_post.replies = detail.replies
            target_post.summary_preview = extract_summary_preview(detail.content)

            # Optional attachment download (D-15-08)
            if download_attachments and target_post.attachments:
                save_dir = (
                    Path(output_dir) if output_dir else cfg.download_dir
                ) / found_course.clean_name / "notices"
                save_dir.mkdir(parents=True, exist_ok=True)

                for att in target_post.attachments:
                    if progress_callback:
                        progress_callback(f"첨부파일 다운로드 중: {att.filename}")
                    try:
                        mat_item = MaterialItem(
                            course_id=found_course.course_id,
                            course_name=found_course.clean_name,
                            week_number=0,
                            module_id=target_post.board_id,
                            title=att.filename,
                            url=att.download_url,
                            download_url=att.download_url,
                            suggested_filename=att.filename,
                        )
                        saved_path, size, _ = download_material_file(client, mat_item, save_dir)
                        att.saved_path = str(saved_path)
                        att.filesize = size
                    except Exception as e:
                        logger.warning(f"Failed to download attachment {att.filename}: {e}")

            return target_post

    finally:
        client.close()
