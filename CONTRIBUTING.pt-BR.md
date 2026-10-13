[English](CONTRIBUTING.md) · **Português (Brasil)**

# Contribuindo

Obrigado por olhar. Este é um projeto pequeno, mantido por uma pessoa, e o que
segue vale mais como expectativa honesta do que como regra.

## Antes de tudo: a branch `rust`

A `main` é a versão Python, funcional e mantida. **É contra ela que os PRs
devem ir.**

A branch `rust` é um exercício pessoal de aprendizado — pode ser reescrita à
força, rebasada ou abandonada sem aviso. Não construa nada em cima dela.

## O que ajuda mais

**Testar em outra distro.** O projeto foi escrito e usado num Ubuntu. Fedora
(unidade *templated* `clamd@scan.service`) e Arch foram conferidos em containers
com systemd, o que não é o mesmo que uso diário num desktop. Um relato com a
saída de:

```sh
systemctl list-units --all 'clam*'
clamconf -n | grep -E 'LocalSocket|LogFile'
python3 -m clamav_tray --dump
```

já vale uma issue, mesmo que nada esteja quebrado.

**Traduzir.** Copie o bloco `pt_BR` em `clamav_tray/i18n.py` e traduza. Não há
ferramenta para instalar: o catálogo é um dicionário Python, e chave sem tradução
cai no inglês em vez de quebrar.

**Relatar bandeja que não aparece.** Diga o desktop e a versão. O GNOME removeu a
bandeja na 3.26 e precisa de extensão; os outros variam.

## Antes de propor mudança na interface

Leia [docs/dbusmenu.md](docs/dbusmenu.pt-BR.md). O menu **não é desenhado pelo GTK** —
ele é serializado por D-Bus e renderizado pelo shell. Widget nenhum atravessa
essa fronteira, e cinco bugs deste projeto vieram de não saber disso.

Se a sua ideia envolve um widget dentro do menu, ela provavelmente não funciona.
Se envolver negrito, cor de texto ou tooltip, ela definitivamente não funciona.

## Testes

```sh
python3 tests/run.py                 # a suíte inteira; só biblioteca padrão
python3 scripts/check-docs-i18n.py   # docs EN e PT-BR em sincronia estrutural
```

O `tests/test_scan.py` usa **saída real de clamdscan** como amostra, não texto
inventado. Se você mexer no parser, mantenha essa propriedade: o valor do teste
está em ele ter vindo de uma máquina de verdade.

## Estilo

Não há linter configurado. O código tem uma característica deliberada que vale
respeitar: **os comentários explicam por que, não o quê**, e quase sempre
registram uma alternativa que foi tentada e falhou, ou uma medição que contrariou
a intuição.

Se você corrigir um bug, o comentário que mais ajuda é o que impede alguém de
reintroduzi-lo.

## O que provavelmente será recusado

- Instalar unidade de sistema ou pedir root na instalação. O projeto é
  instalável sem privilégio, e isso é o que o separa do ClamTk. Automação
  privilegiada vai para `contrib/extras/`, opcional.
- Agendar varredura por conta própria. O programa **observa**; quem decide o que
  varrer e quando é quem administra a máquina.
- Reimplementar o que o ClamTk já faz (editar `clamd.conf`, gerenciar quarentena
  por GUI).

## Lançar uma versão (mantenedor)

```sh
scripts/release.sh 0.3.0 --dry-run   # confere tudo e mostra as notas, sem gravar
scripts/release.sh 0.3.0             # grava commit + tag assinados e envia, perguntando antes
```

Antes de gravar qualquer coisa, o script recusa se: o número não for maior que o
atual ou já aparecer no CHANGELOG; a seção `[Unreleased]` do CHANGELOG (só em inglês) estiver vazia; a árvore
estiver suja; a `main` local divergir da `origin/main`; o CI do commit não estiver
verde; ou os testes locais falharem.

Depois ele sobe a versão no `pyproject.toml` e no `__version__`, transforma
`[Unreleased]` em `[X.Y.Z] — data` (deixando uma `[Unreleased]` vazia em cima) e
envia por **SSH** — o token HTTPS costuma não ter o escopo `workflow`. A tag
dispara o `publish.yml`, que **espera aprovação manual** no ambiente `pypi` do
GitHub antes de publicar. Publicação no PyPI não se desfaz: um número publicado
nunca mais pode ser reusado, nem depois de apagado.
