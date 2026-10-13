**English** · [Português (Brasil)](README.pt-BR.md)

# daily-scan

Home scan at 03:00, with exclusions and quarantine: **incremental** every day
(only what changed since the last completed scan) and **full** every 7 days.

No distro ships this — that's why `clamav-tray` shows "Next scan"
empty on a clean install.

## Install

```sh
sudo ./install.sh <your-user>
```

Read `install.sh` first. It refuses to install if a unit with the same name
already exists, and prints how to uninstall when it finishes.

## What it installs

```
/usr/local/bin/clamav-tray-daily.sh
/etc/systemd/system/clamav-tray-daily.{service,timer}
/etc/default/clamav-tray-daily          ← configuration
/var/lib/clamav-tray-daily/             ← last-scan markers (created on the 1st run)
```

## Incremental and full

There's a single timer and it runs every day; the script picks the mode:

| | When | What it scans | Duration on the origin machine |
|---|---|---|---|
| **full** | on the 1st run and when the last full scan is older than `CLAMAV_TRAY_FULL_EVERY` days (default 7) | the whole home, minus the exclusions | 4h40, 1.1 million files |
| **incremental** | on the other days | only files with a *ctime* later than the last completed scan | minutes |

To force a mode: `sudo /usr/local/bin/clamav-tray-daily.sh full` (or
`incremental`). The log and the notification say which mode ran.

**Why the full scan still exists.** The signature database changes every day. The
incremental only looks at new files; an old file that only today's signature
recognizes would be ignored forever. The full scan re-evaluates everything against the current database,
and 7 days is the exposure ceiling for that case.

**By age, not by weekday.** With `OnCalendar=Sun`, a machine turned off on
Sunday would push the full scan to the following Sunday. By measuring the age of the last one,
it runs on the first day the machine is on.

**ctime, not mtime.** The mtime is set by the user: `touch -d`, `tar x`,
`cp -p`, `wget` and `curl -R` write the source date, and a freshly downloaded file
dated 2019 would slip through a `-newer` search. Only the kernel writes the
ctime. Cost: `chmod` or `mv` also update it, and those files enter the
list without their content having changed — a small surplus next to the opposite error.
Blind spot: moving a **directory** within the same filesystem doesn't
change the ctime of the files inside it. A directory taken from an
excluded path (`.cache`, `node_modules`) and put in `Documents` is only seen on the next
full scan — at most 7 days later.

**The marker is from the start, and only counts if the scan completes.** The instant is recorded
before listing the files; whatever changes during the scan goes into the next one. If
the scan doesn't produce a `SCAN SUMMARY` (daemon died, machine shut down midway), the
previous marker stays, and the next incremental covers the whole interval.

> Upgrading from an earlier version: reinstall `clamav-tray-daily.sh`. Without
> markers in `/var/lib/clamav-tray-daily`, the first run is a full scan.

## Decisions worth knowing

**`clamdscan`, not `clamscan`.** `clamscan` reloads ~1 GB of signatures on
every run and scans single-threaded. Measured on the origin machine: more than
6 hours, with the SSD at 95% utilization and I/O pressure at 57% — the terminal even
went into D state.

**`--fdpass`.** `clamd` runs as the `clamav` user and can't read inside `/home`.
With `--fdpass` the one who opens the file is this script (root), which passes the **descriptor**
over the socket. No copy.

**`--file-list` instead of pointing at the directory.** `clamdscan` has no
`--exclude-dir`, so the exclusions are applied by `find` here.

**The verdict comes from the `SCAN SUMMARY`, not the exit code.** `clamdscan`
returns `2` if *any* file couldn't be opened, and in an hours-long scan
over a million files it's routine for temporary files to vanish midway. Treating that
as failure makes the service report an error every day with no threat at all — an alarm that
always rings stops being an alarm.

**`Nice=19` and `IOSchedulingClass=idle` don't save a saturated disk.** They're there, but
the scan that froze the origin machine ran with exactly those options. What
fixed it was switching the scanner and changing the time.
