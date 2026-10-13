**English** · [Português (Brasil)](README.pt-BR.md)

# quarantine-stats

Publishes a summary of the root quarantine to a readable file, so `clamav-tray`
can show it.

## Why it's needed

The system quarantine is typically `750` owned by `root`, and that is **right**
— it's stored malware. A tray indicator runs as a user and can't even
*count* what's in there.

No permission trick solves it: `0751` would allow opening a file whose name is
known, but not listing. Someone with privilege has to write the summary.

## Install

```sh
sudo ./install.sh [/path/to/quarantine]
```

Without an argument, it looks in the usual paths.

## What gets published

```
/var/lib/clamav-tray/quarantine.stats

path=/var/quarantine/clamav
count=5
bytes=14722957
newest=2026-09-22T15:00:11+00:00
checked=2026-09-25T20:52:42+00:00
```

**Nothing sensitive:** count, total size and dates. No file names,
no content.

## Decisions worth knowing

**Ignores `clamdscan`'s locks.** It creates a `.clamav-quarantine-lock.<pid>`
per run and doesn't remove it when the scan is interrupted. Counting them
would turn the indicator into a false alarm — measured: six locks became
"6 files" in the menu, without any detection having happened.

**Atomic swap** (`mktemp` + `mv -f`). The tray may be reading at that instant,
and a half-written file would become a wrong count instead of a read error.

**Carries the collection time.** The tray shows "checked today 07:42" next to the
number. Stale data presented as current is worse than missing data.

## If you use the `daily-scan` extra

It already calls the publisher at the end of every scan. This timer only adds
freshness for when someone touches the quarantine by hand.
