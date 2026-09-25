# Roadmap

Duas trilhas independentes. A de produto entrega valor a quem instala; a de aprendizado existe
para mim. **A segunda nunca atrasa nem degrada a primeira.**

---

# Trilha 1 — o produto (Python, branch `main`)

## v0.1 — o que existe

- [x] Estado das unidades, detectadas pelo glob `clam*`
- [x] Distinção **daemon** × **tarefa** pelo `Type=` da unidade
      (`simple` = rodando é saudável; `oneshot` = rodando é *em execução*)
- [x] Varredura em andamento, com tempo decorrido
- [x] Resultado da última varredura, lido do `SCAN SUMMARY` do próprio clamdscan
- [x] Ícone reflete o estado
- [x] Ações: varredura sob demanda, abrir quarentena, ver logs
- [x] Caminhos vindos do `clamconf`

## v0.2 — arestas conhecidas

- [ ] Config TOML de verdade (hoje só há o exemplo)
- [ ] Notificação ao terminar uma varredura, não só no menu
- [ ] Ícone com badge de progresso quando dá para estimar
- [ ] Traduções — o projeto nasceu em português e está em inglês na interface

## v0.3 — o que pedem mas eu ainda não sei se quero

- [ ] Ações de serviço (start/stop/restart) — exige polkit, e aumenta muito a superfície
- [ ] Múltiplas instâncias `clamd@` no Fedora, lado a lado
- [ ] Suporte a `clamonacc` (varredura em acesso)

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
