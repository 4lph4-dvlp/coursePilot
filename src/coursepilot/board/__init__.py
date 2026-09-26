"""Board domain package for Coursemos announcements and Q&A boards."""

from coursepilot.board.models import (
    SCHEMA_VERSION,
    BoardArticleDetail,
    BoardAttachmentItem,
    BoardModuleInfo,
    BoardPostItem,
    BoardReplyItem,
    BoardReport,
    BoardSummary,
    BoardType,
    CourseBoardGroup,
)

__all__ = [
    "SCHEMA_VERSION",
    "BoardArticleDetail",
    "BoardAttachmentItem",
    "BoardModuleInfo",
    "BoardPostItem",
    "BoardReplyItem",
    "BoardReport",
    "BoardSummary",
    "BoardType",
    "CourseBoardGroup",
]
