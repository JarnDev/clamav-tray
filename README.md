# clamav-tray

Indicador de bandeja para uma instalação de ClamAV gerenciada por **systemd**.
Responde, sem abrir terminal: *os serviços estão de pé, tem varredura rodando
agora, e como terminou a última?*

![Estados do ícone na bandeja](https://raw.githubusercontent.com/JarnDev/clamav-tray/main/docs/screenshots/tray-states.png)

Um clique abre o estado completo — serviços, varredura, mídia removível e
quarentena:

![Estados do menu](https://raw.githubusercontent.com/JarnDev/clamav-tray/main/docs/screenshots/menu-states.png)

> As imagens são renderizações fiéis, montadas a partir da estrutura que o
> próprio programa produz, com os SVGs do tema Adwaita. Os ícones aparecem
> **brancos** porque é assim que são de fato: o indicador pede um ícone pelo
> nome (`security-high-symbolic`) e quem pinta é o shell, com a cor de primeiro
> plano do painel — o que distingue um estado do outro é a forma e o rótulo ao
> lado, não a cor. A barra de progresso usa as constantes do próprio
> `widgets.py`, lidas do código, para a imagem não poder divergir do programa.
> As duas são regeneráveis: `python3 docs/screenshots/make-tray-states.py` e
> `make-menu-states.py`.

## Por que existe

O [ClamTk](https://github.com/dave-theunsub/clamtk) é a referência da categoria
(436★), mas é um scanner sob demanda: **zero** referências a systemd, **zero** a
bandeja, e o último *push* de código foi em março de 2024. Os demais projetos da
busca têm 0 ou 1 estrela.

Ninguém preencheu o espaço de *"meu ClamAV já roda por systemd, quero ver o
estado dele"*.

**Requer systemd.** É a premissa, não uma limitação temporária — o valor do
projeto é justamente ler o estado das unidades.

## Instalação

```sh
# 1. dependências de sistema — escolha a sua distro
sudo apt install python3-gi gir1.2-ayatanaappindicator3-0.1 pipx                  # Debian/Ubuntu
sudo dnf install python3-gobject gtk3 libayatana-appindicator-gtk3 pipx            # Fedora
sudo pacman -S python-gobject gtk3 libayatana-appindicator python-pipx             # Arch

# 2. o programa
pipx install --system-site-packages clamav-tray
```

Os três comandos foram conferidos em containers limpos (Ubuntu 24.04, Fedora e
Arch atuais), instalando o pacote. No Fedora e no Arch o container rodava o
systemd, e a descoberta das unidades foi conferida ao vivo; no Ubuntu, ela é a
de uso diário na máquina de origem.

**`--system-site-packages` é obrigatório.** O PyGObject (`gi`) vem da distro, não
do pip — compilá-lo num virtualenv exige toolchain e os cabeçalhos do GTK. Sem a
flag, o venv do pipx não enxerga o `python3-gi` do sistema; o programa detecta
isso e diz como corrigir.

**Dependências de sistema:** `python3-gi`, GTK 3 e um dos dois AppIndicator
(`gir1.2-ayatanaappindicator3-0.1` ou `gir1.2-appindicator3-0.1` — o programa
tenta os dois).

Do código-fonte: clone e `pipx install --system-site-packages .`

### Antes: o ClamAV precisa estar no ar

O tray **observa** as unidades do ClamAV; não as cria. Se nenhuma for encontrada,
ele diz isso ("nenhum serviço do ClamAV encontrado") em vez de mostrar o escudo
verde. Duas armadilhas conferidas:

- **Fedora** não habilita nada, e o `/etc/clamd.d/scan.conf` vem com o
  `LocalSocket` **comentado**. Descomente `LocalSocket` (e `LogFile`, se quiser o
  log), rode `sudo freshclam` e então `sudo systemctl enable --now clamd@scan`.
- **Arch** (e o pacote upstream): o `clamav-daemon.service` tem
  `ConditionPathExistsGlob` para a base de assinaturas. Sem `sudo freshclam`
  antes, a unidade "inicia" sem erro, fica inativa e some da lista do systemd.
  Rode `freshclam` primeiro, depois `sudo systemctl enable --now clamav-daemon`.

### Subir sozinho no login

Um programa que se registra para rodar a cada login pede confiança. Por isso o
primeiro passo é **olhar**, não instalar:

```sh
clamav-tray --show-autostart          # mostra destino, comando e conteúdo exato — não grava nada
clamav-tray --show-autostart --xdg    # o mesmo, para o autostart XDG
```

Ele mostra onde o arquivo seria gravado, que comando rodaria a cada login, o
arquivo inteiro e os comandos `systemctl --user` que viriam depois. Se já existe
um arquivo no destino — seu, de outra versão, ou editado à mão —, mostra a
**diferença** linha a linha em vez do arquivo inteiro.

Conferido, instale:

```sh
clamav-tray --install-autostart           # serviço de usuário, supervisionado (recomendado)
clamav-tray --install-autostart --xdg     # autostart XDG, sem supervisão
clamav-tray --uninstall-autostart         # desfaz (com --xdg, o XDG)
```

O `--install-autostart` mostra **de novo** o mesmo conteúdo e só grava depois de
você responder `s`. Fora de um terminal ele recusa, a menos que receba `--yes` —
assim nenhum script grava autostart sem que alguém tenha decidido isso. A remoção
segue a mesma regra.

Nada disso precisa de root: o serviço vai para `~/.config/systemd/user/` e o XDG
para `~/.config/autostart/`. Prefira o serviço: se o processo morrer, ele volta, e
o journal guarda o motivo. O autostart XDG dispara e esquece — foi assim que o
indicador que deu origem a este projeto sumiu da bandeja sem deixar rastro.

Depois de gravar, o instalador **confere** que o serviço subiu, em vez de afirmar
"ativado" sem olhar. Rodando do código-fonte (sem `clamav-tray` no PATH), ele
aponta a unidade para `python3 -m clamav_tray` neste diretório — e o
`--show-autostart` diz isso antes. Quem clonou pode usar também
`./packaging/install-autostart.sh [xdg]`, que encaminha para o mesmo comando.

Os [extras](https://github.com/JarnDev/clamav-tray/tree/main/contrib/extras)
(varredura agendada, USB, Downloads) continuam só no repositório: instalam unidade
de **sistema** e pedem root, o que o pacote não faz por decisão.

### Bandeja no seu desktop

| Desktop | Situação |
|---|---|
| KDE, XFCE, Cinnamon, MATE | nativo |
| Ubuntu | funciona (a Canonical embarca `ubuntu-appindicators`) |
| GNOME puro | **precisa de extensão** — o GNOME removeu a bandeja na 3.26 |

## O que funciona numa instalação limpa

O programa **observa** o que existe. Não instala unidade, não agenda varredura e
não decide o que varrer — é essa escolha que o mantém instalável sem root.

| | De fábrica |
|---|---|
| ClamAV Daemon, Freshclam, On-Access | **sim**, vêm nos pacotes |
| Varrer a home, varrer mídia removível | **sim**, precisa só do `clamd` no ar |
| Quarentena do usuário, barra de progresso | **sim** |
| Varredura agendada, "Próxima", "Última" | **não** — nenhuma distro entrega |
| Monitor de pasta, quarentena do sistema | **não** |

Metade de cima funciona; a metade da varredura nasce vazia. Não é bug: a distro
não agenda varredura, e o programa não deve inventar uma.

Para preencher, há extras **opcionais e independentes** em
[`contrib/extras/`](https://github.com/JarnDev/clamav-tray/tree/main/contrib/extras) — varredura diária, monitor de Downloads,
varredura de USB e publicação das estatísticas de quarentena. Cada um com
instalador próprio, que recusa sobrescrever e diz como desinstalar.

## Configuração

Há um item **Configurações** no menu: ele cria o arquivo comentado se não existir
e abre no seu editor. O arquivo é **relido sozinho ao salvar**.

Nada é obrigatório — o programa descobre as unidades pelo glob `clam*` e os
caminhos pelo `clamconf`.

## Para scripts e painéis

```sh
clamav-tray --dump            # o que o tray veria, em texto
clamav-tray --dump --json     # o mesmo, como dado — formato estável
clamav-tray --dump --json | jq -r .status    # ok | busy | warn | threat
```

Não precisa de tela nem de PyGObject. O JSON é um contrato versionado (campo
`schema`), descrito em [docs/json.md](https://github.com/JarnDev/clamav-tray/blob/main/docs/json.md).

## Idioma

**Inglês é o padrão e a fonte.** Traduzir é opcional por construção: chave sem
tradução aparece em inglês em vez de quebrar.

```toml
[general]
language = "pt_BR"   # ou "auto" para seguir o locale
```

Para contribuir com um idioma, copie o bloco `pt_BR` em
[`clamav_tray/i18n.py`](https://github.com/JarnDev/clamav-tray/blob/main/clamav_tray/i18n.py) e traduza — sem instalar ferramenta
nenhuma. Não usa gettext de propósito; o porquê está em
[docs/design.md](https://github.com/JarnDev/clamav-tray/blob/main/docs/design.md).

## Documentação

| | |
|---|---|
| [docs/design.md](https://github.com/JarnDev/clamav-tray/blob/main/docs/design.md) | decisões de desenho e o que elas custaram |
| [docs/dbusmenu.md](https://github.com/JarnDev/clamav-tray/blob/main/docs/dbusmenu.md) | o que atravessa o protocolo do menu, e o que não |
| [docs/quarantine.md](https://github.com/JarnDev/clamav-tray/blob/main/docs/quarantine.md) | as duas quarentenas e a convenção de estatísticas |
| [docs/progress.md](https://github.com/JarnDev/clamav-tray/blob/main/docs/progress.md) | progresso por contagem, não por relógio |
| [docs/json.md](https://github.com/JarnDev/clamav-tray/blob/main/docs/json.md) | o formato do `--dump --json` e o que é estável nele |
| [docs/removable-media.md](https://github.com/JarnDev/clamav-tray/blob/main/docs/removable-media.md) | detecção sem subprocesso |
| [ROADMAP.md](https://github.com/JarnDev/clamav-tray/blob/main/ROADMAP.md) | o produto, e a migração para Rust |
| [CONTRIBUTING.md](https://github.com/JarnDev/clamav-tray/blob/main/CONTRIBUTING.md) | como contribuir |

---

## Este projeto é também meu caderno de Rust

Decidi usar este projeto para **aprender Rust**, migrando **um módulo por vez**
até que não sobre Python.

- A migração acontece em **branch separada** (`rust`), nunca na `main`
- A `main` continua sendo a versão Python, funcional e mantida
- A **virada de chave só acontece quando eu tiver confiança na linguagem** — não
  por prazo, não por metade dos módulos portados. Se essa confiança não vier, a
  versão Python permanece e isso não é fracasso
- Quem instala usa Python e não precisa saber de nada disso

O desenho em módulos existe por causa disso: cada arquivo tem uma fronteira clara
e pode ser portado sozinho. A ordem e o critério estão no [ROADMAP](https://github.com/JarnDev/clamav-tray/blob/main/ROADMAP.md).

**Se você é contribuidor:** mande PR contra a `main`, em Python. A branch `rust`
é exercício pessoal e pode ser reescrita à força a qualquer momento.

## Estado

v0.1, em uso diário por uma pessoa. Publicado porque o nicho estava vazio, não
porque seja maduro. Se você usar, espere arestas — e abra issue.

## Licença

MIT.
