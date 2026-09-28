# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

## [0.1.0] — 2026-09-25

Primeira versão pública. Nasceu de um script pessoal de 75 linhas.

### Adicionado

- Estado das unidades do ClamAV, descobertas pelo glob `clam*` — cobre
  `clamav-daemon.service` (Debian, Ubuntu, Arch) e `clamd@scan.service` (Fedora)
- Distinção **daemon × tarefa** pelo `Type=` da unidade: sem ela, um monitor de
  pasta apareceria como "varredura em andamento" eternamente
- Varredura sob demanda da home e de mídia removível, como unidade transitória
  do usuário — visível, interrompível e sem root
- Barra de progresso por **contagem** de arquivos, não estimativa por relógio
- Detecção de mídia removível por `/proc/mounts` + `/sys/block/*/removable`,
  sem subprocesso
- Duas quarentenas com donos distintos, e uma convenção para a de root publicar
  estatísticas legíveis
- Distinção entre ameaça **encontrada** e ameaça **isolada** — mídia somente
  leitura reporta a primeira sem conseguir a segunda
- Idioma configurável, com inglês como fonte
- Quatro extras opcionais em `contrib/extras/`, cada um com instalador próprio
- Autostart por serviço de usuário ou autostart XDG

### Decisões registradas

- O programa **observa**; não instala unidade nem agenda varredura. É o que o
  mantém instalável sem root.
- O veredito vem do `SCAN SUMMARY`, nunca do código de saída: o `clamdscan`
  devolve 2 se qualquer arquivo não pôde ser aberto, e isso é rotina numa
  varredura de horas.
- Encontrar vírus não é falha da unidade, e sim o trabalho dela.
- A barra é desenhada com caracteres porque widget não atravessa o dbusmenu.
  Ver [docs/dbusmenu.md](docs/dbusmenu.md).
