[English](ROADMAP.md) · **Português (Brasil)**

# Roadmap

Duas trilhas independentes. A de produto entrega valor a quem instala; a de aprendizado existe
para mim. **A segunda nunca atrasa nem degrada a primeira.**

---

# Trilha 1 — o produto (Python, branch `main`)

Os números abaixo são os do [CHANGELOG](CHANGELOG.md) e do PyPI. Versão futura é intenção, não
promessa: item sobe ou desce conforme o uso real mostrar.

## v0.1 — a base (25/09/2026)

- [x] Estado das unidades, detectadas pelo glob `clam*`
- [x] Distinção **daemon** × **tarefa** pelo `Type=` da unidade
      (`simple` = rodando é saudável; `oneshot` = rodando é *em execução*)
- [x] Resultado da última varredura, lido do `SCAN SUMMARY` do próprio clamdscan
- [x] Varredura sob demanda (home e mídia removível) como unidade transitória
- [x] Ícone reflete o estado; caminhos vindos do `clamconf`
- [x] Config TOML (`~/.config/clamav-tray/config.toml`)
- [x] Traduções, com inglês como fonte e pt_BR completo
- [x] Duas quarentenas com donos distintos, e mídia removível detectada sem subprocesso
- [x] Extras opcionais em `contrib/extras/` e autostart por serviço de usuário

## v0.2 — primeira publicada (13/10/2026)

- [x] No PyPI: `pipx install --system-site-packages clamav-tray`
- [x] Barra de progresso por **contagem** de arquivos, legível no tamanho real
- [x] Alarme escolhe a varredura pela data, não pelo barramento
- [x] `daily-scan` incremental (por ctime) todo dia, completa a cada 7
- [x] Sem PyGObject, o programa diz como corrigir em vez de despejar traceback
- [x] `scripts/release.sh`: lançamento em um comando, publicação com aprovação manual

## v0.3 — arestas que o empacotamento expôs

Quem instala pelo PyPI tem uma experiência pior que quem clona. Fechar essa diferença vem antes
de qualquer recurso novo.

- [x] **Autostart sem clonar.** `clamav-tray --install-autostart`, com os modelos dentro do
      pacote e a mesma conferência de `is-active` do script — e `--show-autostart` para
      inspecionar destino e conteúdo antes de permitir.
- [x] **Sem tela, mensagem em vez de core dump.** O GTK abortava sem `DISPLAY`; agora
      `Gtk.init_check()` é conferido antes, cobrindo também `DISPLAY` que aponta para o nada.
- [x] **`--dump --json`**, saída estável para script e para o Glance/Conky. É também o contrato
      que o `clamav-status` da Trilha 2 vai cumprir — escrevê-lo em Python primeiro fixa o formato.
- [x] **Notificação ao terminar a varredura sob demanda**, pelo próprio tray, via D-Bus e sem
      dependência nova — distinguindo ameaça isolada de ameaça encontrada e não isolada.
- [x] **Validar Fedora e Arch.** Em containers com systemd: a descoberta acha `clamd@scan`
      (Fedora) e `clamav-daemon` (Arch), o `clamconf` dá os caminhos certos nos dois. E mostrou
      um bug: sem serviço nenhum, o tray dizia "Protegido" — corrigido.

## v0.4 — documentação em dois idiomas (13/10/2026)

- [x] Inglês por padrão, português do Brasil ao lado (`X.pt-BR.md`), conferido no CI
- [x] Números seguem o idioma da interface (`14.9 GB` / `14,9 GB`)

## v0.5 — painel GNOME (em andamento, branch `feat/gnome-extension`)

Uma extensão opcional do GNOME Shell que desenha um painel rico — barra de progresso de
verdade, cores, cartões — sobre o estado que o programa já publica. O tray continua
funcionando em qualquer desktop; a extensão só **lê e desenha**, e os botões dela chamam o
`clamav-tray`. Toda a lógica fica no Python. Só entra na `main` depois dos testes de aceite.

- [x] **F0 — prova de conceito.** Um GNOME Shell aninhado, isolado da sessão real (D-Bus,
      dconf e pastas de extensão próprios: `scripts/dev-nested-shell.sh`), carrega um botão na
      barra; três ciclos de desligar e religar não deixam nada para trás.
- [x] **F1 — lado Python.** O tray grava `state.json` em `$XDG_RUNTIME_DIR` de forma atômica a
      cada atualização; campos novos no JSON (`scan.progress`, `media`, `quarantine`) sem subir
      o schema; `--headless` (sem ícone na bandeja) e comandos de ação (`--scan-home`,
      `--stop-scan`, `--scan-device`).
- [x] **F2 — extensão só leitura.** Ícone com a cor do estado; painel com cabeçalho, serviços e
      última varredura. JSON → modelo de tela num módulo puro testado com `gjs` no CI.
- [ ] **F3 — ao vivo.** Barra de progresso real, cartões de mídia e quarentena; volta a
      consultar `--dump --json` quando o arquivo de estado envelhece.
- [ ] **F4 — ações.** Os botões do painel chamam os comandos da F1.
- [ ] **F5 — instalação e documentação.** `--show-gnome-extension` / `--install-gnome-extension`,
      inspecionar antes de permitir, como no autostart; documentação nos dois idiomas.
- [ ] **F6 — lançamento 0.5.0.** Publicar no extensions.gnome.org é decisão separada.

Só versões do GNOME realmente testadas entram no `metadata.json`: um GNOME novo desativa a
extensão em vez de quebrar a barra, e o tray normal assume.

## v0.6 — extras

- [ ] `daily-scan`: modo **sistema inteiro** opcional, além da home, com exclusões próprias
      (`/proc`, `/sys`, `/var/lib/docker`, snaps, modelos de IA). Exige pensar no custo: a
      completa da home sozinha já leva horas num SSD SATA.
- [ ] `daily-scan`: a completa semanal com **notificação só quando algo muda**, para que o
      alarme diário não vire ruído.
- [ ] Teste automatizado dos scripts de `contrib/` (hoje: só `bash -n` no CI e teste manual
      contra o clamd real).

## Distribuição — por demanda, não por data

O PyPI cobre quem tem pipx. Pacote de distro é trabalho recorrente (um build por versão de
distro, assinatura, revisão), e só se paga com gente usando.

| Canal | Quando | Por quê nessa ordem |
|---|---|---|
| **AUR** | primeiro pedido de usuário Arch | um `PKGBUILD`; o mais barato de manter |
| **`.deb` / PPA** | uso real recorrente no Debian/Ubuntu | resolve as dependências do apt num passo, mas é o mais caro |
| **Flathub** | provavelmente nunca | o sandbox briga com a premissa: ler systemd e `/proc` do host |

Os extras de `contrib/` ficam **fora** de qualquer pacote do programa: instalam unidade de sistema
como root, e o tray é instalável sem privilégio por decisão. Se um dia fizer sentido, vão num
pacote separado e opcional.

## Em aberto, sem versão — o que pedem mas eu ainda não sei se quero

- [ ] Ações de serviço (start/stop/restart) — exige polkit, e aumenta muito a superfície
- [ ] Múltiplas instâncias `clamd@` no Fedora, lado a lado
- [ ] Suporte a `clamonacc` (varredura em acesso) além de mostrar a unidade

## Fora de escopo, por decisão

Editar `clamd.conf`, agendar varredura por GUI, gerenciar quarentena com interface. Isso é o
ClamTk, e não vale reconstruir. Este projeto **observa e aciona**; não configura.

Não-systemd (OpenRC, runit, s6) fica aqui embaixo sem data: seria uma segunda camada inteira de
detecção, e o valor do projeto é exatamente a integração com systemd.

---

# Trilha 2 — aprender Rust (branch `rust`)

**Regra que governa tudo:** a `main` nunca depende desta branch. A virada de chave acontece
quando eu tiver confiança na linguagem, e não antes. Se não vier, a versão Python fica.

## Ordem de migração, e por quê

A ordem é pedagógica, não técnica. Cada etapa introduz **um** conceito novo.

| # | Módulo | O que ensina | Por que nesta posição |
|---|---|---|---|
| 1 | `scan.py` → `scan.rs` | `Result`, `?`, `Option`, enums, parsing | Entrada e saída puras: texto entra, struct sai. **Testável sem máquina rodando.** Nada de I/O, nada de posse compartilhada |
| 2 | `units.py` → `units.rs` | `std::process::Command`, structs, `HashMap` | Continua síncrono. Introduz processo externo e tratamento de erro de verdade |
| 3 | `config.py` → `config.rs` | `serde`, traits, tempos de vida | Primeira vez que o borrow checker aparece com força |
| 4 | `actions.py` → `actions.rs` | ambiente, `PathBuf`, detecção de programa | Pequeno, consolida o que veio antes |
| 5 | `tray.py` → `ksni` | async, `Arc<Mutex>`, limites `'static` | **Último de propósito.** É onde iniciante trava, e depurar bandeja é péssimo: quando não aparece, não há mensagem de erro, só ausência |

Entre a etapa 2 e a 3, o binário já é útil sozinho como `clamav-status --json`, e o tray em
Python pode passar a consumir esse JSON. É o padrão do
[ai-usagebar](https://github.com/akitaonrails/ai-usagebar): binário faz o trabalho, camada fina
desenha.

Isso significa que a migração entrega valor **no meio do caminho**, não só no fim — e que a
etapa 5 pode nunca acontecer sem que isso seja perda.

## Protocolo de validação

O mesmo que uso na trilha de C/C++: ao terminar um módulo, eu não passo adiante antes de ser
arguido sobre ele. Não vale "compilou e rodou" — o teste é explicar por que o compilador aceitou.

Para cada módulo portado:

1. Comportamento idêntico ao Python, verificado com a **mesma entrada** nos dois
2. Testes cobrindo os casos que descobri usando o Python de verdade
3. Arguição: por que esta assinatura, por que esta posse, o que o compilador impediu e o que
   eu teria errado sem ele

## Pré-requisito que assumi

Terminar ponteiros e RAII na trilha de C/C++ antes de abrir Rust. Posse e empréstimo fazem muito
mais sentido depois de gerenciar memória na mão — deixam de ser regra arbitrária e viram "o
compilador conferindo o que eu já tentava fazer certo".

## Sinais de que a virada de chave pode acontecer

Não são metas, são sintomas. Quando eu perceber que:

- leio erro do compilador e já sei o que fazer, sem procurar
- escrevo a assinatura antes do corpo, e ela costuma estar certa
- não sinto vontade de `.clone()` para fugir do problema
- consigo revisar PR em Rust de outra pessoa

Aí a branch vira `main`. Antes disso, não.
