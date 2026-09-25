# quarantine-stats

Publica um resumo da quarentena de root num arquivo legível, para o `clamav-tray`
poder mostrá-lo.

## Por que é necessário

A quarentena do sistema é tipicamente `750` com dono `root`, e isso está **certo**
— é malware guardado. Um indicador de bandeja roda como usuário e não consegue
nem *contar* o que há lá dentro.

Não há truque de permissão que resolva: `0751` permitiria abrir um arquivo de nome
conhecido, mas não listar. Alguém com privilégio precisa escrever o resumo.

## Instalar

```sh
sudo ./install.sh [/caminho/da/quarentena]
```

Sem argumento, procura nos caminhos usuais.

## O que é publicado

```
/var/lib/clamav-tray/quarantine.stats

path=/var/quarantine/clamav
count=5
bytes=14722957
newest=2026-09-22T15:00:11+00:00
checked=2026-09-25T20:52:42+00:00
```

**Nada sensível:** quantidade, tamanho somado e datas. Nenhum nome de arquivo,
nenhum conteúdo.

## Decisões que valem saber

**Ignora as travas do `clamdscan`.** Ele cria uma `.clamav-quarantine-lock.<pid>`
por execução e não a remove quando a varredura é interrompida. Contá-las
transformaria o indicador em alarme falso — medido: seis travas viraram
"6 arquivos" no menu, sem nenhuma detecção ter acontecido.

**Troca atômica** (`mktemp` + `mv -f`). O tray pode estar lendo naquele instante,
e um arquivo pela metade viraria contagem errada em vez de erro de leitura.

**Carrega o instante da coleta.** O tray mostra "conferido hoje 07:42" junto do
número. Dado velho apresentado como atual é pior que dado ausente.

## Se você usa o extra `daily-scan`

Ele já chama o publicador ao fim de cada varredura. Este timer só acrescenta
frescor para quando alguém mexe na quarentena à mão.
