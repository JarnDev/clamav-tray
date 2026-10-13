# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Adicionado

- **Pacote no PyPI** (`pipx install --system-site-packages clamav-tray`) e
  workflow que publica a cada tag `v*`, por publicação confiável (OIDC, sem token
  guardado). O workflow recusa publicar se a tag, o `pyproject.toml` e o
  `__version__` não disserem a mesma versão.
- Sem PyGObject no ambiente, o programa diz como corrigir em vez de despejar um
  traceback. Testado num Ubuntu 24.04 limpo: era o que acontecia com
  `pipx install` sem `--system-site-packages`.

### Alterado

- Links e imagens do README agora são absolutos, para renderizarem no PyPI.
- Licença no formato SPDX (PEP 639); o formato antigo vira erro no setuptools a
  partir de fev/2027.
- **`daily-scan` agora é incremental na maioria dos dias.** Varria a home inteira
  todo dia — medido, 4h40 sobre 1,1 milhão de arquivos, das 03:12 às 07:54, num
  SSD que fica inutilizável enquanto isso. Agora o mesmo timer diário varre só o
  que mudou desde a última varredura concluída (por *ctime*, que não se falsifica
  com `touch -d`), e a completa roda quando a última tem mais de 7 dias
  (`CLAMAV_TRAY_FULL_EVERY`). Detalhes e o porquê de cada escolha em
  `contrib/extras/daily-scan/README.md`. O estado fica em
  `/var/lib/clamav-tray-daily` (`CLAMAV_TRAY_DAILY_STATE` — nome distinto de
  `CLAMAV_TRAY_STATE`, que é onde o tray lê as estatísticas da quarentena).

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

- **O trilho da barra de progresso era invisível.** Ele usava `░` (U+2591, um
  quarto de cobertura): medido no tamanho real, **1,00:1** contra o fundo do
  menu — a mesma cor. Só a parte cheia aparecia, e sem o trilho não dá para
  julgar a proporção. Agora é `▒` (U+2592, metade): **1,45:1**. O teto é baixo
  porque cor não atravessa o dbusmenu (ver `docs/dbusmenu.md`), então a única
  alavanca é a densidade do glifo — `▓` foi testado e rejeitado: fica perto
  demais do cheio e a fronteira entre os dois se perde.

### Mudado

- A descoberta dos módulos de teste saiu do YAML do CI para `tests/run.py`: com
  a lista colada no workflow, um arquivo de teste novo não rodava até alguém
  lembrar de editá-lo.
- As duas imagens do README agora são **regeneráveis**:
  `docs/screenshots/make-tray-states.py` e `make-menu-states.py`. Antes o HTML
  que as produziu morava num diretório temporário, então corrigi-las significava
  refazê-las do zero. A do menu monta a barra com as constantes lidas de
  `widgets.py`, para não poder divergir do programa.
- Texto secundário e separadores dos menus com mais contraste, e o mesmo fundo
  nas duas imagens. Medido sobre o fundo do menu (`#353535`): seções de **3,63:1
  para 5,19:1**, linhas de detalhe de 5,82:1 para 6,43:1; a legenda acima de cada
  menu, sobre o fundo da página, de 5,36:1 para 7,57:1.

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
