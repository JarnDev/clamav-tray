**English** · [Português (Brasil)](README.pt-BR.md)

# contrib

`clamav-tray` **observes** what exists. It doesn't install units, doesn't schedule
scans and doesn't decide what to scan — that's the design choice that keeps it
installable without root.

The consequence is honest: on a machine where only `apt install clamav-daemon` was run,
half of the menu stays empty. No relevant distro ships a scheduled scan, a
folder monitor or a quarantine.

| | Debian/Ubuntu | Fedora | Arch |
|---|---|---|---|
| daemon + freshclam | in the package | yes | yes |
| scheduled scan | **not shipped** | **not shipped** | **not shipped** |
| folder monitor | **not shipped** | **not shipped** | **not shipped** |
| quarantine | **not shipped** | **not shipped** | **not shipped** |

The extras here fill that in. Each one is **independent and optional** — install only
what you want, or none, or use them as a reference to write your own.

## Extras

| | What it does |
|---|---|
| [`extras/daily-scan`](extras/daily-scan) | home scan: daily incremental and weekly full, with exclusions and quarantine |
| [`extras/downloads-watch`](extras/downloads-watch) | scans the Downloads folder on every new file |
| [`extras/usb-scan`](extras/usb-scan) | scans removable media as soon as it's mounted |
| [`extras/quarantine-stats`](extras/quarantine-stats) | publishes the root quarantine summary for the tray to read |

## Rules every installer here follows

- **Never overwrites.** If a unit with the same name already exists, it stops and says so.
- **`clamav-tray-` prefix** on everything, so it doesn't collide with what you already have.
- **Says how to uninstall** when it finishes.
- **No `curl | sudo bash`.** You read the file and run it.

## Why it doesn't all come together in the package

Installing a system unit requires root and takes a stance on what to scan and when.
A tray indicator that asks for root at install time is a different category of program
— and would end up competing with the configuration of whoever already has their own.
