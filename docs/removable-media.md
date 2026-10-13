**English** · [Português (Brasil)](removable-media.pt-BR.md)

# Removable media

When you plug in a USB stick, it **shows up in the menu** and the tray icon changes — but
nothing is scanned until you click.

```
DEVICES
🟡  KINGSTON   14,9 GB · not scanned
     /media/user/KINGSTON
```

Clicking scans. While it scans, the progress bar and the "Stop scan" button
apply — the same machinery as the home scan.

### Why it doesn't scan on its own

Scanning automatically on plug-in requires a udev rule, a system unit and root — and
it acts without asking. Plugging in a 2 TB external drive would trigger a long scan
nobody asked for, and stopping it would require privilege.

Since the scan runs **as you**, none of that is needed: `udisks2` mounts the
media with your uid, so `clamdscan --fdpass` reads it without root.

Whoever wants the automatic behavior installs
[`contrib/extras/usb-scan`](../contrib/extras/usb-scan).

### How detection works

Two file reads per refresh, no subprocess:

1. `/proc/mounts` — what's mounted under `/media/$USER` or `/run/media/$USER`
2. `/sys/block/<disk>/removable` — whether the hardware is removable, according to the kernel

The path filter alone would be a proxy: it's where `udisks2` mounts, but someone
can mount a fixed disk there. Hence the cross-check with the kernel's data.

**Known limit:** media you've never opened isn't mounted, and what isn't
mounted can't be scanned by a user process. Only the extra with
root covers that case.
