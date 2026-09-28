# Quarentena

Há duas, com donos e regras diferentes.

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

## A varredura sob demanda

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

A quarentena do usuário é **excluída** de toda varredura da home — a dela e a do extra
`daily-scan`. Sem isso, o que já foi isolado seria reencontrado e movido de novo: a contagem no
menu esvaziaria sozinha durante a noite, com os arquivos reaparecendo na quarentena de root.

**Colisão de nome não sobrescreve.** O `clamdscan --move` acrescenta `.001`, `.002` — verificado
com o arquivo de teste EICAR: dois arquivos de mesmo nome viraram `teste.txt` e `teste.txt.001`.

**Dois vigias não brigam pelo mesmo arquivo.** Cada um tem quarentena própria. Se algo infectado
for copiado de um pendrive para Downloads, são dois arquivos, cada um na sua quarentena — o menu
refletir isso é correto, não duplicação. Numa corrida real pelo mesmo caminho, quem mover primeiro
ganha e o segundo registra `Can't access file`, que conta como ilegível e **não** como infecção.

Varredura lançada **fora** do programa — terminal, cron, outra ferramenta — também acende "em
andamento", detectada por processo. Dessas não dá para ler o resultado, mas é melhor que afirmar
calmaria enquanto o disco trabalha.
