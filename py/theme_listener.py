"""Optional live theme listener for macOS and Linux."""

import sys
import threading


def start(on_theme_change):
    """Start a background listener for OS theme changes.

    Calls on_theme_change(theme_name) when the system switches dark/light.
    Silently does nothing if the required libraries are not available.
    """
    if sys.platform == "darwin":
        _start_macos(on_theme_change)
    elif sys.platform == "win32":
        sys.exit("OS not supported")
    else:
        _start_linux(on_theme_change)


def _start_macos(on_theme_change):
    import subprocess
    import time

    def _is_dark():
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True, text=True
        )
        return result.stdout.strip() == "Dark"

    def run():
        current = _is_dark()
        while True:
            time.sleep(2)
            new = _is_dark()
            if new != current:
                current = new
                on_theme_change("textual-dark" if current else "textual-light")

    threading.Thread(target=run, daemon=True).start()


def _start_linux(on_theme_change):
    try:
        import gi
        gi.require_version('Gio', '2.0')
        from gi.repository import Gio, GLib
    except ImportError:
        return

    def on_setting_changed(proxy, sender_name, signal_name, parameters):
        namespace, key, value = parameters
        if namespace == "org.freedesktop.appearance" and key == "color-scheme":
            on_theme_change("textual-dark" if value.unpack() == 1 else "textual-light")

    def run():
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            proxy = Gio.DBusProxy.new_sync(
                bus, Gio.DBusProxyFlags.NONE, None,
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Settings",
                None,
            )
            proxy.connect("g-signal", on_setting_changed)
            GLib.MainLoop().run()
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()
