# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **`state.json`**: the running tray writes its state to
  `$XDG_RUNTIME_DIR/clamav-tray/state.json` on every refresh, atomically. Same
  document as `--dump --json`, plus what only the tray knows: scan progress and
  which media it scanned this session. New fields (`producer`, `generated_at`,
  `scan.progress`, `media`, `quarantine`) — no `schema` bump, since nothing
  changed meaning.
- `language` in the JSON: the resolved interface language, so whoever draws the
  state speaks the same language.
- **GNOME Shell extension (in development, GNOME 46)** in `gnome-extension/`: a
  status-colored shield in the top bar and a panel with state, last and next scan
  and services, drawn from `state.json`. It only draws — every decision comes
  ready from the program. A stale `state.json` shows "tray not running", never a
  green shield. Text colors measured at 3:1 or more on both the light and the dark
  menu.
  It is live: a real progress bar (counted files, never an invented percentage)
  that moves with the panel open, the percentage next to the icon, and cards for
  removable media and both quarantines. Without a fresh `state.json` it falls
  back to `clamav-tray --dump --json` — every 30 s at most, one at a time, under a
  20 s `timeout` — and says the view is a snapshot.
- `refresh_secs` in the JSON: readers of `state.json` call it stale after 3
  refreshes (at least 30 s), so a longer interval in the config no longer reads as
  "tray not running".
- **`--headless`**: no tray icon, no display needed; keeps refreshing, notifying
  and writing `state.json`. For when the GNOME panel draws instead.
- **`--scan-home`, `--scan-device <mountpoint|key>`, `--stop-scan`** from the
  command line — the same path as the menu.

### Changed

- The on-demand scan's state no longer lives only in the memory of whoever
  started it: starting writes `scan.json` (target, medium, when), stopping marks
  it, and the tray **adopts** any running on-demand scan from it. A scan started
  from the command line now ends with a notification, one stopped from the
  command line doesn't claim it "did not finish", and a tray restarted mid-scan
  no longer loses track of it.

## [0.4.0] — 2026-10-13

### Added

- **Documentation in English and Brazilian Portuguese.** English is the default
  (`X.md`, also what PyPI shows); Portuguese sits next to it as `X.pt-BR.md`,
  with a language switcher on the first line of every page. Faithful translation:
  same sections, same measurements.
- `scripts/check-docs-i18n.py`, run in CI: every page needs its pair, with the
  same number of headings and code blocks. It catches "changed one language and
  forgot the other"; it does not judge the translation itself.

### Changed

- Issue and pull request templates are in English (Portuguese is welcome in the
  text). They stay out of the bilingual pairing: GitHub lists each template as its
  own option.
- The CHANGELOG is now English-only, past entries included. `scripts/release.sh`
  looks for `## [Unreleased]` instead of `## [Não lançado]`.
- README status and CONTRIBUTING brought up to date: 0.3 on PyPI, Fedora and
  Arch checked in containers, tests run with `python3 tests/run.py`.

### Fixed

- **Numbers ignored the interface language.** Five places replaced "." with ","
  on their own, so the English interface showed "14,9 GB" and "1.131.791" files.
  They now go through `i18n.number()`: "14.9 GB" / "1,131,791" in English,
  "14,9 GB" / "1.131.791" in Portuguese.
- `clamav_tray.data` is listed in `packages`: setuptools warned at build time
  that relying on it being picked up implicitly will stop working.

## [0.3.0] — 2026-10-13

### Added

- `scripts/release.sh X.Y.Z`: releases a version in one command, with `--dry-run`.
  Checks before writing anything (version higher than the current one and not yet
  in the CHANGELOG, notes present, clean tree, in sync with `origin`, green CI,
  tests), bumps the version in both files, closes the CHANGELOG, makes a signed
  commit and tag, and pushes over SSH. The `pypi` environment now requires manual
  approval and only accepts `v*` tags.
- **`clamav-tray --dump --json`**: the state the tray sees, as data, for scripts,
  Glance, Conky or `jq`. Versioned format (`schema`), documented in
  `docs/json.md` and locked down by `tests/test_report.py`. Needs no display.
- **Autostart without cloning the repository**: `clamav-tray --install-autostart
  [--xdg]` and `--uninstall-autostart`. The unit and `.desktop` templates now ship
  inside the package (`clamav_tray/data/`).
- **`clamav-tray --show-autostart [--xdg]`: inspect before allowing.**
  Shows the destination, the command, the whole file and the `systemctl` calls
  that would follow — or the diff, if a file already exists — without writing
  anything. The installer shows the same and only writes after confirmation;
  outside a terminal, only with `--yes`.
- **Notification when the on-demand scan finishes** (home or media), from the
  tray itself: clean, threats quarantined, or threats found and **not**
  contained (read-only media) — the last one urgent. Stopping the scan on
  purpose doesn't notify. Talks directly to `org.freedesktop.Notifications` via
  Gio, with no new dependency; without a notification server, it carries on
  without notifying.

### Changed

- `packaging/install-autostart.sh` now only forwards to
  `clamav-tray --install-autostart`, with the same arguments. It now asks before
  writing, and without a terminal it refuses instead of writing directly.
- README with the install command for Debian/Ubuntu, Fedora and Arch, checked in
  clean containers (on Fedora and Arch, with systemd and live discovery), and the
  two configuration pitfalls they revealed (socket commented out on Fedora; a
  unit that disappears without the signature database on Arch).
- Autostart writes `~/.local/bin/clamav-tray` (the pipx link) instead of the
  path inside the venv, which changes if pipx recreates the environment.

### Fixed

- **With no ClamAV service at all, the tray showed a green shield**: "Protected,
  all services running" about no service whatsoever. Seen on a freshly installed
  Fedora, which enables nothing. Now it's "Attention — no ClamAV service found",
  and the JSON `status` is `warn`.
- **Without a display, the program aborted with a core dump.** GTK doesn't fail
  without `DISPLAY`: it aborts (`Gtk-ERROR`) at the first widget. Now
  `Gtk.init_check()` is checked first, and the program says what's missing and
  exits with code 1. It also covers a `DISPLAY` pointing at a display that
  doesn't exist — checking only the environment variable wouldn't catch that case.

## [0.2.0] — 2026-10-13

### Added

- **Package on PyPI** (`pipx install --system-site-packages clamav-tray`) and a
  workflow that publishes on every `v*` tag, via trusted publishing (OIDC, no
  stored token). The workflow refuses to publish if the tag, `pyproject.toml` and
  `__version__` don't state the same version.
- Without PyGObject in the environment, the program says how to fix it instead of
  dumping a traceback. Tested on a clean Ubuntu 24.04: that's what happened with
  `pipx install` without `--system-site-packages`.

### Changed

- README links and images are now absolute, so they render on PyPI.
- License in SPDX format (PEP 639); the old format becomes an error in setuptools
  from Feb/2027.
- **`daily-scan` is now incremental on most days.** It scanned the whole home
  every day — measured, 4h40 over 1.1 million files, from 03:12 to 07:54, on an
  SSD that becomes unusable meanwhile. Now the same daily timer scans only what
  changed since the last completed scan (by *ctime*, which can't be forged with
  `touch -d`), and the full scan runs when the last one is more than 7 days old
  (`CLAMAV_TRAY_FULL_EVERY`). Details and the reason behind each choice in
  `contrib/extras/daily-scan/README.md`. The state lives in
  `/var/lib/clamav-tray-daily` (`CLAMAV_TRAY_DAILY_STATE` — a name distinct from
  `CLAMAV_TRAY_STATE`, which is where the tray reads the quarantine statistics).
- Test module discovery moved from the CI YAML to `tests/run.py`: with the list
  pasted into the workflow, a new test file didn't run until someone remembered
  to edit it.
- Both README images are now **regenerable**:
  `docs/screenshots/make-tray-states.py` and `make-menu-states.py`. Before, the
  HTML that produced them lived in a temporary directory, so fixing them meant
  redoing them from scratch. The menu one builds the bar from the constants read
  from `widgets.py`, so it can't diverge from the program.
- Secondary text and menu separators with more contrast, and the same background
  in both images. Measured against the menu background (`#353535`): sections from
  **3.63:1 to 5.19:1**, detail lines from 5.82:1 to 6.43:1; the caption above
  each menu, against the page background, from 5.36:1 to 7.57:1.

### Fixed

- **The alarm picked the scan by bus, not by date.**
  `pick_scan_unit` preferred the user unit unconditionally, and the transient
  unit remains after finishing (`--remain-after-exit`, which is what keeps the
  result). Consequence: a threat found on demand kept lighting up the icon days
  later, and the clean scheduled scans in between were never read — the unit is
  chosen before the summary is read. The order is now: running now > finished
  last > on demand as the tiebreaker.
- The on-demand scan **empties the output file before launching**. Shell
  redirection only truncates when the shell runs; until then — and forever, if
  the launch failed — the file still answered with the previous scan's summary.
- The autostart installer claimed "Enabled" while the service was failing in a
  loop: the unit had `ExecStart` hardcoded to `~/.local/bin/clamav-tray`, which
  doesn't exist in an install from source. Now it resolves the executable,
  refuses if there's no way to run it, and checks `is-active` after enabling.

- **The icon state strip was illegible.** Adwaita's symbolic icons carry
  `fill="#2e3436"` embedded in the `<path>`, which beats the `<svg>`'s
  `currentColor`. GTK ignores that attribute and recolors the icon; a browser
  doesn't. Since the image is rendered in Chrome, the five icons came out dark
  blue on a dark gray pill — measured, **1.16:1**, against the WCAG minimum of
  3:1 for graphical objects. Now the attribute is removed before rendering and
  the icons come out in the panel's foreground color: **19:1**.

- **The progress bar track was invisible.** It used `░` (U+2591, quarter
  coverage): measured at real size, **1.00:1** against the menu background — the
  same color. Only the filled part showed, and without the track you can't judge
  the proportion. Now it's `▒` (U+2592, half): **1.45:1**. The ceiling is low
  because color doesn't cross dbusmenu (see `docs/dbusmenu.md`), so the only
  lever is glyph density — `▓` was tested and rejected: it's too close to full
  and the boundary between the two gets lost.

## [0.1.0] — 2026-09-25

First public version. Born from a 75-line personal script.

### Added

- State of the ClamAV units, discovered by the `clam*` glob — covers
  `clamav-daemon.service` (Debian, Ubuntu, Arch) and `clamd@scan.service` (Fedora)
- **Daemon × job** distinction by the unit's `Type=`: without it, a folder
  monitor would show up as "scan in progress" forever
- On-demand scan of home and removable media, as a transient user unit —
  visible, stoppable and without root
- Progress bar by file **count**, not a clock-based estimate
- Removable media detection via `/proc/mounts` + `/sys/block/*/removable`,
  without a subprocess
- Two quarantines with distinct owners, and a convention for the root one to
  publish readable statistics
- Distinction between a threat **found** and a threat **contained** — read-only
  media reports the first without achieving the second
- Configurable language, with English as the source
- Four optional extras in `contrib/extras/`, each with its own installer
- Autostart as a user service or XDG autostart

### Decisions recorded

- The program **observes**; it doesn't install units or schedule scans. That's
  what keeps it installable without root.
- The verdict comes from the `SCAN SUMMARY`, never from the exit code:
  `clamdscan` returns 2 if any file couldn't be opened, and that's routine in an
  hours-long scan.
- Finding a virus isn't the unit's failure, it's its job.
- The bar is drawn with characters because widgets don't cross dbusmenu.
  See [docs/dbusmenu.md](docs/dbusmenu.md).
