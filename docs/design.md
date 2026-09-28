# Decisões de desenho

As explicações longas que o README carregava até a v0.1. Cada uma existe
porque uma alternativa razoável foi tentada e falhou, ou porque a medição
contrariou a intuição.

## O que funciona numa instalação limpa

O programa **observa** o que existe. Ele não instala unidade, não agenda varredura
e não decide o que varrer — é essa escolha que o mantém instalável sem root.

Consequência honesta, medida num Ubuntu com `clamav-daemon` e `clamav-freshclam`:

| | De fábrica |
|---|---|
| ClamAV Daemon, Freshclam, On-Access | **sim**, vêm nos pacotes |
| Varrer minha home agora | **sim**, precisa só do `clamd` no ar |
| Quarentena do usuário | **sim**, criada sob demanda |
| Barra de progresso | **sim**, é da varredura sob demanda |
| Varredura agendada, "Próxima", "Última" | **não** — nenhuma distro entrega |
| Monitor de pasta | **não** |
| Quarentena do sistema | **não** — nasce do `--move=` de quem agendou |

Metade de cima funciona; a metade da varredura fica vazia. Não é bug: a distro não
agenda varredura, e o programa não deve inventar uma.

Para preencher, há extras **opcionais e independentes** em [`contrib/extras/`](../contrib/extras),
cada um com instalador próprio — varredura diária, monitor de Downloads e
publicação das estatísticas de quarentena. Instale só o que quiser, ou use como
referência para escrever o seu.

## Idioma

**Inglês é o padrão.** As strings no código são as inglesas, e traduzir é opcional
por construção: uma chave sem tradução aparece em inglês em vez de quebrar.

```toml
[general]
language = "pt_BR"   # ou "auto" para seguir o locale do sistema
```

Traduções vivem em `clamav_tray/i18n.py`, num dicionário. Não usa gettext de propósito:
compilar `.po` em `.mo` acrescentaria um passo de build a um projeto que hoje instala com
`pipx install` e nada mais. Para contribuir com um idioma, copie o bloco `pt_BR` e traduza —
sem instalar ferramenta nenhuma. As chaves já são as frases em inglês, então migrar para
gettext depois é mecânico.

## Configuração

Há um item **Settings** no menu: ele cria o arquivo comentado se não existir e abre no seu
editor. O arquivo é **relido sozinho ao salvar** — sem reiniciar.

Não há diálogo de preferências em GTK de propósito: seria mais código que o resto do programa
junto, para uma edição que acontece raramente.

Nenhuma configuração é obrigatória. O programa descobre sozinho:

- **unidades** — pelo glob `clam*` no systemd, o que cobre tanto `clamav-daemon.service`
  (Debian, Ubuntu, Arch) quanto `clamd@scan.service` (Fedora, que usa unidade *templated*)
- **caminhos** — perguntando ao `clamconf`, que vem do próprio ClamAV e não do empacotador

Para ajustar rótulos, acrescentar unidades ou sobrescrever caminhos, veja
`clamav-tray.example.toml`.

## Permissões

Ler estado de unidade não exige privilégio. Ler o **histórico** do journal exige estar em `adm`
ou `systemd-journal`, dependendo da distro. Sem isso o programa continua funcionando: mostra o
estado atual e omite o histórico, em vez de quebrar.
