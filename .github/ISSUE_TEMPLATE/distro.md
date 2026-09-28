---
name: Relato de distro
about: Testei em outra distribuição
labels: distro
---

O projeto foi escrito e usado num Ubuntu. Relato de outra distro ajuda mesmo que
nada esteja quebrado.

**Distro e versão:**

**Saída:**

```sh
systemctl list-units --all 'clam*'
clamconf -n | grep -E 'LocalSocket|LogFile|DatabaseDirectory'
python3 -m clamav_tray --dump
```

**Funcionou?** Se não, o que apareceu errado.
