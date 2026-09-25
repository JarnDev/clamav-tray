# downloads-watch

Varre cada arquivo novo na pasta Downloads, no instante em que termina de baixar.

## Instalar

```sh
sudo ./install.sh <seu-usuario> [pasta]
```

Requer `inotify-tools`. O instalador verifica e avisa se faltar.

## Decisões que valem saber

**`close_write` e `moved_to`, não `create`.** Varrer em `create` pegaria o arquivo
pela metade. `close_write` cobre o arquivo terminado; `moved_to` cobre o que o
navegador renomeia de `.part`/`.crdownload` para o nome final.

**`Restart=always`, não `on-failure`.** O systemd considera `SIGTERM` uma parada
**limpa**, então `on-failure` não traria o vigia de volta quando algo o matasse —
exatamente o caso em que você não quer ficar sem vigia.

**O `grep FOUND` lê só esta execução.** Lendo o log acumulado, todo arquivo
seguinte seria reportado como infectado depois da primeira ameaça da vida. Esse
bug existiu na versão original e levou tempo para ser notado.

**Quarentena separada** (`/var/quarantine/clamav-downloads`) da varredura diária.
Assim dá para saber por onde a ameaça entrou.
