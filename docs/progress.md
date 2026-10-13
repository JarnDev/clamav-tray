**English** · [Português (Brasil)](progress.pt-BR.md)

# Progress bar

It's a **count**, not a clock-based estimate. With `--file-list`, `clamdscan` prints one line per
file, so:

```
progress = printed lines / lines in the list
```

That's why the on-demand scan builds its own list before starting. Measured cost:
**4,500,726 files listed in 10 s** — irrelevant next to a scan that takes hours. And the
exclusions come as a bonus (cache, `node_modules`, Steam, browser profiles): from 4.5 million
files down to 1.13 million.

Two consequences that aren't obvious:

- **`-i` goes away when there's a list.** `-i` (`--infected`) prints only the infected files, which is
  what you normally want — and it's what makes progress uncountable. With a list, the output has one line
  per file (~70 MB for 1.1 million). It lives in `tmpfs`, disappears at logout, and is read once,
  incrementally: only the new bytes on each refresh.
- **There's no completion estimate.** Speed varies too much with file size —
  extrapolating from minutes of sample gives meaningless numbers. The percentage is honest; a "3h left"
  wouldn't be.

### The scheduled scan pulses, it doesn't fill

It runs as **root** and sends its output to a temporary file with a random name. Peeking through its
`/proc/<pid>/fd/1` doesn't work — `Permission denied`, verified. A user indicator can't see inside a
root process, and that boundary is right.

There's a **convention** for whoever wants it: if there's a readable `scan.progress` next to the log,
with `done/total` on one line, the tray uses it.

```
/var/log/clamav/scan.progress     412391/1099137
```

But there's an honest cost: to count, the scheduled script would also have to give up `-i`. Without
that there's nothing to count. Until someone publishes the counter, the scheduled scan's bar **pulses** —
it says "it's alive" without claiming how much is left.
