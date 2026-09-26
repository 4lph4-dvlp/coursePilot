"""Custom exception hierarchy for CoursePilot."""

class CoursePilotError(Exception):
    """Base exception for all CoursePilot errors."""
    pass


class ConfigError(CoursePilotError):
    """Raised when configuration is invalid or missing required values."""
    pass


class AuthenticationError(CoursePilotError):
    """Raised when LMS authentication fails or session cannot be validated."""
    pass


class NavigationTimeoutError(CoursePilotError):
    """Raised when page navigation times out even after retry."""
    pass


class CourseAccessDeniedError(CoursePilotError):
    """Raised when course access is denied or course is unavailable/restricted."""
    pass


class ActivityCollectionError(CoursePilotError):
    """Raised when supported course activities cannot be fully parsed."""
    pass


class UnsupportedLmsError(CoursePilotError):
    """Raised when LMS_URL does not serve a Coursemos/Moodle course list (unsupported platform or wrong address)."""
    pass


class NotionIntegrationError(CoursePilotError):
    """Base class for safe Notion integration failures."""


class NotionAuthenticationError(NotionIntegrationError):
    """Raised when the configured Notion credential is invalid."""


class NotionPermissionError(NotionIntegrationError):
    """Raised when the integration cannot access the configured target."""


class NotionTargetError(NotionIntegrationError):
    """Raised when the Scheduler target cannot be resolved uniquely."""


class NotionSchemaError(NotionIntegrationError):
    """Raised when the existing Scheduler schema is incompatible."""


class NotionTransportError(NotionIntegrationError):
    """Raised for bounded, safely reported Notion transport failures."""


class VodDownloadError(CoursePilotError):
    """Raised when VOD stream download, decryption, or assembly fails."""
