// F0 — prova de conceito: um botao na barra, e nada mais. Serve para provar o
// ciclo enable/disable no shell aninhado antes de qualquer logica.
//
// Regra que vale para todas as fases: TUDO que enable() cria, disable() desfaz.
// O shell chama disable() ao bloquear a tela e ao desligar a extensao; o que
// sobrar vaza para a sessao do usuario.

import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

export default class ClamavTrayExtension extends Extension {
    enable() {
        this._button = new PanelMenu.Button(0.0, this.metadata.name, false);
        this._button.add_child(new St.Icon({
            icon_name: 'security-high-symbolic',
            style_class: 'system-status-icon',
        }));
        Main.panel.addToStatusArea(this.uuid, this._button);
        console.log(`[clamav-tray] enable: botao na barra`);
    }

    disable() {
        this._button?.destroy();
        this._button = null;
        console.log(`[clamav-tray] disable: botao removido`);
    }
}
