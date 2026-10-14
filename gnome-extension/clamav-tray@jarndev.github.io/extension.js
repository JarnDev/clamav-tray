// Painel do clamav-tray na barra do GNOME — camada fina sobre o programa.
//
// O programa (Python) decide tudo e publica em $XDG_RUNTIME_DIR/clamav-tray/state.json
// a cada atualizacao. Esta extensao so le esse arquivo e desenha (model.js faz o
// texto; aqui so ha widgets). Nada sobre o ClamAV e decidido em JavaScript.
//
// Regras que valem para o arquivo inteiro:
// - TUDO que enable() cria, disable() desfaz: o shell chama disable() ao bloquear
//   a tela e ao desligar a extensao, e o que sobrar vaza para a sessao.
// - Nada bloqueia o shell: leitura de arquivo so assincrona.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {staleAfter, viewModel} from './model.js';

// Ler um arquivo pequeno em tmpfs a cada 5 s custa menos que observar o arquivo:
// o tray o substitui por rename (escrita atomica), e um FileMonitor teria de
// acompanhar troca de inode — mais um objeto para desfazer, para ganho nenhum.
const POLL_SECS = 5;

// Sem state.json fresco, o painel pergunta ao proprio programa (--dump --json).
// Isso SOBE UM PROCESSO Python que consulta o systemd: a cada 30 s, nunca dois ao
// mesmo tempo, e com teto de 20 s — senao a extensao custaria mais que o tray.
const DUMP_EVERY_SECS = 30;
const DUMP_TIMEOUT_SECS = 20;

// O teto e o `timeout` do coreutils, e nao um temporizador aqui: se o shell
// morrer com um --dump em curso (logout, crash), disable() nao roda e o filho
// ficaria orfao — visto no teste. Sob `timeout`, ele morre sozinho.
function withTimeout(argv) {
    const timeout = GLib.find_program_in_path('timeout');
    return timeout ? [timeout, '--kill-after=5', String(DUMP_TIMEOUT_SECS), ...argv] : argv;
}

// Onde esta o clamav-tray. O PATH do gnome-shell costuma nao ter ~/.local/bin,
// que e onde o pipx instala — por isso o caminho explicito. CLAMAV_TRAY_COMMAND
// e so para desenvolvimento (scripts/dev-nested-shell.sh roda o do repositorio).
function findCommand() {
    const dev = GLib.getenv('CLAMAV_TRAY_COMMAND');
    if (dev)
        return GLib.shell_parse_argv(dev)[1];
    const local = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'clamav-tray']);
    const found = GLib.find_program_in_path('clamav-tray') ??
        (GLib.file_test(local, GLib.FileTest.IS_EXECUTABLE) ? local : null);
    return found ? [found] : null;
}

// Sem state.json nao ha campo `language`: o painel cai no idioma da sessao, para
// "tray parado" nao aparecer em ingles numa sessao em portugues.
function sessionLanguage() {
    return GLib.get_language_names().some(l => l.startsWith('pt')) ? 'pt_BR' : 'en';
}

// Linha de cartao: bolinha com o tom, nome, detalhe a direita e, embaixo, uma
// nota opcional (ponto de montagem, "conferida hoje 03:00").
function cardRow(tone, label, detail, note) {
    const row = new PopupMenu.PopupBaseMenuItem({reactive: false});
    row.add_child(new St.Label({text: '●', style_class: `clamav-tray-dot clamav-tray-${tone}`, y_align: Clutter.ActorAlign.START}));
    const col = new St.BoxLayout({vertical: true, x_expand: true});
    const top = new St.BoxLayout({x_expand: true});
    top.add_child(new St.Label({text: label, x_expand: true}));
    if (detail)
        top.add_child(new St.Label({text: detail, style_class: `clamav-tray-detail ${tone === 'threat' ? 'clamav-tray-threat' : 'clamav-tray-dim'}`}));
    col.add_child(top);
    if (note)
        col.add_child(new St.Label({text: note, style_class: 'clamav-tray-dim'}));
    row.add_child(col);
    return row;
}

// Barra de progresso: trilho do tema e preenchimento proporcional, so CSS (as
// cores ficam no stylesheet, com as regras de contraste). Sem fracao — sem
// contagem real — o trilho fica vazio: nada de porcentagem inventada nem de
// animacao, que seria mais um timer para desfazer.
function progressBar() {
    // BoxLayout horizontal: o preenchimento, primeiro filho, fica colado a esquerda.
    const track = new St.BoxLayout({style_class: 'clamav-tray-bar', x_expand: true});
    const fill = new St.Widget({style_class: 'clamav-tray-bar-fill', y_expand: true});
    track.add_child(fill);
    let fraction = null;
    const apply = () => {
        fill.visible = fraction !== null;
        // Fora da tela (menu sendo montado) nao ha largura para medir; o
        // notify::width da alocacao chama de novo.
        if (fill.visible && track.get_stage())
            fill.width = Math.round(track.width * fraction);
    };
    // A largura so e conhecida depois da alocacao; o sinal morre com o trilho.
    track.connect('notify::width', apply);
    return {
        actor: track,
        set(f) {
            fraction = f;
            apply();
        },
    };
}

// O que muda a cada atualizacao durante a varredura. Fora isso, mudou a
// estrutura do painel e ele precisa ser reconstruido.
function structureKey(vm) {
    const {subtitle, panelText: _p, live, ...rest} = vm;
    return JSON.stringify({...rest, subtitle: subtitle !== '', live: live ? {percent: live.percent !== null} : null});
}

const Indicator = class {
    constructor(name) {
        this.button = new PanelMenu.Button(0.0, name, false);
        this.icon = new St.Icon({
            icon_name: 'security-medium-symbolic',
            style_class: 'system-status-icon clamav-tray-icon-stale',
        });
        this.label = new St.Label({
            text: '', y_align: Clutter.ActorAlign.CENTER, style_class: 'clamav-tray-panel-text', visible: false,
        });
        const box = new St.BoxLayout();
        box.add_child(this.icon);
        box.add_child(this.label);
        this.button.add_child(box);
        this._lastKey = null;
        this._lastStructure = null;
        this._pending = null;
        this._live = null;
        // Reconstruir com o menu aberto faz o conteudo pular sob o cursor: adia.
        this._openId = this.button.menu.connect('open-state-changed', (_m, open) => {
            if (!open && this._pending) {
                const v = this._pending;
                this._pending = null;
                this._render(v);
            }
        });
    }

    update(vm) {
        this.icon.icon_name = vm.icon;
        this.icon.style_class = `system-status-icon clamav-tray-icon-${vm.status}`;
        this.label.text = vm.panelText;
        this.label.visible = vm.panelText !== '';
        const key = JSON.stringify(vm);
        if (key === this._lastKey)
            return;
        this._lastKey = key;
        const structure = structureKey(vm);
        if (!this.button.menu.isOpen) {
            this._render(vm);
        } else if (structure === this._lastStructure && !this._pending) {
            // Menu aberto e mesma estrutura: so os numeros da varredura mudaram.
            // Atualiza no lugar — a barra anda com o painel aberto, sem pular.
            this._patchLive(vm);
        } else {
            this._pending = vm;
        }
    }

    _patchLive(vm) {
        const l = this._live;
        if (!l)
            return;
        l.subtitle?.set_text(vm.subtitle);
        if (vm.live) {
            l.percent?.set_text(vm.live.percent ?? '');
            l.bar.set(vm.live.fraction);
            l.detail?.set_text(vm.live.detail);
        }
    }

    _render(vm) {
        const menu = this.button.menu;
        menu.removeAll();
        this._lastStructure = structureKey(vm);
        this._live = {};

        // Cabecalho: estado em uma linha, com a cor dele.
        const head = new PopupMenu.PopupBaseMenuItem({reactive: false, style_class: 'clamav-tray-head'});
        const box = new St.BoxLayout({vertical: true, x_expand: true});
        box.add_child(new St.Label({text: vm.title, style_class: `clamav-tray-title clamav-tray-${vm.status}`}));
        if (vm.subtitle) {
            this._live.subtitle = new St.Label({text: vm.subtitle, style_class: 'clamav-tray-subtitle'});
            box.add_child(this._live.subtitle);
        }
        head.add_child(box);
        menu.addMenuItem(head);

        if (vm.live) {
            const item = new PopupMenu.PopupBaseMenuItem({reactive: false});
            const col = new St.BoxLayout({vertical: true, x_expand: true});
            const top = new St.BoxLayout({x_expand: true});
            top.add_child(new St.Label({text: vm.labels.live, x_expand: true, style_class: 'clamav-tray-strong'}));
            if (vm.live.percent !== null) {
                this._live.percent = new St.Label({text: vm.live.percent, style_class: 'clamav-tray-strong clamav-tray-busy'});
                top.add_child(this._live.percent);
            }
            col.add_child(top);
            this._live.bar = progressBar();
            this._live.bar.set(vm.live.fraction);
            col.add_child(this._live.bar.actor);
            this._live.detail = new St.Label({text: vm.live.detail, style_class: 'clamav-tray-dim'});
            col.add_child(this._live.detail);
            item.add_child(col);
            menu.addMenuItem(item);
        }

        if (vm.lastScan) {
            menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem(vm.labels.lastScan));
            const scan = new PopupMenu.PopupBaseMenuItem({reactive: false});
            const col = new St.BoxLayout({vertical: true, x_expand: true});
            col.add_child(new St.Label({
                text: vm.lastScan.text,
                style_class: vm.lastScan.alarming ? 'clamav-tray-threat' : 'clamav-tray-strong',
            }));
            const meta = [vm.lastScan.when, vm.lastScan.files].filter(Boolean).join(' · ');
            if (meta)
                col.add_child(new St.Label({text: meta, style_class: 'clamav-tray-dim'}));
            if (vm.nextScan)
                col.add_child(new St.Label({text: `${vm.labels.nextScan}: ${vm.nextScan}`, style_class: 'clamav-tray-dim'}));
            scan.add_child(col);
            menu.addMenuItem(scan);
        }

        if (vm.services.length) {
            menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem(vm.labels.services));
            for (const s of vm.services) {
                const row = new PopupMenu.PopupBaseMenuItem({reactive: false});
                const dot = s.running ? 'busy' : s.healthy ? 'ok' : 'warn';
                row.add_child(new St.Label({text: '●', style_class: `clamav-tray-dot clamav-tray-${dot}`, y_align: Clutter.ActorAlign.CENTER}));
                row.add_child(new St.Label({text: s.label, x_expand: true, y_align: Clutter.ActorAlign.CENTER}));
                if (s.detail)
                    row.add_child(new St.Label({text: s.detail, style_class: 'clamav-tray-detail clamav-tray-dim', y_align: Clutter.ActorAlign.CENTER}));
                menu.addMenuItem(row);
            }
        }

        if (vm.media.length) {
            menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem(vm.labels.devices));
            for (const m of vm.media)
                menu.addMenuItem(cardRow(m.tone, m.label, m.detail, m.mountpoint));
        }

        if (vm.quarantine.length) {
            menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem(vm.labels.quarantine));
            for (const q of vm.quarantine)
                menu.addMenuItem(cardRow(q.tone, q.owner, q.detail, q.note));
        }

        if (vm.footer) {
            menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            const foot = new PopupMenu.PopupBaseMenuItem({reactive: false});
            foot.add_child(new St.Label({text: vm.footer, style_class: 'clamav-tray-dim'}));
            menu.addMenuItem(foot);
        }
    }

    destroy() {
        this._live = null;
        this.button.menu.disconnect(this._openId);
        this.button.destroy();
    }
};

export default class ClamavTrayExtension extends Extension {
    enable() {
        this._indicator = new Indicator(this.metadata.name);
        Main.panel.addToStatusArea(this.uuid, this._indicator.button);
        this._file = Gio.File.new_for_path(
            GLib.build_filenamev([GLib.get_user_runtime_dir(), 'clamav-tray', 'state.json']));
        this._cancellable = new Gio.Cancellable();
        this._userName = GLib.get_user_name();
        this._lastDump = 0;
        this._dumpState = null;
        this._proc = null;
        this._poll();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, POLL_SECS, () => {
            this._poll();
            return GLib.SOURCE_CONTINUE;
        });
        // So desenvolvimento (scripts/dev-nested-shell.sh): abre o painel sozinho
        // para o screenshot, ja que no shell aninhado nao ha como clicar por script.
        // A sessao real nunca tem esta variavel.
        // O shell sobe na visao geral, e a transicao dela fecha um menu aberto
        // cedo demais: sai dela aos 3 s e abre o menu aos 5 s.
        if (GLib.getenv('CLAMAV_TRAY_DEV_OPEN') === '1') {
            let tick = 0;
            this._devOpen = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
                tick++;
                if (tick === 3)
                    Main.overview.hide();
                if (tick < 5)
                    return GLib.SOURCE_CONTINUE;
                this._devOpen = 0;
                this._indicator?.button.menu.open();
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    _poll() {
        this._file.load_contents_async(this._cancellable, (file, res) => {
            let state = null;
            try {
                const [, bytes] = file.load_contents_finish(res);
                state = JSON.parse(new TextDecoder().decode(bytes));
            } catch (e) {
                // Cancelado no disable(): o indicador ja nao existe, nao toque nele.
                if (e instanceof GLib.Error && e.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                    return;
                // Sem arquivo (tray parado) ou JSON quebrado: segue para o --dump.
            }
            const now = new Date();
            const fresh = state && (now - new Date(state.generated_at)) / 1000 <= staleAfter(state);
            this._fresh = fresh;
            if (fresh) {
                this._dumpState = null;
                this._show(state, now, {});
                return;
            }
            this._maybeDump(now);
            // Ate o primeiro --dump responder (ou se ele falhar), o painel mostra
            // "tray parado" — nunca um escudo verde por omissao.
            this._show(this._dumpState ?? state, now, {reason: this._command === null ? 'no-command' : undefined});
        });
    }

    _show(state, now, opts) {
        this._indicator?.update(viewModel(state, now, sessionLanguage(), {userName: this._userName, ...opts}));
    }

    _maybeDump(now) {
        if (this._proc || now - this._lastDump < DUMP_EVERY_SECS * 1000)
            return;
        this._lastDump = now.getTime();
        this._command = findCommand();
        if (!this._command)
            return;
        let proc;
        try {
            proc = Gio.Subprocess.new(withTimeout([...this._command, '--dump', '--json']),
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
        } catch (e) {
            this._dumpState = null;
            return;
        }
        this._proc = proc;
        proc.communicate_utf8_async(null, this._cancellable, (p, res) => {
            let out = null;
            try {
                [, out] = p.communicate_utf8_finish(res);
            } catch (e) {
                if (e instanceof GLib.Error && e.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                    return;
            }
            this._proc = null;
            let state = null;
            if (p.get_successful() && out) {
                try {
                    state = JSON.parse(out);
                } catch (e) {
                    state = null;
                }
            }
            // So aceita o que se apresenta como --dump: outra coisa no lugar do
            // comando nao vira escudo verde.
            this._dumpState = state?.producer === 'dump' ? state : null;
            // O tray pode ter voltado enquanto o --dump rodava: o state.json vence.
            if (!this._fresh)
                this._show(this._dumpState, new Date(), {});
        });
    }

    disable() {
        if (this._devOpen) {
            GLib.Source.remove(this._devOpen);
            this._devOpen = 0;
        }
        if (this._timer) {
            GLib.Source.remove(this._timer);
            this._timer = 0;
        }
        this._cancellable?.cancel();
        this._cancellable = null;
        // Cancelar a leitura nao mata o filho: o --dump em curso morre aqui. TERM,
        // nao force_exit() (KILL): o `timeout` repassa TERM ao filho; KILL mataria
        // so o `timeout` e deixaria o --dump orfao.
        this._proc?.send_signal(15);
        this._proc = null;
        this._dumpState = null;
        this._indicator?.destroy();
        this._indicator = null;
        this._file = null;
    }
}
