# Mídia removível

Ao plugar um pendrive, ele **aparece no menu** e o ícone da bandeja muda — mas
nada é varrido até você clicar.

```
DISPOSITIVOS
🟡  KINGSTON   14,9 GB · não varrido
     /media/user/KINGSTON
```

Clicar varre. Enquanto varre, valem a barra de progresso e o botão "Parar
varredura" — a mesma máquina da varredura da home.

### Por que não varre sozinho

Varrer automaticamente ao plugar exige regra de udev, unidade de sistema e root — e
age sem perguntar. Plugar um HD externo de 2 TB dispararia uma varredura longa que
ninguém pediu, e interrompê-la exigiria privilégio.

Como a varredura roda **como você**, nada disso é necessário: o `udisks2` monta a
mídia com o seu uid, então `clamdscan --fdpass` a lê sem root.

Quem quiser o comportamento automático instala
[`contrib/extras/usb-scan`](../contrib/extras/usb-scan).

### Como a detecção funciona

Duas leituras de arquivo por atualização, nenhum subprocesso:

1. `/proc/mounts` — o que está montado sob `/media/$USER` ou `/run/media/$USER`
2. `/sys/block/<disco>/removable` — se o hardware é removível, segundo o kernel

O filtro por caminho sozinho seria proxy: é onde o `udisks2` monta, mas alguém
pode montar disco fixo ali. Por isso o cruzamento com o dado do kernel.

**Limite conhecido:** mídia que você nunca abriu não está montada, e o que não está
montado não pode ser varrido por um processo de usuário. Esse caso só o extra com
root cobre.
