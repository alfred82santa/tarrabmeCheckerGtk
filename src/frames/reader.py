#!/usr/bin/python
#
# reader.py
# Copyright (C) Alfred 2012 <alfred82santa@gmail.com>
#
# safeTicketApp is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# safeTicketApp is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.


#from gi.repository import Gtk, GdkPixbuf, Gdk
from gi.repository import WebKit, Gtk, Gdk, Soup, Pango, Gio, GLib
from .login import LoginDialog
from .setup import SetupDialog
from audio.pipes import make_notification_emitter
from config import *
from utils import device


class LastResultBox(Gtk.HBox):
    FAIL = "fail"
    SUCCESS = "success"
    WAITING = "waiting"

    READER_SCHEMA = "apps.tarrabme.checker.checker"

    def __init__(self):
        Gtk.HBox.__init__(self)
        self.icon = Gtk.Image()
        self.pack_start(self.icon, False, False, 10)

        self.last_result_label = Gtk.Label()
        self.last_result_label.set_ellipsize(Pango.EllipsizeMode.START)
        # self.last_result_label.set_focus_on_click(False)
        self.pack_start(self.last_result_label, True, True, 10)

        self.set_message()

    def set_message(self, status=WAITING, code=None):
        if status == self.WAITING:
            self.icon.set_from_stock(Gtk.STOCK_DIALOG_WARNING, Gtk.IconSize.DIALOG)
            self.last_result_label.set_label("No scanned code, yet")
        elif status == self.SUCCESS:
            self.icon.set_from_stock(Gtk.STOCK_APPLY, Gtk.IconSize.DIALOG)
            self.last_result_label.set_label("Success code scan: " + code)
        else:
            self.icon.set_from_stock(Gtk.STOCK_CANCEL, Gtk.IconSize.DIALOG)
            self.last_result_label.set_label("Fail code scan: " + code)


class Reader(Gtk.VBox):
    CONFIG_SCHEMA = "apps.tarrabme.checker.checker"

    def __init__(self, parent, app, name='default', label='Default', *args, **kwargs):
        Gtk.VBox.__init__(self, *args, **kwargs)
        self.parent = parent
        self.app = app

        schema = self.app.sss.lookup(self.CONFIG_SCHEMA, False)

        self.settings = Gio.Settings.new_full(schema, None,
                                              "/apps/tarrabme/checker/{0}/".format(name))

        self.toolbar = Gtk.HeaderBar()
        self.toolbar.set_subtitle(label)
        self.get_style_context().add_class("titlebar")

        self.login_button = Gtk.Button()

        icon = Gtk.Image()
        icon.set_from_icon_name("avatar-default-symbolic", Gtk.IconSize.BUTTON)

        self.login_button.add(icon)
        self.login_button.set_property("visible", True)
        self.login_button.set_property("can_focus", False)

        self.toolbar.pack_start(self.login_button)

        self.login_button.connect("clicked", self.on_click_login)

        self.pack_start(self.toolbar, False, False, 0)

        self.setup_button = Gtk.Button()

        icon = Gtk.Image()
        icon.set_from_icon_name("preferences-system-symbolic", Gtk.IconSize.BUTTON)

        self.setup_button.add(icon)
        self.setup_button.set_property("visible", True)
        self.setup_button.set_property("can_focus", False)
        self.toolbar.pack_end(self.setup_button)

        self.setup_button.connect("clicked", self.on_click_setup)

        self.info_bar_scanner = Gtk.InfoBar()
        self.info_bar_scanner.set_message_type(Gtk.MessageType.ERROR)
        self.info_bar_scanner.set_show_close_button(False)
        self.info_bar_scanner.get_content_area().add(Gtk.Label("No scanner selected"))

        self.pack_start(self.info_bar_scanner, False, False, 0)

        self.waiter = Gtk.ProgressBar()
        self.pack_start(self.waiter, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        self.browser = WebKit.WebView()

        scrolled_window.add(self.browser)
        self.pack_start(scrolled_window, True, True, 0)

        self.last_result_box = LastResultBox()
        self.pack_start(self.last_result_box, False, False, 0)

        man = Gdk.Display.get_default().get_device_manager()
        man.connect("device-removed", self.on_device_removed)

        self.socket = Soup.SessionAsync()
        self.scanner_id = None
        self.reset_reader()
        self.unblock()

    def reset_reader(self):
        self.barcode_scanned = None
        self.last_barcode_scanned = None
        self.last_status_code = None
        self.set_scanner()
        self.reset_browser()
        self.waiter.set_fraction(0)
        self.last_result_box.set_message()

        self._scanner_device = None
        self._sound_device = None

        self._cache_keypress = ''

        self._reload_config()
        self.unblock()

    def _reload_config(self):
        self.set_scanner(self._scanner_device)

        self._check_warns()

        self.sounds_emiter = make_notification_emitter(
            name=self.toolbar.get_subtitle(),
            device_id=self._sound_device,
            balance=self.settings.get_string("sound-card-channel"),
            volume_general=self.settings.get_double("volume-general"),
            volume_read=self.settings.get_double("volume-read"),
            volume_success=self.settings.get_double("volume-success"),
            volume_fail=self.settings.get_double("volume-fail"))

    def reset_browser(self):
        self.browser.set_sensitive(False)
        self.browser.load_string(
            "",
            "text/html",
            "UTF-8",
            ""
        )

    def set_scanner(self, scanner_id=None):
        if self.scanner_id is not None:
            dev = device.get_device_by_id(self.scanner_id)
            if dev is not None:
                dev.ungrab(Gdk.CURRENT_TIME)
        dev = device.get_device_by_id(scanner_id)
        if (scanner_id is None) or (dev is None):
            self.scanner_id = None
            return

        self.scanner_id = scanner_id
        self.get_window().set_support_multidevice(True)
        self.get_window().set_device_events(dev, Gdk.EventMask.ALL_EVENTS_MASK)
        dev.grab(self.get_window(),
                 Gdk.GrabOwnership.NONE, True, Gdk.EventMask.ALL_EVENTS_MASK,
                 None, Gdk.CURRENT_TIME)
        dev.set_mode(Gdk.InputMode.SCREEN)

    def on_click_login(self, button):
        dialog = LoginDialog(self.parent)
        dialog.set_modal(True)
        dialog.set_title(dialog.get_title() + " " + self.toolbar.get_subtitle())
        dialog.set_transient_for(self.parent)
        dialog.set_settings(self.general_settings)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            self.socket.add_feature(dialog.cookieJar)
            self.username = dialog.username
            self.toolbar.set_title(self.username)
            #self.login_button.set_label("Logged as " + self.username)
        dialog.destroy()

    def on_click_setup(self, button):
        dialog = SetupDialog(self.app, self.parent, settings=self.settings)
        dialog.set_modal(True)
        dialog.set_title(dialog.get_title() + " " + self.toolbar.get_subtitle())
        dialog.set_transient_for(self.parent)

        self.settings.delay()
        if dialog.run() == Gtk.ResponseType.OK:
            self.settings.apply()
            self._save_config(dialog)
        else:
            self.settings.revert()
        dialog.destroy()
        self._reload_config()

    def _save_config(self, dialog):
        self._scanner_device = dialog.get_scanner_device()
        self._sound_device = dialog.get_sound_device()
        self.settings.apply()

    def _check_warns(self):
        if self.scanner_id:
            self.info_bar_scanner.hide()
        else:
            self.info_bar_scanner.show()

    def on_response(self, session, message, data):
        if self.last_status_code is None:
            self.last_result_box.set_message(LastResultBox.WAITING, None)
        elif self.last_status_code == 201:
            self.last_result_box.set_message(LastResultBox.SUCCESS, self.last_barcode_scanned)
        else:
            self.last_result_box.set_message(LastResultBox.FAIL, self.last_barcode_scanned)

        message.props.response_body.flatten()
        self.browser.load_string(
            message.props.response_body.data,
            "text/html",
            "UTF-8",
            message.get_uri().to_string(False)
        )

        self.last_barcode_scanned = self.barcode_scanned
        self.last_status_code = message.props.status_code
        if (message.props.status_code == 201):
            self.sounds_emiter.play_notification('success')
        else:
            self.sounds_emiter.play_notification('fail')
        self._blocked = False
        GLib.timeout_add_seconds(10, self.unblock)

    def unblock(self):
        self._blocked = False
        print("eee")
        return False

    def block(self):
        self._blocked = True

    def on_scan_barcode(self, code):
        if self._blocked:
            return
        self.block()
        self.sounds_emiter.play_notification('read')
        self.barcode_scanned = code
        baseurl = self.general_setting.get_string("baseurl").strip('/')
        attempt_path = self.general_setting.get_string("attempt-path").strip('/').replace('%code%', code)
        url = baseurl + "/" + attempt_path
        message = Soup.Message.new("GET", url)
        self.socket.queue_message(message, self.on_response, None)
        self.reset_browser()

    def on_device_removed(self, device_manager, device):
        print(dir(device.props))
        if self.scanner_id == str(device.props.device_id):
            self.scanner_id = None
            self._scanner_device = None
        self._check_warns()
