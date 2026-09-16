"""Feature flag definitions for shipping risky changes behind toggles.

Flags are environment-driven and default to OFF, so agents can land changes
without exposing behavior to every user at once. Evaluate flags with
:func:`is_enabled`; document every flag's purpose and removal plan here.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Final

from .observability import get_logger

#: All known flags with their defaults and purpose. Keep this table complete:
#: a flag missing here cannot be evaluated safely.
FLAG_DEFAULTS: Final[dict[str, bool]] = {
    # Enables the optional anonymous tool-usage events (product analytics).
    "shlink.analytics.enabled": False,
    # Marks a short URL with a deletion plan before removing it (soft delete).
    "shlink.soft_delete.enabled": False,
    # Adds a small delay+retry window for Shlink 5xx responses in the client.
    "shlink.retry_5xx.enabled": False,
}

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_PREFIX = "FLAG_"


@lru_cache(maxsize=None)
def _resolved_flags() -> dict[str, bool]:
    """Resolve every known flag once per process from the environment."""
    resolved = dict(FLAG_DEFAULTS)
    for flag_name, default in FLAG_DEFAULTS.items():
        env_name = _PREFIX + flag_name.replace(".", "_").replace("-", "_").upper()
        raw = os.environ.get(env_name)
        if raw is None or raw.strip() == "":
            resolved[flag_name] = default
            continue
        resolved[flag_name] = raw.strip().lower() in _TRUE_VALUES
    return resolved


def is_enabled(flag_name: str) -> bool:
    """Return whether ``flag_name`` is enabled.

    Unknown flags resolve to ``False`` and log a warning once, so typos fail
    safe instead of silently changing behavior.
    """
    flags = _resolved_flags()
    if flag_name not in FLAG_DEFAULTS:
        get_logger().warning("feature_flag.unknown", flag=flag_name)
        return False
    return flags[flag_name]


def set_flag_for_tests(flag_name: str, enabled: bool) -> None:
    """Override a flag in the current process (tests and local tooling only)."""
    if flag_name not in FLAG_DEFAULTS:
        raise KeyError(f"unknown flag: {flag_name}")
    _resolved_flags()[flag_name] = enabled


def reset_flags() -> None:
    """Re-resolve flags from the environment (used by tests)."""
    _resolved_flags.cache_clear()


def all_flags() -> dict[str, bool]:
    """Return a snapshot of every flag and its current value."""
    return dict(_resolved_flags())
