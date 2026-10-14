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

import {viewModel} from './model.js';

// Ler um arquivo pequeno em tmpfs a cada 5 s custa menos que observar o arquivo:
// o tray o substitui por rename (escrita atomica), e um FileMonitor teria de
// acompanhar troca de inode — mais um objeto para desfazer, para ganho nenhum.
const POLL_SECS = 5;

// Sem state.json nao ha campo `language`: o painel cai no idioma da sessao, para
// "tray parado" nao aparecer em ingles numa sessao em portugues.
function sessionLanguage() {
    return GLib.get_language_names().some(l => l.startsWith('pt')) ? 'pt_BR' : 'en';
}

const Indicator = class {
    constructor(name) {
        this.button = new PanelMenu.Button(0.0, name, false);
        this.icon = new St.Icon({
            icon_name: 'security-medium-symbolic',
            style_class: 'system-status-icon clamav-tray-icon-stale',
        });
        this.button.add_child(this.icon);
        this._lastKey = null;
        this._pending = null;
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
        const key = JSON.stringify(vm);
        if (key === this._lastKey)
            return;
        this._lastKey = key;
        if (this.button.menu.isOpen)
            this._pending = vm;
        else
            this._render(vm);
    }

    _render(vm) {
        const menu = this.button.menu;
        menu.removeAll();

        // Cabecalho: estado em uma linha, com a cor dele.
        const head = new PopupMenu.PopupBaseMenuItem({reactive: false, style_class: 'clamav-tray-head'});
        const box = new St.BoxLayout({vertical: true, x_expand: true});
        box.add_child(new St.Label({text: vm.title, style_class: `clamav-tray-title clamav-tray-${vm.status}`}));
        if (vm.subtitle)
            box.add_child(new St.Label({text: vm.subtitle, style_class: 'clamav-tray-subtitle'}));
        head.add_child(box);
        menu.addMenuItem(head);

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
                    row.add_child(new St.Label({text: s.detail, style_class: 'clamav-tray-dim', y_align: Clutter.ActorAlign.CENTER}));
                menu.addMenuItem(row);
            }
        }
    }

    destroy() {
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
        this._poll();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, POLL_SECS, () => {
            this._poll();
            return GLib.SOURCE_CONTINUE;
        });
        // So desenvolvimento (scripts/dev-nested-shell.sh): abre o painel sozinho
        // para o screenshot, ja que no shell aninhado nao ha como clicar por script.
        // A sessao real nunca tem esta variavel.
        if (GLib.getenv('CLAMAV_TRAY_DEV_OPEN') === '1') {
            this._devOpen = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 3, () => {
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
                // Sem arquivo (tray parado) ou JSON quebrado: state fica null, e o
                // modelo mostra "tray parado" — nunca um escudo verde por omissao.
            }
            this._indicator?.update(viewModel(state, new Date(), sessionLanguage()));
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
        this._indicator?.destroy();
        this._indicator = null;
        this._file = null;
    }
}
