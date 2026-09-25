# clamav-tray

Indicador de bandeja para uma instalação de ClamAV gerenciada por **systemd**.
Responde, sem abrir terminal: *os serviços estão de pé, tem varredura rodando agora, e como
terminou a última?*

**Requer systemd.** Essa é a premissa, não uma limitação temporária — o valor do projeto é
justamente ler o estado das unidades. Suporte a OpenRC e similares está no [ROADMAP](ROADMAP.md),
sem data.

```
🟢 Freshclam (updates)          ← daemons: rodando = saudável
🟢 ClamAV Daemon
🟢 Download Monitor
🔍 Varredura em andamento — há 2h14      ← tarefas: rodando = em execução
⏱  Próxima: amanhã 03:01
✅ Última: hoje 07:42, limpa (4h33, 6 arquivos ilegíveis)
```

## Por que existe

O [ClamTk](https://github.com/dave-theunsub/clamtk) é a referência da categoria (436★), mas é um
scanner sob demanda: **zero** referências a systemd, **zero** a bandeja, e o último *push* de
código foi em março de 2024. Os demais projetos da busca têm 0 ou 1 estrela.

Ninguém preencheu o espaço de "meu ClamAV já roda por systemd, quero ver o estado dele".

## Estado: v0.1, em uso diário por uma pessoa

Isto nasceu de um script pessoal de 75 linhas que rodava na minha máquina. Está publicado porque
o nicho estava vazio, não porque seja maduro. Se você usar, espere arestas — e abra issue.

---

## Este projeto é também meu caderno de Rust

Decidi usar este projeto para **aprender Rust**, e a forma escolhida foi migrar **um módulo por
vez** até que não sobre Python.

**Como funciona:**

- A migração acontece em **branch separada** (`rust`), nunca na `main`
- A `main` continua sendo a versão Python, funcional e mantida
- A **virada de chave só acontece quando eu tiver confiança na linguagem** — não por prazo, não
  por metade dos módulos portados, não por vontade de anunciar. Se essa confiança não vier, a
  versão Python permanece e isso não é fracasso
- Enquanto isso, quem instala usa Python e não precisa saber de nada disso

**Por que assim:** a lógica é a mesma nas duas linguagens. Ter uma implementação Python que já
funciona e é validada pelo uso transforma o exercício em "como eu digo isto em Rust?" em vez de
"o que eu deveria fazer?". Aprende-se mais rápido quando só uma variável muda por vez.

O desenho em módulos existe por causa disso: cada arquivo tem uma fronteira clara e pode ser
portado sozinho. A ordem de migração e o motivo de cada etapa estão no [ROADMAP](ROADMAP.md).

**Se você é contribuidor:** mande PR contra a `main`, em Python. A branch `rust` é exercício
pessoal e pode ser reescrita à força a qualquer momento.

---

## Instalação

```sh
pipx install clamav-tray     # ainda não publicado — por ora, ver DEVELOPMENT.md
```

**Dependências de sistema:** `python3-gi`, GTK 3 e um dos dois AppIndicator
(`gir1.2-appindicator3-0.1` ou `gir1.2-ayatanaappindicator3-0.1` — o programa tenta os dois).

### Bandeja no seu desktop

| Desktop | Situação |
|---|---|
| KDE, XFCE, Cinnamon, MATE | nativo |
| Ubuntu | funciona (a Canonical embarca `ubuntu-appindicators`) |
| GNOME puro | **precisa de extensão** — o GNOME removeu a bandeja na 3.26 |

## Configuração

Nenhuma é obrigatória. O programa descobre sozinho:

- **unidades** — pelo glob `clam*` no systemd, o que cobre tanto `clamav-daemon.service`
  (Debian, Ubuntu, Arch) quanto `clamd@scan.service` (Fedora, que usa unidade *templated*)
- **caminhos** — perguntando ao `clamconf`, que vem do próprio ClamAV e não do empacotador

Para ajustar rótulos, acrescentar unidades ou sobrescrever caminhos, veja
`clamav-tray.example.toml`.

## Permissões

Ler estado de unidade não exige privilégio. Ler o **histórico** do journal exige estar em `adm`
ou `systemd-journal`, dependendo da distro. Sem isso o programa continua funcionando: mostra o
estado atual e omite o histórico, em vez de quebrar.

## Licença

MIT.
