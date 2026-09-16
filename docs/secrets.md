# Secrets Management

How secrets are stored, injected, and kept out of this repository.

## Rules

1. **Never hardcode secrets.** No API keys, tokens, or passwords in source,
   tests, docs, or CI YAML.
2. **Local development** reads secrets from environment variables
   (`.env` files are gitignored; copy `.env.example` to `.env` and fill in).
3. **CI** uses GitHub Actions secrets (`${{ secrets.* }}` references only);
   the Droid workflows use `secrets.FACTORY_API_KEY`, PyPI publishing uses
   Trusted Publishing (`id-token: write`), so there are no PyPI tokens at all.
4. **Secrets in logs are redacted** by `mcp_shlink.observability` (key-shaped
   fields, `X-Api-Key`/`authorization` headers, basic-auth URLs) before any
   line is written.

## Runtime secrets

| Secret | Used by | Source |
|--------|---------|--------|
| `SHLINK_API_KEY` | Shlink API auth | Operator-provided env var |
| `SENTRY_DSN` (optional) | Error tracking | Operator-provided env var |
| `FACTORY_API_KEY` | Droid CI workflows | GitHub Actions secret |

## Enforcement (defense in depth)

- `pre-commit` hook `detect-private-key` + `detect-secrets` with
  `.secrets.baseline` (refresh with `detect-secrets scan --update .secrets.baseline`).
- CI job **Secret Detection** runs `gitleaks detect --redact` on every push/PR.
- `.gitignore` blocks `.env` style files (not `.env.example`).
- `scripts/check_file_size.py` indirectly hinders blob smuggling of large
  secret dumps.

## If a secret leaks

See `docs/runbooks.md` > "Incident: suspected leaked API key" (rotate first,
then verify scanning is clean).
