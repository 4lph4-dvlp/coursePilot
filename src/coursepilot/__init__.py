"""CoursePilot package root."""

from coursepilot.exceptions import (
    AuthenticationError,
    ConfigError,
    CoursePilotError,
    NavigationTimeoutError,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "CoursePilotError",
    "ConfigError",
    "AuthenticationError",
    "NavigationTimeoutError",
]
