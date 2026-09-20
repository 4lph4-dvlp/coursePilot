"""KAU LXP Assistant package root."""

from kau_assistant.exceptions import (
    AuthenticationError,
    ConfigError,
    KauAssistantError,
    NavigationTimeoutError,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "KauAssistantError",
    "ConfigError",
    "AuthenticationError",
    "NavigationTimeoutError",
]
