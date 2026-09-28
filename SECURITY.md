# Política de segurança

## Reportar uma vulnerabilidade

Abra um [security advisory](https://github.com/JarnDev/clamav-tray/security/advisories/new)
em vez de uma issue pública.

Se preferir e-mail, use o endereço do autor no histórico de commits. Respondo
quando puder — é um projeto de uma pessoa, sem SLA.

## Superfície de ataque, honestamente

O programa roda **como usuário comum**, sem privilégio. Isso limita o estrago,
mas não a zero. O que ele faz que merece atenção:

**Executa `systemctl` e `journalctl`** para ler estado. Leitura apenas; não
inicia, para nem modifica unidade de sistema.

**Executa `clamdscan`** com caminhos vindos de `/proc/mounts` e da configuração.
Os argumentos são montados como lista, nunca por interpolação em shell — exceto
na varredura sob demanda, que passa por `sh -c` para redirecionar a saída. Ali os
caminhos são citados com aspas simples escapadas.

**Abre terminal e gerenciador de arquivos** com caminhos de configuração. Um
arquivo de configuração malicioso poderia apontar para outro lugar — mas quem o
escreve já é você.

**Lê `/proc/mounts` e `/sys/block/*/removable`.** Só leitura.

**Não abre porta, não faz requisição de rede, não envia telemetria.**

## O que o programa deliberadamente NÃO faz

**Não torna a quarentena legível.** Ela é tipicamente `750` de root, e isso está
certo — é malware guardado. O programa lê um resumo publicado por quem tem
privilégio, e esse resumo não carrega nome de arquivo nem conteúdo.

**Não abre a quarentena no gerenciador de arquivos.** Gerenciador de arquivos
gera miniatura e lê cabeçalho do que exibe; encostar num executável malicioso com
o thumbnailer é um jeito ruim de olhar para ele. A ação lista com `ls` num
terminal.

**Não varre a própria quarentena.** Ela é excluída das varreduras da home, senão
o que já foi isolado seria reencontrado e movido de novo.

## Limitação que vale saber

O programa **relata**; quem protege é o ClamAV. Um indicador verde significa que
os serviços responderam e que a última varredura não achou nada — não que a
máquina esteja limpa.

E há um caso em que ele avisa explicitamente: quando a mídia é somente leitura, o
`clamdscan` encontra a ameaça e **falha ao isolá-la**, ainda reportando
`Infected files: N`. O menu distingue "encontrado" de "isolado" justamente por
isso. Ver [docs/quarantine.md](docs/quarantine.md).
