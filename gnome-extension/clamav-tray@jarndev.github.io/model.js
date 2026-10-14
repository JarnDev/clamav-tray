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

// 3 atualizacoes do tray (10 s cada) sem arquivo novo = tray parado. Uma so de
// atraso acontece com a maquina ocupada; tres, nao.
export const STALE_SECS = 30;

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
    },
};

// Separadores (milhar, decimal), como i18n.SEPARATORS no Python.
const SEPARATORS = {en: [',', '.'], pt_BR: ['.', ',']};

export function translator(lang) {
    const cat = CATALOG[lang] ?? {};
    return (key, vars = {}) =>
        (cat[key] ?? key).replace(/\{(\w+)\}/g, (_m, k) => String(vars[k] ?? ''));
}

export function number(n, lang) {
    const [thousands] = SEPARATORS[lang] ?? SEPARATORS.en;
    return String(Math.trunc(n)).replace(/\B(?=(\d{3})+(?!\d))/g, thousands);
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

// state: o JSON (objeto), ou null se nao havia arquivo. now: Date.
// fallbackLang: idioma da sessao, usado quando nao ha arquivo (sem `language`).
export function viewModel(state, now, fallbackLang = 'en') {
    const lang = state?.language ?? fallbackLang;
    const t = translator(lang);

    const labels = {services: t('Services'), lastScan: t('Last scan'), nextScan: t('Next scan')};
    const ageSecs = state ? (now - new Date(state.generated_at)) / 1000 : Infinity;
    if (!state || ageSecs > STALE_SECS) {
        return {
            status: 'stale',
            icon: ICONS.stale,
            title: t('Tray not running'),
            subtitle: state ? t('no update for {n} min', {n: Math.max(1, Math.round(ageSecs / 60))}) : '',
            services: [],
            lastScan: null,
            nextScan: null,
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

    // Proxima varredura: o timer que dispara mais cedo.
    const next = units.map(u => u.next_run).filter(Boolean).sort()[0] ?? null;

    return {
        status: state.status,
        icon: ICONS[state.status] ?? ICONS.warn,
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
        labels,
    };
}
