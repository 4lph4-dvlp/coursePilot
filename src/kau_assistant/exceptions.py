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
