"""Custom exception hierarchy for KAU LXP Assistant."""

class KauAssistantError(Exception):
    """Base exception for all KAU Assistant errors."""
    pass


class ConfigError(KauAssistantError):
    """Raised when configuration is invalid or missing required values."""
    pass


class AuthenticationError(KauAssistantError):
    """Raised when LMS authentication fails or session cannot be validated."""
    pass


class NavigationTimeoutError(KauAssistantError):
    """Raised when page navigation times out even after retry."""
    pass


class CourseAccessDeniedError(KauAssistantError):
    """Raised when course access is denied or course is unavailable/restricted."""
    pass


class NotionIntegrationError(KauAssistantError):
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
