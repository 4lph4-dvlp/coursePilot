"""Domain models and versioned JSON contract (schema_version: 1) for course boards."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal[1] = 1


class BoardType(str, Enum):
    """Classification of bulletin boards within an LXP course."""

    NOTICE = "notice"
    QNA = "qna"
    OTHER = "other"
    CUSTOM = "custom"


class BoardModuleInfo(BaseModel):
    """Metadata for a board module discovered on a course homepage."""

    model_config = ConfigDict(extra="forbid")

    module_id: str
    title: str
    url: str
    board_type: BoardType


class BoardAttachmentItem(BaseModel):
    """An attached file associated with a board post or article."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    download_url: str
    filesize: int = 0
    saved_path: str | None = None


class BoardReplyItem(BaseModel):
    """An official reply or comment to a board post."""

    model_config = ConfigDict(extra="forbid")

    author: str
    created_at: str
    content: str


class BoardPostItem(BaseModel):
    """Represents a single post/article item in a course bulletin board."""

    model_config = ConfigDict(extra="forbid")

    post_id: str
    bwid: str | None = None
    board_id: str
    board_type: BoardType
    title: str
    author: str
    created_at: str
    hit_count: int = 0
    url: str
    is_read: bool = False
    is_my_question: bool = False
    is_answered: bool | None = None
    is_secret: bool = False
    summary_preview: str = ""
    content: str | None = None
    attachments: list[BoardAttachmentItem] = Field(default_factory=list)
    replies: list[BoardReplyItem] = Field(default_factory=list)


class CourseBoardGroup(BaseModel):
    """Group of board posts for a specific course."""

    model_config = ConfigDict(extra="forbid")

    course_id: str
    course_name: str
    course_abbr: str
    notices: list[BoardPostItem] = Field(default_factory=list)
    qna: list[BoardPostItem] = Field(default_factory=list)


class BoardSummary(BaseModel):
    """Aggregate summary statistics across courses."""

    model_config = ConfigDict(extra="forbid")

    total_courses: int
    total_notices: int
    unread_notices: int
    total_questions: int
    unanswered_questions: int
    my_questions: int


class BoardReport(BaseModel):
    """Versioned JSON contract (schema_version: 1) for board command output."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    command: Literal["board", "notices", "qna"] = "board"
    generated_at: datetime
    summary: BoardSummary
    courses: list[CourseBoardGroup] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)


class BoardArticleDetail(BaseModel):
    """Detailed content, attachments, and replies parsed from article.php."""

    model_config = ConfigDict(extra="forbid")

    subject: str
    author: str
    created_at: str
    hit_count: int = 0
    content: str
    attachments: list[BoardAttachmentItem] = Field(default_factory=list)
    replies: list[BoardReplyItem] = Field(default_factory=list)
