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

## O que funciona numa instalação limpa

O programa **observa** o que existe. Ele não instala unidade, não agenda varredura
e não decide o que varrer — é essa escolha que o mantém instalável sem root.

Consequência honesta, medida num Ubuntu com `clamav-daemon` e `clamav-freshclam`:

| | De fábrica |
|---|---|
| ClamAV Daemon, Freshclam, On-Access | **sim**, vêm nos pacotes |
| Varrer minha home agora | **sim**, precisa só do `clamd` no ar |
| Quarentena do usuário | **sim**, criada sob demanda |
| Barra de progresso | **sim**, é da varredura sob demanda |
| Varredura agendada, "Próxima", "Última" | **não** — nenhuma distro entrega |
| Monitor de pasta | **não** |
| Quarentena do sistema | **não** — nasce do `--move=` de quem agendou |

Metade de cima funciona; a metade da varredura fica vazia. Não é bug: a distro não
agenda varredura, e o programa não deve inventar uma.

Para preencher, há extras **opcionais e independentes** em [`contrib/extras/`](contrib/extras),
cada um com instalador próprio — varredura diária, monitor de Downloads e
publicação das estatísticas de quarentena. Instale só o que quiser, ou use como
referência para escrever o seu.

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

## Idioma

**Inglês é o padrão.** As strings no código são as inglesas, e traduzir é opcional
por construção: uma chave sem tradução aparece em inglês em vez de quebrar.

```toml
[general]
language = "pt_BR"   # ou "auto" para seguir o locale do sistema
```

Traduções vivem em `clamav_tray/i18n.py`, num dicionário. Não usa gettext de propósito:
compilar `.po` em `.mo` acrescentaria um passo de build a um projeto que hoje instala com
`pipx install` e nada mais. Para contribuir com um idioma, copie o bloco `pt_BR` e traduza —
sem instalar ferramenta nenhuma. As chaves já são as frases em inglês, então migrar para
gettext depois é mecânico.

## Configuração

Há um item **Settings** no menu: ele cria o arquivo comentado se não existir e abre no seu
editor. O arquivo é **relido sozinho ao salvar** — sem reiniciar.

Não há diálogo de preferências em GTK de propósito: seria mais código que o resto do programa
junto, para uma edição que acontece raramente.

Nenhuma configuração é obrigatória. O programa descobre sozinho:

- **unidades** — pelo glob `clam*` no systemd, o que cobre tanto `clamav-daemon.service`
  (Debian, Ubuntu, Arch) quanto `clamd@scan.service` (Fedora, que usa unidade *templated*)
- **caminhos** — perguntando ao `clamconf`, que vem do próprio ClamAV e não do empacotador

Para ajustar rótulos, acrescentar unidades ou sobrescrever caminhos, veja
`clamav-tray.example.toml`.

## Quarentena

O caminho **não** vem do `clamconf`: quarentena nasce do `--move=` de quem agendou a varredura,
não da configuração do ClamAV, e não há caminho padrão na especificação. O programa procura nos
lugares que aparecem na prática:

```
/var/quarantine/clamav
/var/lib/clamav/quarantine
/var/spool/clamav/quarantine
```

Fora desses, use `paths.quarantine` no arquivo de configuração.

### Por que ela costuma dizer "precisa de root para listar"

```
⚪ Quarentena   precisa de root para listar
    /var/quarantine/clamav
```

Quarentena é normalmente `750` com dono `root`, e isso está **certo** — é malware guardado. Não
conseguir contar é o caso comum, não um erro de configuração.

Por isso o programa distingue *não sei* de *vazia*: sem permissão ele diz que precisa de root, em
vez de mostrar "vazia" e passar uma tranquilidade que não mediu.

### Por que a ação abre um terminal, não o gerenciador de arquivos

Duas razões, ambas práticas:

1. `xdg-open` numa pasta `750` de root devolve "permission denied" numa janela, sem explicar o
   motivo. No terminal o `sudo` pergunta a senha e fica claro o que está acontecendo.
2. **Ali dentro há malware de verdade.** Gerenciador de arquivos gera miniatura, indexa e lê
   cabeçalho dos arquivos que exibe — encostar num executável malicioso com o thumbnailer é um
   jeito ruim de olhar para ele. `ls` não abre nada.

Se quiser ler sem `sudo`, dá para mudar o grupo do diretório. É enfraquecer uma permissão
deliberada; saiba que está fazendo isso.

## Varredura sob demanda

O botão lança a varredura como **unidade transitória do usuário** (`systemd-run --user`), não como
comando solto. Sem isso o indicador ficaria cego para a varredura que ele mesmo iniciou: não
mostraria "em andamento" e perderia o resultado, porque a saída iria para a tela e não para lugar
nenhum que desse para reler.

Não precisa de root: com `--fdpass` quem abre os arquivos é você, e o `clamd` lê pelo descritor.

### Ela DETECTA, não põe em quarentena

Rodando como você, a varredura sob demanda não consegue escrever numa quarentena `750` de root —
e essa permissão está certa. Então o `--move` só é passado quando você de fato pode escrever lá;
caso contrário a varredura apenas **aponta** o que achou.

Passar `--move` sem permissão não degrada com elegância: o `clamdscan` **aborta antes de olhar um
único arquivo**, com `Failed to create quarantine lock file ... Permission denied` e status 2.
Medido: uma varredura de 771 MB "terminou" em 0,000 s.

### Onde a sob demanda põe o que encontra

Numa quarentena **sua**, em `~/.local/share/clamav-tray/quarantine` (modo `0700`), criada só
quando for usada.

Isso não enfraquece nada: o arquivo já estava na sua home, com as suas permissões. Movê-lo para
ali não aumenta privilégio — **diminui exposição**, porque sai do lugar onde poderia ser aberto
por engano e vai para um diretório que nenhum programa varre, indexa ou gera miniatura.

A quarentena do **sistema** continua sendo da varredura agendada, que roda como root.

**Limitação conhecida:** varrendo a home inteira, a quarentena do usuário está dentro do alvo.
Arquivos já isolados são varridos de novo a cada execução. Não incomoda enquanto ela está vazia,
que é o caso normal.

Varredura lançada **fora** do programa — terminal, cron, outra ferramenta — também acende "em
andamento", detectada por processo. Dessas não dá para ler o resultado, mas é melhor que afirmar
calmaria enquanto o disco trabalha.

## Barra de progresso

É **contagem**, não estimativa por relógio. Com `--file-list` o `clamdscan` imprime uma linha por
arquivo, então:

```
progresso = linhas impressas / linhas da lista
```

Por isso a varredura sob demanda monta a própria lista antes de começar. Custo medido:
**4.500.726 arquivos listados em 10 s** — irrelevante diante de uma varredura de horas. E de
brinde vêm as exclusões (cache, `node_modules`, Steam, perfis de navegador): de 4,5 milhões de
arquivos para 1,13 milhão.

Duas consequências que não são óbvias:

- **`-i` some quando há lista.** `-i` (`--infected`) imprime só os infectados, que é o que se quer
  normalmente — e é o que torna o progresso incontável. Com lista, a saída passa a ter uma linha
  por arquivo (~70 MB para 1,1 milhão). Fica em `tmpfs`, some no logout, e é lida uma vez, de
  forma incremental: só os bytes novos a cada atualização.
- **Não há previsão de término.** A velocidade varia demais com o tamanho dos arquivos —
  extrapolar minutos de amostra dá números sem sentido. A porcentagem é honesta; um "faltam 3h"
  não seria.

### A varredura agendada pulsa, não preenche

Ela roda como **root** e manda a saída para um arquivo temporário de nome aleatório. Espiar pelo
`/proc/<pid>/fd/1` dela não funciona — `Permission denied`, verificado. Um indicador de usuário
não vê dentro de um processo de root, e essa fronteira está certa.

Existe uma **convenção** para quem quiser: se houver um `scan.progress` legível ao lado do log,
com `feitos/total` numa linha, o tray usa.

```
/var/log/clamav/scan.progress     412391/1099137
```

Mas há um custo honesto: para contar, o script agendado também precisaria abrir mão do `-i`. Sem
isso não há o que contar. Enquanto ninguém publicar o contador, a barra da agendada **pulsa** — diz
"está viva" sem afirmar quanto falta.

## Permissões

Ler estado de unidade não exige privilégio. Ler o **histórico** do journal exige estar em `adm`
ou `systemd-journal`, dependendo da distro. Sem isso o programa continua funcionando: mostra o
estado atual e omite o histórico, em vez de quebrar.

## Licença

MIT.
