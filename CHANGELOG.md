# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Corrigido

- **O alarme escolhia a varredura pelo barramento, não pela data.**
  `pick_scan_unit` preferia a unidade do usuário incondicionalmente, e a unidade
  transitória permanece após terminar (`--remain-after-exit`, que é o que guarda
  o resultado). Consequência: uma ameaça encontrada sob demanda continuava
  acendendo o ícone dias depois, e as varreduras agendadas limpas no meio nunca
  chegavam a ser lidas — a escolha da unidade acontece antes da leitura do
  resumo. A ordem agora é: rodando agora > terminou por último > sob demanda como
  desempate.
- A varredura sob demanda **esvazia o arquivo de saída antes de disparar**. O
  redirecionamento do shell só trunca quando o shell roda; até lá — e para
  sempre, se o lançamento falhasse — o arquivo ainda respondia com o resumo da
  varredura anterior.
- O instalador de autostart afirmava "Ativado" enquanto o serviço falhava em
  laço: a unidade tinha `ExecStart` fixo em `~/.local/bin/clamav-tray`, que não
  existe em instalação a partir do código. Agora ele resolve o executável, recusa
  se não houver como executar, e confere `is-active` depois de habilitar.

- **A faixa de estados do ícone era ilegível.** Os símbolicos do Adwaita trazem
  `fill="#2e3436"` embutido no `<path>`, que vence o `currentColor` do `<svg>`. O
  GTK ignora esse atributo e recolore o ícone; um navegador não. Como a imagem é
  renderizada no Chrome, os cinco ícones saíam azul-escuro sobre pílula
  cinza-escura — medido, **1,16:1**, contra o mínimo de 3:1 da WCAG para elemento
  gráfico. Agora o atributo é removido antes da renderização e os ícones saem na
  cor de primeiro plano do painel: **19:1**.

### Mudado

- A descoberta dos módulos de teste saiu do YAML do CI para `tests/run.py`: com
  a lista colada no workflow, um arquivo de teste novo não rodava até alguém
  lembrar de editá-lo.
- A faixa de estados do ícone agora é **regenerável**:
  `docs/screenshots/make-tray-states.py`. Antes o HTML que a produziu morava num
  diretório temporário, então corrigi-la significava refazê-la do zero.

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
