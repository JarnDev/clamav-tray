# daily-scan

Varredura da home às 03:00, com exclusões e quarentena: **incremental** todo dia
(só o que mudou desde a última varredura concluída) e **completa** a cada 7 dias.

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
/var/lib/clamav-tray-daily/             ← marcos da última varredura (criado na 1ª)
```

## Incremental e completa

O timer é um só e roda todo dia; o script escolhe o modo:

| | Quando | O que varre | Duração na máquina de origem |
|---|---|---|---|
| **completa** | na 1ª execução e quando a última completa tem mais de `CLAMAV_TRAY_FULL_EVERY` dias (padrão 7) | a home inteira, menos as exclusões | 4h40, 1,1 milhão de arquivos |
| **incremental** | nos outros dias | só arquivos com *ctime* posterior à última varredura concluída | minutos |

Para forçar um modo: `sudo /usr/local/bin/clamav-tray-daily.sh full` (ou
`incremental`). O log e a notificação dizem qual modo rodou.

**Por que a completa continua existindo.** A base de assinaturas muda todo dia. A
incremental só olha arquivo novo; um arquivo antigo que só uma assinatura de hoje
reconhece seria ignorado para sempre. A completa reavalia tudo contra a base atual,
e 7 dias é o teto de exposição desse caso.

**Por idade, não por dia da semana.** Com `OnCalendar=Sun`, a máquina desligada no
domingo empurraria a completa para o domingo seguinte. Medindo a idade da última,
ela roda no primeiro dia em que a máquina estiver ligada.

**ctime, não mtime.** O mtime é o usuário quem define: `touch -d`, `tar x`,
`cp -p`, `wget` e `curl -R` gravam a data de origem, e um arquivo recém-baixado
com data de 2019 passaria batido numa busca por `-newer`. O ctime só o kernel
escreve. Custo: `chmod` ou `mv` também o atualizam, e esses arquivos entram na
lista sem terem mudado de conteúdo — sobra pequena perto do erro oposto.
Ponto cego: mover um **diretório** dentro do mesmo sistema de arquivos não
altera o ctime dos arquivos dentro dele. Um diretório tirado de um caminho
excluído (`.cache`, `node_modules`) e posto em `Documentos` só é visto na próxima
completa — no máximo 7 dias depois.

**O marco é do início, e só vale se a varredura concluir.** O instante é gravado
antes de listar os arquivos; o que mudar durante a varredura entra na próxima. Se
a varredura não produzir `SCAN SUMMARY` (daemon caiu, máquina desligou no meio), o
marco anterior fica, e a próxima incremental cobre o intervalo inteiro.

> Atualizando de uma versão anterior: reinstale o `clamav-tray-daily.sh`. Sem
> marcos em `/var/lib/clamav-tray-daily`, a primeira execução é completa.

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
