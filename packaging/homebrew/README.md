Homebrew packaging notes for Lucifex Agent.

Use `packaging/homebrew/lucifex-agent.rb` as a tap or `homebrew-core` starting point.

Key choices:
- Stable builds should target the semver-named sdist asset attached to each GitHub release, not the CalVer tag tarball.
- `faster-whisper` now lives in the `voice` extra, which keeps wheel-only transitive dependencies out of the base Homebrew formula.
- The wrapper exports `LUCIFEX_BUNDLED_SKILLS`, `LUCIFEX_OPTIONAL_SKILLS`, and `LUCIFEX_MANAGED=homebrew` so packaged installs keep runtime assets and defer upgrades to Homebrew.

Typical update flow:
1. Bump the formula `url`, `version`, and `sha256`.
2. Refresh Python resources with `brew update-python-resources --print-only lucifex-agent`.
3. Keep `ignore_packages: %w[certifi cryptography pydantic]`.
4. Verify `brew audit --new --strict lucifex-agent` and `brew test lucifex-agent`.
