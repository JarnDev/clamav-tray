**English** · [Português (Brasil)](quarantine.pt-BR.md)

# Quarantine

There are two, with different owners and rules.

The path does **not** come from `clamconf`: quarantine is born from the `--move=` of whoever scheduled
the scan, not from ClamAV's configuration, and there's no default path in the specification. The program
looks in the places that show up in practice:

```
/var/quarantine/clamav
/var/lib/clamav/quarantine
/var/spool/clamav/quarantine
```

Outside those, use `paths.quarantine` in the configuration file.

### Why it usually says "needs root to list"

```
⚪ Quarantine   needs root to list
    /var/quarantine/clamav
```

Quarantine is normally `750` owned by `root`, and that is **right** — it's stored malware. Not
being able to count is the common case, not a configuration error.

That's why the program distinguishes *don't know* from *empty*: without permission it says it needs root,
instead of showing "empty" and conveying a reassurance it didn't measure.

### Why the action opens a terminal, not the file manager

Two reasons, both practical:

1. `xdg-open` on a root `750` folder returns "permission denied" in a window, without explaining
   why. In the terminal, `sudo` asks for the password and it's clear what's happening.
2. **There's real malware in there.** A file manager generates thumbnails, indexes and reads
   headers of the files it displays — touching a malicious executable with the thumbnailer is a
   bad way to look at it. `ls` opens nothing.

If you want to read it without `sudo`, you can change the directory's group. That's weakening a deliberate
permission; know that you're doing it.

## The on-demand scan

The button launches the scan as a **transient user unit** (`systemd-run --user`), not as a
loose command. Without that the indicator would be blind to the scan it started itself: it wouldn't
show "in progress" and would lose the result, because the output would go to the screen and not anywhere
that could be read again.

It doesn't need root: with `--fdpass` the one who opens the files is you, and `clamd` reads through the descriptor.

### It DETECTS, it doesn't quarantine

Running as you, the on-demand scan can't write to a root `750` quarantine —
and that permission is right. So `--move` is only passed when you can actually write there;
otherwise the scan only **points out** what it found.

Passing `--move` without permission doesn't degrade gracefully: `clamdscan` **aborts before looking at a
single file**, with `Failed to create quarantine lock file ... Permission denied` and status 2.
Measured: a 771 MB scan "finished" in 0.000 s.

### Where the on-demand scan puts what it finds

In a quarantine of **yours**, at `~/.local/share/clamav-tray/quarantine` (mode `0700`), created only
when it's used.

This weakens nothing: the file was already in your home, with your permissions. Moving it
there doesn't raise privilege — it **reduces exposure**, because it leaves the place where it could be opened
by mistake and goes to a directory that no program scans, indexes or thumbnails.

The **system** quarantine still belongs to the scheduled scan, which runs as root.

The user quarantine is **excluded** from every home scan — its own and the `daily-scan`
extra's. Without that, what was already isolated would be found again and moved again: the count in the
menu would empty itself overnight, with the files reappearing in root's quarantine.

**Name collisions don't overwrite.** `clamdscan --move` appends `.001`, `.002` — verified
with the EICAR test file: two files with the same name became `teste.txt` and `teste.txt.001`.

**Two watchers don't fight over the same file.** Each has its own quarantine. If something infected
is copied from a USB stick to Downloads, those are two files, each in its own quarantine — the menu
reflecting that is correct, not duplication. In a real race for the same path, whoever moves first
wins and the second logs `Can't access file`, which counts as unreadable and **not** as an infection.

A scan launched **outside** the program — terminal, cron, another tool — also lights up "in
progress", detected by process. Its result can't be read, but that's better than claiming
calm while the disk works.
