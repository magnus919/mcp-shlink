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
```

## Running Tests

```bash
pytest
```

## Code Style

This project uses ruff for linting and formatting:

```bash
ruff check .
ruff format .
```

## Type Checking

```bash
mypy src/
```

## Submitting Changes

1. Ensure all tests pass and code is linted
2. Run full verification: `ruff check . && ruff format . --check && mypy src/ && pytest`
3. Commit your changes with clear commit messages
4. Push to your fork and submit a pull request
5. Link the issue in your PR description

## Reporting Bugs

Please report bugs via the [issue tracker](https://github.com/magnus919/mcp-shlink/issues).

## Suggesting Features

Open an issue to discuss new features before implementing.
