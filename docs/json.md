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

O futuro `clamav-status` em Rust (ver [ROADMAP](../ROADMAP.md)) vai produzir esta
mesma saída.

## Exemplo

```json
{
  "schema": 1,
  "version": "0.3.0",
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
    "finished_at": "2026-10-13T07:54:11-03:00"
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

## Campos

**Raiz**

| campo | tipo | |
|---|---|---|
| `schema` | int | versão deste formato |
| `version` | string | versão do clamav-tray que gerou |
| `status` | `"ok"` \| `"busy"` \| `"warn"` \| `"threat"` | a mesma precedência do ícone: ameaça > varrendo > serviço caído > ok |

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

**`paths`** — `socket`, `scan_log`, `daemon_log`, `quarantine`, `user_quarantine`:
string ou `null`. `daemon_log` é o log do clamd, **não** o da varredura.
