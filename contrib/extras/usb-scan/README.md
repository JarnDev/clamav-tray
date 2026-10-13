**English** · [Português (Brasil)](README.pt-BR.md)

# usb-scan

Scans removable media as soon as it's mounted.

## Why it doesn't use `RUN+=` in udev

The udev documentation is categorical:

> *Starting daemons or other long-running processes is not allowed; the forked
> processes, detached or not, will be **unconditionally killed** after the event
> handling has finished.*

A USB stick scan lasts longer than a udev event. With `RUN+=`, it's
killed midway — and silently, which is the worst way to fail in a program whose
job is to warn.

The doc itself names the way out: **a service unit pulled in by the device**.
That's what the rule does, with `TAG+="systemd"` and `ENV{SYSTEMD_WANTS}`.

Side benefit: as a unit, it **shows up in `clamav-tray`** — which discovers
by unit and can't see a loose process.

## The `%k` trap

udev hands over the partition's **kernel name** (`sdc1`), not the mount point.
And it fires on the `add` event, which happens **before** the automount finishes.

A script that expects to receive a ready directory gets `sdc1` and aborts on the
third line. Here the script resolves it, with `findmnt`, waiting up to 30 s
for the mount.

If it doesn't mount within that time, it exits with **0** — it isn't a failure: it may be a system
partition, swap, or the user simply didn't open the media.

## Install

```sh
sudo ./install.sh <your-user>
```

The installer **asks first**, because this extra is the only one that acts on its own in
response to hardware: plugging in a 2 TB external drive triggers a long scan
you didn't ask for.

To stop one in progress:

```sh
systemctl stop 'clamav-tray-usb@*'
```

## `--multiscan`, unlike the other extras

There's no exclusion to apply here, so the directory can be scanned directly — without
`--file-list` — taking advantage of `clamd`'s threads.

The home scan uses `--file-list` because the exclusions have to be applied
by `find`; `clamdscan` has no `--exclude-dir`. This extra doesn't pay that
cost.

## Separate quarantine

`/var/quarantine/clamav-usb`, distinct from the daily scan and the Downloads
monitor. That way you can tell where the threat came in.
