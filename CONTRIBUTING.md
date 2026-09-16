# Contributing

Thank you for considering contributing to mcp-shlink!

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your changes

## Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (enforces lint, types, secrets, doc freshness)
pre-commit install
```

## Running Tests

```bash
# Unit + integration tests; runs with xdist (parallel) and random order,
# enforcing the 80% coverage gate and printing the 10 slowest tests.
pytest

# Integration tests use a local Shlink stub (tests/shlink_stub_server.py),
# so no real Shlink instance or network access is required.
```

## Code Style

This project uses ruff for linting and formatting:

```bash
ruff check .
ruff format .
```

Enabled rule families include naming consistency (`N`), complexity (`C90`,
max 10 per function), and TODO hygiene (`TD`: every TODO needs an owner).

## Type Checking

```bash
mypy src/
```

## Quality Gates

The same checks CI runs are available locally:

```bash
vulture src                # dead code
xenon src --max-absolute B --max-average A --max-modules B
deptry src                 # unused dependencies
python scripts/check_file_size.py
python scripts/check_agents_md.py
```

## Submitting Changes

1. Ensure all tests pass and code is linted
2. Run full verification: `ruff check . && ruff format . --check && mypy src/ && pytest`
3. Commit your changes (pre-commit hooks run automatically)
4. Push to your fork and submit a pull request
5. Link the issue in your PR description
6. Fill out the PR template (description, testing done, checklist)

## Reporting Bugs

Open a [bug report](https://github.com/magnus919/mcp-shlink/issues/new?template=bug_report.md)
using the issue template.

## Suggesting Features

Open a [feature request](https://github.com/magnus919/mcp-shlink/issues/new?template=feature_request.md)
to discuss new features before implementing.
