# Barra de progresso

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
