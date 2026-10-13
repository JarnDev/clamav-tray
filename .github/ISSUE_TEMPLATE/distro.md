---
name: Distro report
about: I tested on another distribution
labels: distro
---

The project was written and used on Ubuntu, and Fedora and Arch were checked in
containers. A report from a real install on any distro helps even if nothing is
broken.

**Distro and version:**

**Output:**

```sh
systemctl list-units --all 'clam*'
clamconf -n | grep -E 'LocalSocket|LogFile|DatabaseDirectory'
python3 -m clamav_tray --dump
```

**Did it work?** If not, what looked wrong.

<!-- Português é bem-vindo. -->
