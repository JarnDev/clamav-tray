**English** · [Português (Brasil)](design.pt-BR.md)

# Design decisions

The long explanations the README carried up to v0.1. Each one exists because a
reasonable alternative was tried and failed, or because measurement contradicted
intuition.

## What works on a clean install

The program **observes** what exists. It doesn't install units, doesn't schedule
scans and doesn't decide what to scan — that choice is what keeps it installable
without root.

Honest consequence, measured on Ubuntu with `clamav-daemon` and `clamav-freshclam`:

| | Out of the box |
|---|---|
| ClamAV Daemon, Freshclam, On-Access | **yes**, they come in the packages |
| Scan my home now | **yes**, only needs `clamd` running |
| User quarantine | **yes**, created on demand |
| Progress bar | **yes**, it belongs to the on-demand scan |
| Scheduled scan, "Next", "Last" | **no** — no distro ships it |
| Folder monitor | **no** |
| System quarantine | **no** — it comes from the `--move=` of whoever scheduled the scan |

The top half works; the scan half stays empty. It isn't a bug: the distro doesn't
schedule scans, and the program shouldn't invent one.

To fill it in, there are **optional and independent** extras in [`contrib/extras/`](../contrib/extras),
each with its own installer — daily scan, Downloads monitor and publishing of
quarantine statistics. Install only what you want, or use them as a reference to
write your own.

## Language

**English is the default.** The strings in the code are the English ones, and
translating is optional by construction: a key without a translation shows up in
English instead of breaking.

```toml
[general]
language = "pt_BR"   # or "auto" to follow the system locale
```

Translations live in `clamav_tray/i18n.py`, in a dictionary. It doesn't use gettext on purpose:
compiling `.po` into `.mo` would add a build step to a project that today installs with
`pipx install` and nothing else. To contribute a language, copy the `pt_BR` block and translate it —
without installing any tool. The keys are already the English sentences, so migrating to
gettext later is mechanical.

## Configuration

There's a **Settings** item in the menu: it creates the commented file if it doesn't exist and opens
it in your editor. The file is **reloaded on its own when saved** — no restart.

There's no GTK preferences dialog on purpose: it would be more code than the rest of the program
combined, for an edit that rarely happens.

No configuration is required. The program discovers on its own:

- **units** — through the `clam*` glob in systemd, which covers both `clamav-daemon.service`
  (Debian, Ubuntu, Arch) and `clamd@scan.service` (Fedora, which uses a *templated* unit)
- **paths** — by asking `clamconf`, which comes from ClamAV itself and not from the packager

To adjust labels, add units or override paths, see
`clamav-tray.example.toml`.

## Permissions

Reading unit state requires no privilege. Reading the journal **history** requires being in `adm`
or `systemd-journal`, depending on the distro. Without that the program keeps working: it shows the
current state and omits the history, instead of breaking.
