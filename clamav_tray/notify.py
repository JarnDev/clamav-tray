"""Notificacao na area de trabalho, pela interface padrao do freedesktop.

Fala direto com org.freedesktop.Notifications pelo D-Bus de sessao, via Gio, que
ja vem no PyGObject. Alternativas descartadas:

- libnotify (gir1.2-notify-0.7): mais uma dependencia de sistema para instalar
  pela distro, so para uma chamada.
- notify-send: um processo por notificacao, e nem toda distro o instala.
- Gio.Notification: exige GApplication registrada com .desktop correspondente,
  que um indicador de bandeja nao e.

NUNCA pode derrubar o tray. Sem servidor de notificacao (sessao minima, alguns
WMs), a chamada falha e isso e ignorado: o menu continua mostrando o resultado.
"""

from __future__ import annotations

from gi.repository import Gio, GLib

_URGENCY_NORMAL, _URGENCY_CRITICAL = 1, 2


def send(title: str, body: str, icon: str, urgent: bool = False) -> bool:
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        params = GLib.Variant(
            "(susssasa{sv}i)",
            ("ClamAV", 0, icon, title, body, [],
             {"urgency": GLib.Variant("y", _URGENCY_CRITICAL if urgent else _URGENCY_NORMAL)},
             -1),
        )
        # Assincrono e sem callback: o loop do GTK nao espera o servidor responder.
        bus.call("org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                 "org.freedesktop.Notifications", "Notify", params,
                 None, Gio.DBusCallFlags.NONE, 5000, None, None, None)
        return True
    except GLib.Error:
        return False
