## Description

<!-- What does this PR change and why? Link related issues with "Fixes #123". -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing behavior to change)
- [ ] Documentation only

## How was this tested?

<!-- Which test suites cover this? Note any manual steps. -->

- [ ] `pytest` passes locally (coverage gate: 80%)
- [ ] New/updated tests included for changed behavior

## Checklist

- [ ] `ruff check .` and `ruff format . --check` pass
- [ ] `mypy src/` passes (strict)
- [ ] `pre-commit run --all-files` passes
- [ ] AGENTS.md updated if commands or env vars changed
- [ ] Feature flag added if shipping risky behavior behind a toggle
