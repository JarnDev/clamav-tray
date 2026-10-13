**English** · [Português (Brasil)](SECURITY.pt-BR.md)

# Security policy

## Reporting a vulnerability

Open a [security advisory](https://github.com/JarnDev/clamav-tray/security/advisories/new)
instead of a public issue.

If you prefer email, use the author's address from the commit history. I reply
when I can — it is a one-person project, with no SLA.

## Attack surface, honestly

The program runs **as a regular user**, without privilege. That limits the
damage, but not to zero. What it does that deserves attention:

**Runs `systemctl` and `journalctl`** to read state. Read only; it does not
start, stop or modify system units.

**Runs `clamdscan`** with paths coming from `/proc/mounts` and from the
configuration. Arguments are built as a list, never by shell interpolation —
except in the on-demand scan, which goes through `sh -c` to redirect the output.
There the paths are quoted with escaped single quotes.

**Opens a terminal and a file manager** with paths from the configuration. A
malicious configuration file could point somewhere else — but whoever writes it
is already you.

**Reads `/proc/mounts` and `/sys/block/*/removable`.** Read only.

**Opens no port, makes no network request, sends no telemetry.**

## What the program deliberately does NOT do

**It does not make the quarantine readable.** It is typically root's `750`, and
that is right — it is stored malware. The program reads a summary published by
whoever has the privilege, and that summary carries neither file names nor
content.

**It does not open the quarantine in the file manager.** File managers generate
thumbnails and read the headers of what they display; poking a malicious
executable with the thumbnailer is a bad way to look at it. The action lists it
with `ls` in a terminal.

**It does not scan its own quarantine.** It is excluded from home scans,
otherwise what was already isolated would be found and moved again.

## Limitation worth knowing

The program **reports**; ClamAV is what protects. A green indicator means the
services answered and the last scan found nothing — not that the machine is
clean.

And there is one case where it warns explicitly: when the media is read-only,
`clamdscan` finds the threat and **fails to isolate it**, still reporting
`Infected files: N`. The menu tells "found" apart from "isolated" precisely
because of that. See [docs/quarantine.md](docs/quarantine.md).
