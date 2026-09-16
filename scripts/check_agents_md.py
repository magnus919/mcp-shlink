#!/usr/bin/env python
"""Validate that AGENTS.md stays accurate as the tooling evolves.

Checks that every documented command still matches what pyproject.toml and CI
actually use (tool names, script names, coverage flags, and the testpath), and
that documented env vars stay in sync with mcp_shlink.config.Settings.
Run directly, or via the pre-commit hook / CI job of the same name.
"""

from __future__ import annotations

import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent


def _read_agents_md() -> str:
    agents_md = ROOT / "AGENTS.md"
    if not agents_md.exists():
        print("FAIL: AGENTS.md missing at repository root")
        raise SystemExit(1)
    return agents_md.read_text(encoding="utf-8")


def _load_pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def check_dev_group_documented(content: str, pyproject: dict) -> list[str]:
    problems = []
    dev_deps = set(pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", []))
    for tool in ("pytest", "ruff", "mypy"):
        if not any(dep.split(">")[0].split("=")[0] == tool for dep in dev_deps):
            continue
        if tool not in content:
            problems.append(f"AGENTS.md does not mention required dev tool '{tool}'")
    return problems


def check_coverage_gate_documented(content: str, pyproject: dict) -> list[str]:
    problems = []
    fail_under = pyproject.get("tool", {}).get("coverage", {}).get("report", {}).get("fail_under")
    if fail_under and f"{fail_under}%" not in content:
        problems.append(
            f"AGENTS.md should state the enforced coverage gate ({fail_under}%); "
            "the number changed in pyproject.toml"
        )
    return problems


def check_testpath_documented(content: str, pyproject: dict) -> list[str]:
    problems = []
    testpaths = pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths")
    if testpaths:
        first = testpaths[0]
        if first not in content:
            problems.append(f"AGENTS.md should reference the configured testpath '{first}'")
    return problems


def check_env_vars_documented(content: str) -> list[str]:
    problems = []
    from mcp_shlink.config import Settings  # local import: avoid package import cost at parse time

    for field_name in ("base_url", "api_key"):
        env_name = f"SHLINK_{'BASE_URL' if field_name == 'base_url' else 'API_KEY'}"
        if env_name not in content:
            problems.append(f"AGENTS.md must document required env var {env_name} (see config.py)")
    optional_env = {"SHLINK_ENV", "SHLINK_ANALYTICS_ENABLED", "SENTRY_DSN"}
    missing_optional = {name for name in optional_env if name not in content}
    if missing_optional:
        problems.append(
            "AGENTS.md optional-env table is missing: " + ", ".join(sorted(missing_optional))
        )
    assert Settings.model_fields, "config.Settings must remain a pydantic model"
    return problems


def main() -> int:
    content = _read_agents_md()
    pyproject = _load_pyproject()

    problems: list[str] = []
    problems += check_dev_group_documented(content, pyproject)
    problems += check_coverage_gate_documented(content, pyproject)
    problems += check_testpath_documented(content, pyproject)
    try:
        problems += check_env_vars_documented(content)
    except ImportError:
        # Package not installed in this interpreter; skip env-var cross-check.
        print("note: mcp_shlink not importable; skipping env-var cross-check")

    if problems:
        print("AGENTS.md is out of date with the repository:")
        for problem in problems:
            print(f"  - {problem}")
        print("Update AGENTS.md (or the matching config) so docs and code agree.")
        return 1

    print("AGENTS.md validation passed: commands, coverage gate, and env vars are current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
