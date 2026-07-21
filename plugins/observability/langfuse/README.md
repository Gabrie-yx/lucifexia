# Langfuse Observability Plugin

This plugin ships bundled with Lucifex but is **opt-in** — it only loads when
you explicitly enable it.

## Enable

Pick one:

```bash
# Interactive: walks you through credentials + SDK install + enable
lucifex tools  # → Langfuse Observability

# Manual
pip install langfuse
lucifex plugins enable observability/langfuse
```

## Required credentials

Set these in `~/.lucifex/.env` (or via `lucifex tools`):

```bash
LUCIFEX_LANGFUSE_PUBLIC_KEY=pk-lf-...
LUCIFEX_LANGFUSE_SECRET_KEY=sk-lf-...
LUCIFEX_LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted URL
```

Without the SDK or credentials the hooks no-op silently — the plugin fails
open.

## Verify

```bash
lucifex plugins list                 # observability/langfuse should show "enabled"
lucifex chat -q "hello"              # then check Langfuse for a "Lucifex turn" trace
```

## Optional tuning

```bash
LUCIFEX_LANGFUSE_ENV=production       # environment tag
LUCIFEX_LANGFUSE_RELEASE=v1.0.0       # release tag
LUCIFEX_LANGFUSE_SAMPLE_RATE=0.5      # sample 50% of traces
LUCIFEX_LANGFUSE_MAX_CHARS=12000      # max chars per field (default: 12000)
LUCIFEX_LANGFUSE_DEBUG=true           # verbose plugin logging
```

## Disable

```bash
lucifex plugins disable observability/langfuse
```
