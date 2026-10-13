**English** · [Português (Brasil)](README.pt-BR.md)

# downloads-watch

Scans every new file in the Downloads folder, the moment it finishes downloading.

## Install

```sh
sudo ./install.sh <your-user> [folder]
```

Requires `inotify-tools`. The installer checks and warns if it's missing.

## Decisions worth knowing

**`close_write` and `moved_to`, not `create`.** Scanning on `create` would catch the file
halfway. `close_write` covers the finished file; `moved_to` covers what the
browser renames from `.part`/`.crdownload` to the final name.

**`Restart=always`, not `on-failure`.** systemd considers `SIGTERM` a **clean**
stop, so `on-failure` wouldn't bring the watcher back when something killed it —
exactly the case in which you don't want to be left without a watcher.

**The `grep FOUND` reads only this run.** Reading the accumulated log, every
subsequent file would be reported as infected after the first threat ever. That
bug existed in the original version and took a while to be noticed.

**Separate quarantine** (`/var/quarantine/clamav-downloads`) from the daily scan.
That way you can tell where the threat came in.
