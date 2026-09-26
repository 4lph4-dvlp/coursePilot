"""Compatibility namespace for CoursePilot's former Python package name."""

import importlib
from importlib.abc import Loader, MetaPathFinder
from importlib.util import find_spec, spec_from_loader
import sys

from coursepilot import (
    AuthenticationError,
    ConfigError,
    CoursePilotError,
    NavigationTimeoutError,
    __version__,
)

KauAssistantError = CoursePilotError


class _LegacyLoader(Loader):
    def __init__(self, target: str):
        self.target = target

    def create_module(self, spec):
        module = importlib.import_module(self.target)
        self.canonical_spec = module.__spec__
        return module

    def exec_module(self, module):
        # The canonical module is already executed. Never define duplicate enums,
        # exceptions, Pydantic models or settings singletons under the old name.
        # Import machinery assigns the alias spec before exec_module. Restore
        # the canonical one so reload(), resources and tooling keep working.
        module.__spec__ = self.canonical_spec


class _LegacyFinder(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith("kau_assistant.") or fullname == "kau_assistant.__main__":
            return None
        canonical = "coursepilot" + fullname[len("kau_assistant"):]
        canonical_spec = find_spec(canonical)
        if canonical_spec is None:
            return None
        return spec_from_loader(
            fullname, _LegacyLoader(canonical),
            is_package=canonical_spec.submodule_search_locations is not None,
        )


sys.meta_path.insert(0, _LegacyFinder())

__all__ = [
    "__version__", "KauAssistantError", "CoursePilotError", "ConfigError",
    "AuthenticationError", "NavigationTimeoutError",
]
