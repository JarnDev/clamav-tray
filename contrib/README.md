# contrib

O `clamav-tray` **observa** o que existe. Ele não instala unidade, não agenda
varredura e não decide o que varrer — essa é a escolha de desenho que o mantém
instalável sem root.

A consequência é honesta: numa máquina onde só se fez `apt install clamav-daemon`,
metade do menu fica vazia. Nenhuma distro relevante entrega varredura agendada,
monitor de pasta ou quarentena.

| | Debian/Ubuntu | Fedora | Arch |
|---|---|---|---|
| daemon + freshclam | vem no pacote | vem | vem |
| varredura agendada | **não vem** | **não vem** | **não vem** |
| monitor de pasta | **não vem** | **não vem** | **não vem** |
| quarentena | **não vem** | **não vem** | **não vem** |

Os extras aqui preenchem isso. Cada um é **independente e opcional** — instale só
o que quiser, ou nenhum, ou use como referência para escrever o seu.

## Extras

| | O que faz |
|---|---|
| [`extras/daily-scan`](extras/daily-scan) | varredura diária da home, com exclusões e quarentena |
| [`extras/downloads-watch`](extras/downloads-watch) | varre a pasta Downloads a cada arquivo novo |
| [`extras/quarantine-stats`](extras/quarantine-stats) | publica o resumo da quarentena de root para o tray ler |

## Regras que todo instalador aqui segue

- **Nunca sobrescreve.** Se já existe unidade com o mesmo nome, ele para e diz.
- **Prefixo `clamav-tray-`** em tudo, para não colidir com o que você já tenha.
- **Diz como desinstalar** ao terminar.
- **Nada de `curl | sudo bash`.** Você lê o arquivo e executa.

## Por que não vem tudo junto no pacote

Instalar unidade de sistema exige root e opina sobre o que varrer e quando.
Um indicador de bandeja que pede root na instalação é outra categoria de programa
— e passaria a competir com a configuração de quem já tem a sua.
