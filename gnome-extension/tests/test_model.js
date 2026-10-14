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

// ---- F3: ao vivo, midia, quarentena, --dump

const varrendo = (scan = {}) => base({
    status: 'busy',
    units: [...base().units, {id: 'clamav-scan.service', label: 'Scan', kind: 'job', healthy: true,
        running: true, active_state: 'active', started_at: '2026-10-13T17:00:00-03:00', next_run: null}],
    scan: {...base().scan, running: true, progress: {done: 571234, total: 1000000}, ...scan},
});

caso('varredura com contagem: barra, taxa e tempo', () => {
    const v = M.viewModel(varrendo(), AGORA);
    igual([v.title, v.subtitle, v.panelText], ['Scanning', 'for 1h00', '57%']);
    igual(v.live.fraction, 0.571234);
    igual(v.live.detail, '571,234 / 1,000,000 files · 158/s');
});

caso('varredura sem contagem: sem porcentagem inventada', () => {
    const v = M.viewModel(varrendo({progress: null}), AGORA);
    igual([v.live.fraction, v.live.percent, v.panelText], [null, null, '']);
    igual(v.live.detail, 'counting files…');
});

caso('varredura fora do systemd', () => {
    const v = M.viewModel(varrendo({progress: null, unit: null, outside_systemd: true}), AGORA);
    igual([v.live.elapsed, v.live.detail], [null, 'started outside the tray']);
});

caso('ameaca na barra mostra a contagem', () => {
    const v = M.viewModel(base({status: 'threat', scan: {...base().scan, verdict: 'infected', infected: 3}}), AGORA);
    igual(v.panelText, '⚠ 3');
    igual(M.viewModel(base(), AGORA).panelText, '');
});

const PEN = {key: '/dev/sdc1:/media/u/PEN', label: 'PEN', mountpoint: '/media/u/PEN', size_bytes: 16 * 1024 ** 3};
caso('midia: nao varrida, limpa e ameaca nao isolada', () => {
    const media = [
        {...PEN, scanned: null},
        {...PEN, label: 'HD', size_bytes: 1.5 * 1024 ** 4, scanned: {at: '2026-10-13T17:00:00-03:00', infected: 0, not_contained: 0}},
        {...PEN, label: 'CD', size_bytes: null, scanned: {at: '2026-10-13T17:00:00-03:00', infected: 1, not_contained: 1}},
    ];
    const v = M.viewModel(base({media, language: 'pt_BR'}), AGORA);
    igual(v.media.map(m => [m.label, m.detail, m.tone]), [
        ['PEN', '16 GB · não varrido', 'idle'],
        ['HD', '1,5 TB · limpo hoje 17:00', 'ok'],
        ['CD', '1 ameaça NÃO isolada hoje 17:00', 'threat'],
    ]);
});

caso('quarentena: so o que se sabe', () => {
    const quarantine = {system: {count: 2, bytes: 2178432, checked_at: '2026-10-13T03:00:00-03:00'}, user: {count: 0}};
    const v = M.viewModel(base({quarantine}), AGORA, 'en', {userName: 'ana'});
    igual(v.quarantine.map(q => [q.owner, q.detail, q.note, q.tone]), [
        ['root', '2 files · 2.1 MB', 'checked today 03:00', 'warn'],
        ['ana', 'empty', null, 'ok'],
    ]);
    igual(M.viewModel(base({quarantine: {system: null, user: null}}), AGORA).quarantine, []);
    igual(M.viewModel(base({quarantine: null}), AGORA).quarantine, []);
});

caso('--dump: nunca velho, avisa a origem e nao inventa "nao varrido"', () => {
    const v = M.viewModel(base({producer: 'dump', generated_at: '2026-10-13T10:00:00-03:00', media: [{...PEN, scanned: null}]}), AGORA);
    igual([v.status, v.footer], ['ok', 'tray not running · snapshot from --dump']);
    igual(v.media[0].detail, '16 GB');
});

caso('sem clamav-tray para o --dump, diz o motivo', () => {
    igual(M.viewModel(null, AGORA, 'pt_BR', {reason: 'no-command'}).subtitle, 'clamav-tray não encontrado');
});

caso('refresh_secs maior estica o limite de velho', () => {
    const s = base({refresh_secs: 60, generated_at: '2026-10-13T17:57:30-03:00'});
    igual(M.viewModel(s, AGORA).status, 'ok');
    igual(M.staleAfter(null), 30);
});

caso('tamanhos como no Python', () => {
    igual([M.humanSize(15 * 1024 ** 3, 'pt_BR'), M.humanSize(14.9 * 1024 ** 3, 'pt_BR'), M.humanSize(0, 'en')], ['15 GB', '14,9 GB', '']);
    igual([M.humanBytes(512, 'en'), M.humanBytes(4096, 'en'), M.humanBytes(3 * 1024 ** 3, 'pt_BR')], ['512 B', '4 KB', '3,0 GB']);
});

print(falhas ? `\nFALHOU — ${falhas} falha(s)` : '\nOK — 0 falha(s)');
if (falhas)
    System.exit(1);
