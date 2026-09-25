# daily-scan

Varredura diária da home, às 03:00, com exclusões e quarentena.

Nenhuma distro entrega isso — por isso o `clamav-tray` mostra "Próxima varredura"
vazia numa instalação limpa.

## Instalar

```sh
sudo ./install.sh <seu-usuario>
```

Leia o `install.sh` antes. Ele recusa instalar se já houver unidade com o mesmo
nome, e imprime como desinstalar ao terminar.

## O que ele instala

```
/usr/local/bin/clamav-tray-daily.sh
/etc/systemd/system/clamav-tray-daily.{service,timer}
/etc/default/clamav-tray-daily          ← configuração
```

## Decisões que valem saber

**`clamdscan`, não `clamscan`.** O `clamscan` recarrega ~1 GB de assinaturas a
cada execução e varre em thread única. Medido na máquina de origem: mais de
6 horas, com o SSD a 95% de ocupação e pressão de I/O em 57% — o terminal chegou
a ficar em estado D.

**`--fdpass`.** O `clamd` roda como usuário `clamav` e não lê dentro de `/home`.
Com `--fdpass` quem abre o arquivo é este script (root) e passa o **descritor**
pelo socket. Sem cópia.

**`--file-list` em vez de apontar o diretório.** O `clamdscan` não tem
`--exclude-dir`, então as exclusões são aplicadas pelo `find` aqui.

**O veredito vem do `SCAN SUMMARY`, não do código de saída.** O `clamdscan`
devolve `2` se *qualquer* arquivo não pôde ser aberto, e numa varredura de horas
sobre um milhão de arquivos é rotina que temporários sumam no meio. Tratar isso
como falha faz o serviço reportar erro todo dia sem nenhuma ameaça — alarme que
sempre toca deixa de ser alarme.

**`Nice=19` e `IOSchedulingClass=idle` não salvam disco saturado.** Estão ali, mas
a varredura que travou a máquina de origem rodava com exatamente essas opções. O
que resolveu foi trocar o scanner e mudar o horário.
