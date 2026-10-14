// Testes do model.js, rodados com gjs fora do shell:
//
//     TZ=America/Sao_Paulo gjs -m gnome-extension/tests/test_model.js
//
// Sem framework: gjs nao traz um, e o CI nao deveria precisar de mais que o
// interpretador — a mesma regra dos testes em Python. TZ fixo porque horario
// relativo ("hoje 07:54") depende do fuso.

import System from 'system';

import * as M from '../clamav-tray@jarndev.github.io/model.js';

let falhas = 0;
function caso(nome, fn) {
    try {
        fn();
        print(`ok     ${nome}`);
    } catch (e) {
        falhas++;
        print(`FALHA  ${nome}\n       ${e.message}`);
    }
}
function igual(a, b) {
    const ja = JSON.stringify(a), jb = JSON.stringify(b);
    if (ja !== jb)
        throw new Error(`esperado ${jb}\n       obtido   ${ja}`);
}

const AGORA = new Date('2026-10-13T18:00:00-03:00');
const base = (extra = {}) => ({
    schema: 1, language: 'en', producer: 'tray', generated_at: '2026-10-13T17:59:55-03:00',
    status: 'ok',
    units: [
        {id: 'clamav-daemon.service', label: 'ClamAV Daemon', kind: 'daemon', healthy: true, running: false, active_state: 'active', next_run: null},
        {id: 'clamav-scan.timer', label: 'Scan', kind: 'timer', healthy: true, running: false, active_state: 'active', next_run: '2026-10-14T03:02:45-03:00'},
    ],
    scan: {unit: 'clamav-scan.service', running: false, verdict: 'clean', infected: 0, unreadable: 2,
        scanned: 1099137, duration_secs: 16680, finished_at: '2026-10-13T07:54:11-03:00', progress: null},
    ...extra,
});

caso('protegido, em ingles', () => {
    const v = M.viewModel(base(), AGORA);
    igual([v.status, v.icon, v.title, v.subtitle], ['ok', 'security-high-symbolic', 'Protected', 'all services running']);
    igual(v.lastScan.text, 'clean (4h38), 2 unreadable');
    igual(v.lastScan.when, 'today 07:54');
    igual(v.lastScan.files, '1,099,137 files');
    igual(v.nextScan, 'tomorrow 03:02');
});

caso('mesmo estado em portugues', () => {
    const v = M.viewModel(base({language: 'pt_BR'}), AGORA);
    igual([v.title, v.subtitle], ['Protegido', 'todos os serviços no ar']);
    igual(v.lastScan.text, 'limpa (4h38), 2 ilegível(is)');
    igual(v.lastScan.files, '1.099.137 arquivos');
    igual(v.nextScan, 'amanhã 03:02');
    igual(v.labels.services, 'Serviços');
});

caso('ameaca vence tudo e e alarme', () => {
    const v = M.viewModel(base({status: 'threat', scan: {...base().scan, verdict: 'infected', infected: 1}}), AGORA);
    igual([v.icon, v.title, v.subtitle], ['security-low-symbolic', 'Threat detected', '1 threat found']);
    igual(v.lastScan.alarming, true);
});

caso('sem servico nenhum nao e protegido', () => {
    const v = M.viewModel(base({status: 'warn', units: []}), AGORA);
    igual([v.title, v.subtitle], ['Attention', 'no ClamAV service found']);
});

caso('servico caido aparece pelo nome', () => {
    const units = [{...base().units[0], healthy: false, active_state: 'failed'}];
    const v = M.viewModel(base({status: 'warn', units}), AGORA);
    igual(v.subtitle, 'ClamAV Daemon not healthy');
    igual(v.services[0].detail, 'failed');
});

caso('arquivo velho = tray parado, e nunca "protegido"', () => {
    const v = M.viewModel(base({generated_at: '2026-10-13T17:50:00-03:00'}), AGORA);
    igual([v.status, v.title, v.subtitle], ['stale', 'Tray not running', 'no update for 10 min']);
    igual(v.services, []);
});

caso('sem arquivo nenhum tambem e tray parado', () => {
    igual(M.viewModel(null, AGORA).status, 'stale');
});

caso('sem arquivo, cai no idioma da sessao', () => {
    igual(M.viewModel(null, AGORA, 'pt_BR').title, 'Tray parado');
    igual(M.viewModel(null, AGORA).title, 'Tray not running');
});

caso('limite de 30 s para envelhecer', () => {
    igual(M.viewModel(base({generated_at: '2026-10-13T17:59:31-03:00'}), AGORA).status, 'ok');
    igual(M.viewModel(base({generated_at: '2026-10-13T17:59:29-03:00'}), AGORA).status, 'stale');
});

caso('sem resultado nao vira "limpa"', () => {
    const v = M.viewModel(base({scan: {...base().scan, verdict: 'unknown', scanned: null, finished_at: null}}), AGORA);
    igual([v.lastScan.text, v.lastScan.when, v.lastScan.files], ['no result recorded', null, null]);
});

caso('duracao e data distante', () => {
    igual([M.duration(42), M.duration(720), M.duration(16680)], ['42s', '12min', '4h38']);
    igual(M.relativeTime('2026-10-09T03:00:00-03:00', AGORA, M.translator('en')), '09/10 03:00');
});

print(falhas ? `\nFALHOU — ${falhas} falha(s)` : '\nOK — 0 falha(s)');
if (falhas)
    System.exit(1);
