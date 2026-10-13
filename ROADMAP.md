**English** · [Português (Brasil)](ROADMAP.pt-BR.md)

# Roadmap

Two independent tracks. The product track delivers value to whoever installs it; the learning
track exists for me. **The second never delays or degrades the first.**

---

# Track 1 — the product (Python, branch `main`)

The numbers below are the ones in the [CHANGELOG](CHANGELOG.md) and on PyPI. A future version is
an intention, not a promise: items move up or down as real use shows.

## v0.1 — the foundation (2026-09-25)

- [x] Unit state, discovered by the `clam*` glob
- [x] **Daemon** × **job** distinction by the unit's `Type=`
      (`simple` = running is healthy; `oneshot` = running means *in progress*)
- [x] Result of the last scan, read from clamdscan's own `SCAN SUMMARY`
- [x] On-demand scan (home and removable media) as a transient unit
- [x] Icon reflects the state; paths come from `clamconf`
- [x] TOML config (`~/.config/clamav-tray/config.toml`)
- [x] Translations, with English as the source and complete pt_BR
- [x] Two quarantines with distinct owners, and removable media detected without a subprocess
- [x] Optional extras in `contrib/extras/` and autostart as a user service

## v0.2 — first published (2026-10-13)

- [x] On PyPI: `pipx install --system-site-packages clamav-tray`
- [x] Progress bar by file **count**, legible at real size
- [x] The alarm picks the scan by date, not by bus
- [x] Incremental `daily-scan` (by ctime) every day, full every 7
- [x] Without PyGObject, the program says how to fix it instead of dumping a traceback
- [x] `scripts/release.sh`: release in one command, publishing with manual approval

## v0.3 — edges the packaging exposed

Whoever installs from PyPI has a worse experience than whoever clones. Closing that gap comes
before any new feature.

- [x] **Autostart without cloning.** `clamav-tray --install-autostart`, with the templates inside
      the package and the same `is-active` check as the script — and `--show-autostart` to
      inspect destination and content before allowing it.
- [x] **No display: a message instead of a core dump.** GTK aborted without `DISPLAY`; now
      `Gtk.init_check()` is checked first, also covering a `DISPLAY` that points at nothing.
- [x] **`--dump --json`**, stable output for scripts and for Glance/Conky. It is also the contract
      that Track 2's `clamav-status` will fulfill — writing it in Python first pins the format.
- [x] **Notification when the on-demand scan finishes**, from the tray itself, over D-Bus and with
      no new dependency — telling a quarantined threat apart from one found but not contained.
- [x] **Validate Fedora and Arch.** In containers with systemd: discovery finds `clamd@scan`
      (Fedora) and `clamav-daemon` (Arch), and `clamconf` gives the right paths on both. It also
      exposed a bug: with no service at all, the tray said "Protected" — fixed.

## v0.4 — documentation in two languages (2026-10-13)

- [x] English by default, Brazilian Portuguese next to it (`X.pt-BR.md`), checked in CI
- [x] Numbers follow the interface language (`14.9 GB` / `14,9 GB`)

## v0.5 — GNOME panel (in progress, branch `feat/gnome-extension`)

An optional GNOME Shell extension that draws a rich panel — real progress bar, colors,
cards — on top of the state the program already publishes. The tray keeps working on any
desktop; the extension only **reads and draws**, and its buttons call `clamav-tray`. All
logic stays in Python. Merged into `main` only after acceptance tests.

- [x] **F0 — proof of concept.** A nested GNOME Shell, isolated from the real session (own
      D-Bus, dconf and extension dirs: `scripts/dev-nested-shell.sh`), loads a bar button;
      three disable/enable cycles leave nothing behind.
- [x] **F1 — Python side.** The tray writes `state.json` to `$XDG_RUNTIME_DIR` atomically on
      every refresh; new JSON fields (`scan.progress`, `media`, `quarantine`) without a schema
      bump; `--headless` (no tray icon) and action commands (`--scan-home`, `--stop-scan`,
      `--scan-device`).
- [ ] **F2 — read-only extension.** Status-colored icon; panel with header, services and last
      scan. JSON → view model in a pure module tested with `gjs` in CI.
- [ ] **F3 — live.** Real progress bar, media and quarantine cards; falls back to polling
      `--dump --json` when the state file goes stale.
- [ ] **F4 — actions.** Panel buttons call the F1 commands.
- [ ] **F5 — install and docs.** `--show-gnome-extension` / `--install-gnome-extension`,
      inspect before allowing, as with autostart; docs in both languages.
- [ ] **F6 — release 0.5.0.** Publishing on extensions.gnome.org is a separate decision.

Only GNOME versions actually tested go into `metadata.json`: a new GNOME disables the
extension instead of breaking the bar, and the normal tray takes over.

## v0.6 — extras

- [ ] `daily-scan`: optional **whole-system** mode, beyond home, with its own exclusions
      (`/proc`, `/sys`, `/var/lib/docker`, snaps, AI models). Needs thought about cost: the
      full scan of home alone already takes hours on a SATA SSD.
- [ ] `daily-scan`: the weekly full scan with **notification only when something changes**, so
      the daily alarm doesn't turn into noise.
- [ ] Automated tests for the `contrib/` scripts (today: only `bash -n` in CI and manual testing
      against the real clamd).

## Distribution — on demand, not by date

PyPI covers whoever has pipx. A distro package is recurring work (one build per distro version,
signing, review), and only pays off with people using it.

| Channel | When | Why in this order |
|---|---|---|
| **AUR** | first request from an Arch user | one `PKGBUILD`; the cheapest to maintain |
| **`.deb` / PPA** | recurring real use on Debian/Ubuntu | solves the apt dependencies in one step, but is the most expensive |
| **Flathub** | probably never | the sandbox fights the premise: reading the host's systemd and `/proc` |

The `contrib/` extras stay **out** of any package of the program: they install system units as
root, and the tray is installable without privilege by design. If it ever makes sense, they go in
a separate, optional package.

## Open, unversioned — what people ask for but I'm not sure I want yet

- [ ] Service actions (start/stop/restart) — requires polkit, and greatly widens the surface
- [ ] Multiple `clamd@` instances on Fedora, side by side
- [ ] `clamonacc` support (on-access scanning) beyond showing the unit

## Out of scope, by decision

Editing `clamd.conf`, scheduling scans from a GUI, managing quarantine through an interface. That
is ClamTk, and it isn't worth rebuilding. This project **observes and triggers**; it doesn't
configure.

Non-systemd (OpenRC, runit, s6) stays down here with no date: it would be a whole second layer of
detection, and the project's value is precisely the systemd integration.

---

# Track 2 — learning Rust (branch `rust`)

**The rule that governs everything:** `main` never depends on this branch. The switch happens
when I'm confident in the language, and not before. If that never comes, the Python version stays.

## Migration order, and why

The order is pedagogical, not technical. Each step introduces **one** new concept.

| # | Module | What it teaches | Why in this position |
|---|---|---|---|
| 1 | `scan.py` → `scan.rs` | `Result`, `?`, `Option`, enums, parsing | Pure input and output: text in, struct out. **Testable without a running machine.** No I/O, no shared ownership |
| 2 | `units.py` → `units.rs` | `std::process::Command`, structs, `HashMap` | Still synchronous. Introduces an external process and real error handling |
| 3 | `config.py` → `config.rs` | `serde`, traits, lifetimes | First time the borrow checker shows up in force |
| 4 | `actions.py` → `actions.rs` | environment, `PathBuf`, program detection | Small; consolidates what came before |
| 5 | `tray.py` → `ksni` | async, `Arc<Mutex>`, `'static` bounds | **Last on purpose.** It's where beginners get stuck, and debugging a tray is miserable: when it doesn't show up, there's no error message, just absence |

Between steps 2 and 3, the binary is already useful on its own as `clamav-status --json`, and the
Python tray can start consuming that JSON. It's the
[ai-usagebar](https://github.com/akitaonrails/ai-usagebar) pattern: the binary does the work, a
thin layer draws.

That means the migration delivers value **halfway through**, not only at the end — and that step 5
may never happen without that being a loss.

## Validation protocol

The same one I use in the C/C++ track: when I finish a module, I don't move on before being
questioned about it. "It compiled and ran" doesn't count — the test is explaining why the compiler
accepted it.

For each ported module:

1. Behavior identical to the Python one, verified with the **same input** on both
2. Tests covering the cases I discovered using the Python version for real
3. Questioning: why this signature, why this ownership, what the compiler prevented and what I
   would have gotten wrong without it

## Prerequisite I took on

Finish pointers and RAII in the C/C++ track before opening Rust. Ownership and borrowing make much
more sense after managing memory by hand — they stop being an arbitrary rule and become "the
compiler checking what I was already trying to get right".

## Signs that the switch can happen

These aren't goals, they're symptoms. When I notice that:

- I read a compiler error and already know what to do, without searching
- I write the signature before the body, and it's usually right
- I don't feel the urge to `.clone()` my way out of a problem
- I can review someone else's Rust PR

Then the branch becomes `main`. Not before.
