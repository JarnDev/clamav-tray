# usb-scan

Varre mídia removível assim que ela é montada.

## Por que não usa `RUN+=` no udev

A documentação do udev é categórica:

> *Starting daemons or other long-running processes is not allowed; the forked
> processes, detached or not, will be **unconditionally killed** after the event
> handling has finished.*

Uma varredura de pendrive dura mais que um evento do udev. Com `RUN+=`, ela é
morta no meio — e em silêncio, que é o pior jeito de falhar num programa cuja
função é avisar.

A própria doc nomeia a saída: **uma unidade de serviço puxada pelo dispositivo**.
É o que a regra faz, com `TAG+="systemd"` e `ENV{SYSTEMD_WANTS}`.

Ganho colateral: virando unidade, ela **aparece no `clamav-tray`** — que descobre
por unidade e não enxerga processo solto.

## A armadilha do `%k`

O udev entrega o **nome de kernel** da partição (`sdc1`), não o ponto de montagem.
E dispara no evento `add`, que acontece **antes** de o automount terminar.

Um script que espere receber um diretório pronto recebe `sdc1` e aborta na
terceira linha. Aqui quem resolve é o script, com `findmnt`, esperando até 30 s
pela montagem.

Se não montar nesse prazo, sai com **0** — não é falha: pode ser partição de
sistema, swap, ou o usuário simplesmente não abriu a mídia.

## Instalar

```sh
sudo ./install.sh <seu-usuario>
```

O instalador **pergunta antes**, porque este extra é o único que age sozinho em
resposta a hardware: plugar um HD externo de 2 TB dispara uma varredura longa que
você não pediu.

Para parar uma em curso:

```sh
systemctl stop 'clamav-tray-usb@*'
```

## `--multiscan`, diferente dos outros extras

Aqui não há exclusão a aplicar, então dá para varrer o diretório direto — sem
`--file-list` — e aproveitar as threads do `clamd`.

A varredura da home usa `--file-list` porque as exclusões precisam ser aplicadas
pelo `find`; o `clamdscan` não tem `--exclude-dir`. Este extra não paga esse
custo.

## Quarentena separada

`/var/quarantine/clamav-usb`, distinta da varredura diária e do monitor de
Downloads. Assim dá para saber por onde a ameaça entrou.
