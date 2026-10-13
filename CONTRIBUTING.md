**English** · [Português (Brasil)](CONTRIBUTING.pt-BR.md)

# Contributing

Thanks for looking. This is a small project, maintained by one person, and what
follows is better read as honest expectation than as rules.

## First of all: the `rust` branch

`main` is the Python version, working and maintained. **PRs should go against
it.**

The `rust` branch is a personal learning exercise — it may be force-rewritten,
rebased or abandoned without notice. Do not build anything on top of it.

## What helps the most

**Testing on another distro.** The project was written and used on Ubuntu.
Fedora (templated unit `clamd@scan.service`) and Arch were checked in containers
with systemd, which is not the same as daily use on a desktop. A report with the
output of:

```sh
systemctl list-units --all 'clam*'
clamconf -n | grep -E 'LocalSocket|LogFile'
python3 -m clamav_tray --dump
```

is already worth an issue, even if nothing is broken.

**Translating.** Copy the `pt_BR` block in `clamav_tray/i18n.py` and translate
it. There is no tool to install: the catalog is a Python dictionary, and a key
without a translation falls back to English instead of breaking.

**Reporting a tray that does not show up.** Say the desktop and the version.
GNOME removed the tray in 3.26 and needs an extension; the others vary.

## Before proposing an interface change

Read [docs/dbusmenu.md](docs/dbusmenu.md). The menu **is not drawn by GTK** — it
is serialized over D-Bus and rendered by the shell. No widget crosses that
boundary, and five bugs in this project came from not knowing that.

If your idea involves a widget inside the menu, it probably does not work.
If it involves bold, text color or a tooltip, it definitely does not work.

## Tests

```sh
python3 tests/run.py                 # the whole suite; standard library only
python3 scripts/check-docs-i18n.py   # EN and PT-BR docs structurally in sync
```

`tests/test_scan.py` uses **real clamdscan output** as samples, not invented
text. If you touch the parser, keep that property: the value of the test lies in
it having come from a real machine.

## Style

There is no linter configured. The code has one deliberate trait worth
respecting: **comments explain why, not what**, and almost always record an
alternative that was tried and failed, or a measurement that went against
intuition.

If you fix a bug, the most helpful comment is the one that stops someone from
reintroducing it.

## What will probably be declined

- Installing a system unit or asking for root at install time. The project is
  installable without privilege, and that is what sets it apart from ClamTk.
  Privileged automation goes into `contrib/extras/`, optional.
- Scheduling scans on its own. The program **observes**; whoever administers the
  machine decides what to scan and when.
- Reimplementing what ClamTk already does (editing `clamd.conf`, managing the
  quarantine through a GUI).

## Releasing a version (maintainer)

```sh
scripts/release.sh 0.3.0 --dry-run   # checks everything and shows the notes, writes nothing
scripts/release.sh 0.3.0             # writes signed commit + tag and pushes, asking first
```

Before writing anything, the script refuses if: the number is not greater than
the current one or already appears in the CHANGELOG; the `[Unreleased]` section
is empty; the tree is dirty; local `main` diverges from `origin/main`; the
commit's CI is not green; or the local tests fail.

Then it bumps the version in `pyproject.toml` and in `__version__`, turns
`[Unreleased]` into `[X.Y.Z] — date` (leaving an empty `[Unreleased]` on top)
and pushes over **SSH** — the HTTPS token usually lacks the `workflow` scope. The
tag triggers `publish.yml`, which **waits for manual approval** in the GitHub
`pypi` environment before publishing. A PyPI release cannot be undone: a
published number can never be reused, not even after deletion.
