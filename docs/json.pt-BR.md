[English](json.md) · **Português (Brasil)**

# `clamav-tray --dump --json`

O que o tray enxerga, como dado. Não precisa de tela nem de PyGObject: serve para
script, Glance, Conky, `jq`, monitoramento.

```sh
clamav-tray --dump --json | jq -r .status          # ok | busy | warn | threat
clamav-tray --dump --json | jq '.scan.infected'
```

## Estabilidade

É um **contrato**. O campo `schema` sobe quando um campo muda de sentido, muda de
tipo ou some. Campo **novo** não sobe o `schema` — quem lê deve ignorar o que não
conhece.

- Ausência é `null`, nunca campo omitido.
- Horários em ISO 8601 **com fuso** (`2026-10-14T03:02:45-03:00`).
- Os testes em `tests/test_report.py` falham se um nome ou tipo mudar.

O futuro `clamav-status` em Rust (ver [ROADMAP](../ROADMAP.pt-BR.md)) vai produzir esta
mesma saída.

## Exemplo

```json
{
  "schema": 1,
  "version": "0.5.0",
  "producer": "tray",
  "language": "en",
  "generated_at": "2026-10-13T18:01:42-03:00",
  "status": "ok",
  "units": [
    {
      "id": "clamav-scan.timer",
      "label": "Scan",
      "kind": "timer",
      "user_scope": false,
      "active_state": "active",
      "sub_state": "waiting",
      "result": "success",
      "healthy": true,
      "running": false,
      "exit_status": null,
      "started_at": null,
      "finished_at": null,
      "next_run": "2026-10-14T03:02:45-03:00"
    }
  ],
  "scan": {
    "unit": "clamav-scan.service",
    "running": false,
    "outside_systemd": false,
    "verdict": "clean",
    "infected": 0,
    "unreadable": 6,
    "scanned": null,
    "duration_secs": 16317,
    "finished_at": "2026-10-13T07:54:11-03:00",
    "progress": null
  },
  "media": [],
  "quarantine": {
    "system": null,
    "user": {"count": 0}
  },
  "paths": {
    "socket": "/var/run/clamav/clamd.ctl",
    "scan_log": "/var/log/clamav/scan.log",
    "daemon_log": "/var/log/clamav/clamav.log",
    "quarantine": "/var/quarantine/clamav",
    "user_quarantine": null
  }
}
```

## O arquivo de estado

O tray em execução (também no modo `--headless`) grava este mesmo documento em
`$XDG_RUNTIME_DIR/clamav-tray/state.json` a cada atualização, de forma atômica
(arquivo temporário + rename: quem lê nunca vê meio arquivo). É o que a extensão
do GNOME lê, sem custo: nenhum processo é disparado. O `--dump --json` é a
alternativa quando o tray não está rodando.

## Campos

**Raiz**

| campo | tipo | |
|---|---|---|
| `schema` | int | versão deste formato |
| `version` | string | versão do clamav-tray que gerou |
| `producer` | `"tray"` \| `"dump"` | `tray` = o `state.json` que o tray em execução grava; `dump` = `--dump --json` |
| `language` | string | idioma resolvido da interface (`"en"`, `"pt_BR"`), para quem desenha falar a mesma língua |
| `generated_at` | string | ISO 8601. Um `state.json` que para de mudar significa tray parado |
| `status` | `"ok"` \| `"busy"` \| `"warn"` \| `"threat"` | a mesma precedência do ícone: ameaça > varrendo > serviço caído > ok. **Nenhuma unidade encontrada é `warn`**, não `ok` |

`status` **não** inclui mídia removível pendente: "pendente" depende do que o tray
já varreu na sessão dele, que fica na memória do processo, não no sistema.

**`units[]`** — ordenadas por `id`

| campo | tipo | |
|---|---|---|
| `id` | string | nome da unidade systemd |
| `label` | string | rótulo exibido no menu |
| `kind` | `"daemon"` \| `"job"` \| `"timer"` | pelo `Type=` da unidade: `job` é o que roda e termina |
| `user_scope` | bool | unidade do `systemctl --user` (a varredura sob demanda vive lá) |
| `active_state`, `sub_state`, `result` | string | como o systemd reporta |
| `healthy` | bool | job que achou vírus (saída 1) é saudável: achar é o trabalho dele |
| `running` | bool | job em execução agora |
| `exit_status` | int \| null | |
| `started_at`, `finished_at`, `next_run` | string \| null | ISO 8601 |

**`scan`** — a última varredura, da unidade que o tray escolhe (rodando agora >
terminou por último)

| campo | tipo | |
|---|---|---|
| `unit` | string \| null | de onde veio o resultado |
| `running` | bool | |
| `outside_systemd` | bool | há `clamscan`/`clamdscan` rodando fora de qualquer unidade |
| `verdict` | `"clean"` \| `"infected"` \| `"error"` \| `"unknown"` | lido do `SCAN SUMMARY`, nunca do código de saída. `unknown` = não havia resumo — não é o mesmo que limpo |
| `infected`, `unreadable` | int | |
| `scanned` | int \| null | o `clamdscan` nem sempre imprime |
| `duration_secs` | int \| null | |
| `finished_at` | string \| null | |
| `progress` | `{done, total}` \| null | arquivos feitos / arquivos listados, por contagem. Só no `state.json`: o contador mora no processo do tray |

**`media[]`** — mídia removível montada sob a árvore do usuário

| campo | tipo | |
|---|---|---|
| `key` | string | `dispositivo:ponto-de-montagem`, a identidade usada por `--scan-device` |
| `label`, `mountpoint` | string | |
| `size_bytes` | int \| null | |
| `scanned` | `{at, infected, not_contained}` \| null | o que o tray varreu **nesta sessão**; `null` = não varrida, e sempre `null` no `--dump` (isso vive na memória do tray). `not_contained` = encontradas e não isoladas (mídia somente leitura) |

**`quarantine`** — `{system, user}`; cada um `null` quando não dá para saber (a
do sistema é de root e só se conhece pelo resumo que alguém com privilégio
publica). `system`: `{count, bytes, checked_at}`; `user`: `{count}`.

**`paths`** — `socket`, `scan_log`, `daemon_log`, `quarantine`, `user_quarantine`:
string ou `null`. `daemon_log` é o log do clamd, **não** o da varredura.
