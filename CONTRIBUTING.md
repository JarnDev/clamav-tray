# Contribuindo

Obrigado por olhar. Este é um projeto pequeno, mantido por uma pessoa, e o que
segue vale mais como expectativa honesta do que como regra.

## Antes de tudo: a branch `rust`

A `main` é a versão Python, funcional e mantida. **É contra ela que os PRs
devem ir.**

A branch `rust` é um exercício pessoal de aprendizado — pode ser reescrita à
força, rebasada ou abandonada sem aviso. Não construa nada em cima dela.

## O que ajuda mais

**Testar em outra distro.** O projeto foi escrito e usado num Ubuntu. Fedora usa
unidade *templated* (`clamd@scan.service`), Arch tem nomes próprios, e eu não
testei nenhum dos dois. Um relato com a saída de:

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

Leia [docs/dbusmenu.md](docs/dbusmenu.md). O menu **não é desenhado pelo GTK** —
ele é serializado por D-Bus e renderizado pelo shell. Widget nenhum atravessa
essa fronteira, e cinco bugs deste projeto vieram de não saber disso.

Se a sua ideia envolve um widget dentro do menu, ela provavelmente não funciona.
Se envolver negrito, cor de texto ou tooltip, ela definitivamente não funciona.

## Testes

```sh
python3 -m pytest tests/         # se tiver pytest
python3 -c "import tests.test_scan as t; [getattr(t,n)() for n in dir(t) if n.startswith('test_')]"
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
