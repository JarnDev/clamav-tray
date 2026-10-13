## What changes

## Why

If it fixes a bug, add a code comment explaining what keeps someone from
reintroducing it. That is the project's convention: comments record the
alternative that failed or the measurement that contradicted intuition.

## Checked

- [ ] `python3 -m clamav_tray --dump` runs
- [ ] `python3 tests/run.py` passes
- [ ] if docs changed, both languages were updated (`python3 scripts/check-docs-i18n.py`)
- [ ] if the menu changed, I read [docs/dbusmenu.md](../docs/dbusmenu.md)

## Branch

PRs go against `main`, in Python. The `rust` branch is a personal exercise and
may be force-rewritten.

<!-- Português é bem-vindo na descrição do PR. -->
