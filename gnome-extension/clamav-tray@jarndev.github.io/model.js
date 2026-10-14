// JSON do clamav-tray -> o que o painel desenha. Funcao PURA: sem GNOME, sem I/O,
// sem relogio implicito (o "agora" entra por parametro). E testada com gjs fora do
// shell (tests/test_model.js) e no CI.
//
// Regra do projeto: a extensao so DESENHA. Nenhuma decisao sobre o ClamAV mora
// aqui — status, veredito e saude ja vem prontos no JSON, calculados pelo Python.
// Este modulo so escolhe texto, cor e icone para o que ja foi decidido.

// Mesmos icones do tray (clamav_tray/tray.py, ICONS): quem usa os dois ve o mesmo
// escudo.
export const ICONS = {
    ok: 'security-high-symbolic',
    busy: 'system-search-symbolic',
    warn: 'security-medium-symbolic',
    threat: 'security-low-symbolic',
    stale: 'security-medium-symbolic',
};

// 3 atualizacoes do tray sem arquivo novo = tray parado. Uma so de atraso
// acontece com a maquina ocupada; tres, nao. O intervalo vem do proprio arquivo
// (refresh_secs), porque o usuario pode muda-lo; 30 s e o piso.
export const STALE_SECS = 30;

export function staleAfter(state) {
    return Math.max(STALE_SECS, 3 * (state?.refresh_secs ?? 10));
}

const CATALOG = {
    pt_BR: {
        'Protected': 'Protegido',
        'Scanning': 'Varredura em andamento',
        'Attention': 'Atenção',
        'Threat detected': 'Ameaça detectada',
        'Tray not running': 'Tray parado',
        'all services running': 'todos os serviços no ar',
        'no ClamAV service found': 'nenhum serviço do ClamAV encontrado',
        '{names} not healthy': '{names} com problema',
        'no update for {n} min': 'sem atualização há {n} min',
        'Services': 'Serviços',
        'Last scan': 'Última varredura',
        'Next scan': 'Próxima varredura',
        'clean': 'limpa',
        'no result recorded': 'nenhum resultado registrado',
        'scan did not finish': 'a varredura não concluiu',
        '{n} threat found': '{n} ameaça encontrada',
        '{n} threats found': '{n} ameaças encontradas',
        '{n} unreadable': '{n} ilegível(is)',
        '{n} files': '{n} arquivos',
        'today': 'hoje',
        'yesterday': 'ontem',
        'tomorrow': 'amanhã',
        'running': 'rodando',
        'stopped': 'parado',
        'failed': 'falhou',
        'waiting': 'aguardando',
        'clamav-tray not found': 'clamav-tray não encontrado',
        'tray not running · snapshot from --dump': 'tray parado · retrato via --dump',
        'In progress': 'Em andamento',
        'for {duration}': 'há {duration}',
        '{done} / {total} files': '{done} / {total} arquivos',
        '{n}/s': '{n}/s',
        'started outside the tray': 'iniciada fora do tray',
        'counting files…': 'contando arquivos…',
        'Devices': 'Dispositivos',
        'not scanned': 'não varrido',
        'clean {when}': 'limpo {when}',
        '{n} threat {when}': '{n} ameaça {when}',
        '{n} threats {when}': '{n} ameaças {when}',
        '{n} threat NOT isolated {when}': '{n} ameaça NÃO isolada {when}',
        '{n} threats NOT isolated {when}': '{n} ameaças NÃO isoladas {when}',
        'Quarantine': 'Quarentena',
        'empty': 'vazia',
        '{n} file': '{n} arquivo',
        'checked {when}': 'conferida {when}',
    },
};

// Separadores (milhar, decimal), como i18n.SEPARATORS no Python.
const SEPARATORS = {en: [',', '.'], pt_BR: ['.', ',']};

export function translator(lang) {
    const cat = CATALOG[lang] ?? {};
    return (key, vars = {}) =>
        (cat[key] ?? key).replace(/\{(\w+)\}/g, (_m, k) => String(vars[k] ?? ''));
}

export function number(n, lang, decimals = 0) {
    const [thousands, decimal] = SEPARATORS[lang] ?? SEPARATORS.en;
    const [int, frac] = (decimals ? n.toFixed(decimals) : String(Math.trunc(n))).split('.');
    const out = int.replace(/\B(?=(\d{3})+(?!\d))/g, thousands);
    return frac ? `${out}${decimal}${frac}` : out;
}

// Porte de devices.human_size: "15 GB" e nao "15,0 GB" (casa zerada e ruido).
export function humanSize(n, lang) {
    if (!n)
        return '';
    for (const [unit, div] of [['TB', 1024 ** 4], ['GB', 1024 ** 3], ['MB', 1024 ** 2]]) {
        if (n >= div) {
            const v = n / div;
            const whole = Math.round(v * 10) / 10 === Math.round(v);
            return `${whole ? number(Math.round(v), lang) : number(v, lang, 1)} ${unit}`;
        }
    }
    return `${Math.floor(n / 1024)} KB`;
}

// Porte de quarantine.human_bytes.
export function humanBytes(n, lang) {
    if (n < 1024)
        return `${n} B`;
    if (n < 1024 ** 2)
        return `${Math.floor(n / 1024)} KB`;
    if (n < 1024 ** 3)
        return `${number(n / 1024 ** 2, lang, 1)} MB`;
    return `${number(n / 1024 ** 3, lang, 1)} GB`;
}

export function duration(secs) {
    // "4h38", "12min", "42s" — a unidade mais grossa que informa, como no Python.
    if (secs >= 3600)
        return `${Math.floor(secs / 3600)}h${String(Math.floor((secs % 3600) / 60)).padStart(2, '0')}`;
    if (secs >= 60)
        return `${Math.floor(secs / 60)}min`;
    return `${secs}s`;
}

function pad(n) {
    return String(n).padStart(2, '0');
}

// 'hoje 07:54' / 'amanha 03:02' / '09/10 03:00'. O fuso local entra pelo proprio
// Date (getHours etc.), que e o fuso do shell — o mesmo da tela do usuario.
export function relativeTime(iso, now, t) {
    if (!iso)
        return null;
    const when = new Date(iso);
    const day = d => Date.UTC(d.getFullYear(), d.getMonth(), d.getDate());
    const delta = Math.round((day(when) - day(now)) / 86400000);
    const hm = `${pad(when.getHours())}:${pad(when.getMinutes())}`;
    const prefix = {0: 'today', [-1]: 'yesterday', 1: 'tomorrow'}[delta];
    return prefix ? `${t(prefix)} ${hm}` : `${pad(when.getDate())}/${pad(when.getMonth() + 1)} ${hm}`;
}

function verdictText(scan, t, lang) {
    switch (scan.verdict) {
    case 'unknown': return t('no result recorded');
    case 'error': return t('scan did not finish');
    case 'infected':
        return t(scan.infected === 1 ? '{n} threat found' : '{n} threats found',
            {n: number(scan.infected, lang)});
    }
    let out = t('clean');
    if (scan.duration_secs != null)
        out += ` (${duration(scan.duration_secs)})`;
    if (scan.unreadable)
        out += `, ${t('{n} unreadable', {n: number(scan.unreadable, lang)})}`;
    return out;
}

function unitState(u, t) {
    if (u.running)
        return t('running');
    if (!u.healthy)
        return u.active_state === 'failed' ? t('failed') : t('stopped');
    if (u.kind === 'timer')
        return t('waiting');
    if (u.kind === 'job')
        return '';
    return t('running');
}

// Varredura em curso. Fracao so com contagem real (scan.progress); sem ela, a
// barra fica vazia e o texto diz so o tempo — nunca uma porcentagem inventada.
function liveScan(state, now, t, lang) {
    const scan = state.scan ?? {};
    if (!scan.running)
        return null;
    const unit = (state.units ?? []).find(u => u.id === scan.unit && u.running);
    const elapsed = unit?.started_at
        ? Math.max(0, Math.round((now - new Date(unit.started_at)) / 1000)) : null;
    const pr = scan.progress;
    const fraction = pr && pr.total > 0 ? Math.min(pr.done / pr.total, 1) : null;
    const lines = [];
    if (pr && pr.total > 0) {
        lines.push(t('{done} / {total} files', {done: number(pr.done, lang), total: number(pr.total, lang)}));
        if (elapsed && pr.done > 0)
            lines.push(t('{n}/s', {n: number(Math.max(Math.floor(pr.done / elapsed), 1), lang)}));
    } else if (!scan.outside_systemd) {
        lines.push(t('counting files…'));
    }
    if (scan.outside_systemd)
        lines.push(t('started outside the tray'));
    return {
        fraction,
        percent: fraction === null ? null : `${Math.floor(fraction * 100)}%`,
        elapsed: elapsed ? t('for {duration}', {duration: duration(elapsed)}) : null,
        detail: lines.join(' · '),
    };
}

// Midia removivel. `scanned` so existe no state.json do tray (vive na memoria
// dele); no --dump e sempre null, e "nao varrido" ali seria afirmar o que nao se sabe.
function mediaRows(state, now, t, lang, fromDump) {
    return (state.media ?? []).map(m => {
        let detail = null, tone = 'idle';
        if (!fromDump) {
            const sc = m.scanned;
            if (!sc) {
                detail = t('not scanned');
            } else {
                const when = relativeTime(sc.at, now, t);
                if (sc.not_contained) {
                    detail = t(sc.not_contained === 1 ? '{n} threat NOT isolated {when}' : '{n} threats NOT isolated {when}',
                        {n: number(sc.not_contained, lang), when});
                    tone = 'threat';
                } else if (sc.infected) {
                    detail = t(sc.infected === 1 ? '{n} threat {when}' : '{n} threats {when}',
                        {n: number(sc.infected, lang), when});
                    tone = 'threat';
                } else {
                    detail = t('clean {when}', {when});
                    tone = 'ok';
                }
            }
        }
        return {
            label: m.label,
            detail: [humanSize(m.size_bytes, lang), detail].filter(Boolean).join(' · '),
            tone,
            mountpoint: m.mountpoint,
        };
    });
}

// Quarentenas que se conhece. null = nao da para saber, e entao a linha some:
// "0" afirmaria uma quarentena vazia que ninguem conferiu.
function quarantineRows(state, now, t, lang, userName) {
    const q = state.quarantine;
    const rows = [];
    const files = n => n === 0 ? t('empty') : t(n === 1 ? '{n} file' : '{n} files', {n: number(n, lang)});
    if (q?.system) {
        const s = q.system;
        rows.push({
            owner: 'root',
            detail: [files(s.count), s.count && s.bytes ? humanBytes(s.bytes, lang) : null].filter(Boolean).join(' · '),
            note: s.checked_at ? t('checked {when}', {when: relativeTime(s.checked_at, now, t)}) : null,
            tone: s.count ? 'warn' : 'ok',
        });
    }
    if (q?.user) {
        rows.push({
            owner: userName,
            detail: files(q.user.count),
            note: null,
            tone: q.user.count ? 'warn' : 'ok',
        });
    }
    return rows;
}

// Texto ao lado do icone na barra, como o do tray: vazio em repouso, "57%"
// varrendo, "⚠ 2" com ameaca. Indicador que fala o tempo todo vira ruido.
function panelText(state, live, lang) {
    if (state.status === 'threat')
        return `⚠ ${number(state.scan?.infected ?? 0, lang)}`;
    if (live)
        return live.percent ?? '';
    return '';
}

// state: o JSON (objeto), ou null se nao havia arquivo. now: Date.
// fallbackLang: idioma da sessao, usado quando nao ha arquivo (sem `language`).
// opts.userName: dono da quarentena do usuario. opts.reason: por que nao ha
// estado ('no-command' = nem state.json nem clamav-tray para o --dump).
export function viewModel(state, now, fallbackLang = 'en', opts = {}) {
    const lang = state?.language ?? fallbackLang;
    const t = translator(lang);

    const labels = {
        services: t('Services'), lastScan: t('Last scan'), nextScan: t('Next scan'),
        live: t('In progress'), devices: t('Devices'), quarantine: t('Quarantine'),
    };
    // Saida do --dump acabou de ser gerada pela propria extensao: nunca e velha.
    const fromDump = state?.producer === 'dump';
    const ageSecs = state ? (now - new Date(state.generated_at)) / 1000 : Infinity;
    if (!state || (!fromDump && !(ageSecs <= staleAfter(state)))) {
        let subtitle = '';
        if (state)
            subtitle = t('no update for {n} min', {n: Math.max(1, Math.round(ageSecs / 60))});
        else if (opts.reason === 'no-command')
            subtitle = t('clamav-tray not found');
        return {
            status: 'stale',
            icon: ICONS.stale,
            panelText: '',
            title: t('Tray not running'),
            subtitle,
            live: null,
            services: [],
            lastScan: null,
            nextScan: null,
            media: [],
            quarantine: [],
            footer: null,
            labels,
        };
    }

    const units = state.units ?? [];
    const broken = units.filter(u => !u.healthy);
    const titles = {ok: 'Protected', busy: 'Scanning', warn: 'Attention', threat: 'Threat detected'};
    let subtitle = '';
    if (state.status === 'threat')
        subtitle = verdictText(state.scan, t, lang);
    else if (state.status === 'warn')
        subtitle = units.length === 0
            ? t('no ClamAV service found')
            : t('{names} not healthy', {names: broken.slice(0, 2).map(u => u.label).join(', ')});
    else if (state.status === 'ok')
        subtitle = t('all services running');

    const live = liveScan(state, now, t, lang);
    if (state.status === 'busy' && live?.elapsed)
        subtitle = live.elapsed;

    // Proxima varredura: o timer que dispara mais cedo.
    const next = units.map(u => u.next_run).filter(Boolean).sort()[0] ?? null;

    return {
        status: state.status,
        icon: ICONS[state.status] ?? ICONS.warn,
        panelText: panelText(state, live, lang),
        title: t(titles[state.status] ?? 'Attention'),
        subtitle,
        services: units.map(u => ({
            label: u.label,
            healthy: u.healthy,
            running: u.running,
            detail: unitState(u, t),
        })),
        lastScan: {
            text: verdictText(state.scan, t, lang),
            when: relativeTime(state.scan.finished_at, now, t),
            files: state.scan.scanned != null ? t('{n} files', {n: number(state.scan.scanned, lang)}) : null,
            alarming: state.scan.verdict === 'infected',
        },
        nextScan: relativeTime(next, now, t),
        live,
        media: mediaRows(state, now, t, lang, fromDump),
        quarantine: quarantineRows(state, now, t, lang, opts.userName ?? 'user'),
        // Sem o tray, nao ha progresso, notificacao nem varredura sob demanda
        // acompanhada: o painel mostra o retrato e diz de onde ele veio.
        footer: fromDump ? t('tray not running · snapshot from --dump') : null,
        labels,
    };
}
