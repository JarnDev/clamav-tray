**English** · [Português (Brasil)](json.pt-BR.md)

# `clamav-tray --dump --json`

What the tray sees, as data. It needs neither a display nor PyGObject: it's for
scripts, Glance, Conky, `jq`, monitoring.

```sh
clamav-tray --dump --json | jq -r .status          # ok | busy | warn | threat
clamav-tray --dump --json | jq '.scan.infected'
```

## Stability

It's a **contract**. The `schema` field goes up when a field changes meaning, changes
type or disappears. A **new** field doesn't bump `schema` — readers should ignore what they
don't know.

- Absence is `null`, never an omitted field.
- Timestamps in ISO 8601 **with time zone** (`2026-10-14T03:02:45-03:00`).
- The tests in `tests/test_report.py` fail if a name or type changes.

The future `clamav-status` in Rust (see the [ROADMAP](../ROADMAP.md)) will produce this
same output.

## Example

```json
{
  "schema": 1,
  "version": "0.5.0",
  "producer": "tray",
  "generated_at": "2026-10-13T18:01:42-03:00",
  "status": "ok",
  "units": [
    {
      "id": "clamav-scan.timer",
      "label": "Scan",
      "kind": "timer",
      "user_scope": false,
      "active_state": "active",
      "sub_state": "waiting",
      "result": "success",
      "healthy": true,
      "running": false,
      "exit_status": null,
      "started_at": null,
      "finished_at": null,
      "next_run": "2026-10-14T03:02:45-03:00"
    }
  ],
  "scan": {
    "unit": "clamav-scan.service",
    "running": false,
    "outside_systemd": false,
    "verdict": "clean",
    "infected": 0,
    "unreadable": 6,
    "scanned": null,
    "duration_secs": 16317,
    "finished_at": "2026-10-13T07:54:11-03:00",
    "progress": null
  },
  "media": [],
  "quarantine": {
    "system": null,
    "user": {"count": 0}
  },
  "paths": {
    "socket": "/var/run/clamav/clamd.ctl",
    "scan_log": "/var/log/clamav/scan.log",
    "daemon_log": "/var/log/clamav/clamav.log",
    "quarantine": "/var/quarantine/clamav",
    "user_quarantine": null
  }
}
```

## The state file

The running tray (also in `--headless` mode) writes this same document to
`$XDG_RUNTIME_DIR/clamav-tray/state.json` on every refresh, atomically (temporary
file + rename: a reader never sees half a file). It is what the GNOME extension
reads, at no cost: no process is spawned. `--dump --json` is the fallback when the
tray isn't running.

## Fields

**Root**

| field | type | |
|---|---|---|
| `schema` | int | version of this format |
| `version` | string | version of clamav-tray that produced it |
| `producer` | `"tray"` \| `"dump"` | `tray` = the `state.json` the running tray writes; `dump` = `--dump --json` |
| `generated_at` | string | ISO 8601. A `state.json` that stops changing means the tray stopped |
| `status` | `"ok"` \| `"busy"` \| `"warn"` \| `"threat"` | the same precedence as the icon: threat > scanning > service down > ok. **No unit found is `warn`**, not `ok` |

`status` does **not** include pending removable media: "pending" depends on what the tray
has already scanned in its session, which lives in the process's memory, not in the system.

**`units[]`** — sorted by `id`

| field | type | |
|---|---|---|
| `id` | string | systemd unit name |
| `label` | string | label shown in the menu |
| `kind` | `"daemon"` \| `"job"` \| `"timer"` | from the unit's `Type=`: `job` is what runs and finishes |
| `user_scope` | bool | unit of `systemctl --user` (the on-demand scan lives there) |
| `active_state`, `sub_state`, `result` | string | as systemd reports them |
| `healthy` | bool | a job that found a virus (exit 1) is healthy: finding is its job |
| `running` | bool | job running right now |
| `exit_status` | int \| null | |
| `started_at`, `finished_at`, `next_run` | string \| null | ISO 8601 |

**`scan`** — the last scan, from the unit the tray picks (running now >
finished last)

| field | type | |
|---|---|---|
| `unit` | string \| null | where the result came from |
| `running` | bool | |
| `outside_systemd` | bool | there's a `clamscan`/`clamdscan` running outside any unit |
| `verdict` | `"clean"` \| `"infected"` \| `"error"` \| `"unknown"` | read from the `SCAN SUMMARY`, never from the exit code. `unknown` = there was no summary — not the same as clean |
| `infected`, `unreadable` | int | |
| `scanned` | int \| null | `clamdscan` doesn't always print it |
| `duration_secs` | int \| null | |
| `finished_at` | string \| null | |
| `progress` | `{done, total}` \| null | files done / files listed, by count. Only in `state.json`: the counter lives in the tray process |

**`media[]`** — removable media mounted under the user's tree

| field | type | |
|---|---|---|
| `key` | string | `device:mountpoint`, the identity used by `--scan-device` |
| `label`, `mountpoint` | string | |
| `size_bytes` | int \| null | |
| `scanned` | `{at, infected, not_contained}` \| null | what the tray scanned **this session**; `null` = not scanned, and always `null` in `--dump` (that lives in the tray's memory). `not_contained` = found but not quarantined (read-only media) |

**`quarantine`** — `{system, user}`; each one `null` when it can't be known
(the system one belongs to root and is known only through the summary someone
privileged publishes). `system`: `{count, bytes, checked_at}`; `user`: `{count}`.

**`paths`** — `socket`, `scan_log`, `daemon_log`, `quarantine`, `user_quarantine`:
string or `null`. `daemon_log` is clamd's log, **not** the scan's.
