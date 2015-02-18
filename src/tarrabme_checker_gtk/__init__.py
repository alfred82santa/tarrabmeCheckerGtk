
__author__ = 'alfred'

import os
from .frames import Reader
from .dialogs import PreferencesDialog
from gi.repository import Gtk, Gdk, GObject, Gio, GLib, Gst, GdkPixbuf, GtkClutter

MEDIA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'media')
CONFIG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'config')


class TarrabmeCheckerApp(Gtk.Application):
    CONFIG_SCHEMA = "apps.tarrabme.checker"

    def __init__(self):
        Gtk.Application.__init__(self, application_id="org.me.tarrab.Checker",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

        self.setting_schema_source = None
        self.settings = None

        self.connect('activate', self.activate_cb)
        self.connect('startup', self.startup_cb)

        GLib.set_application_name("Tarrab.me Checker")
        GLib.set_prgname('tarrabme_checker_gtk-Checker')

        self.register(None)

        if self.get_is_remote():
            print("Application already running")
            self.quit()

    def startup_cb(self, app):
        GObject.threads_init()
        Gst.init(None)
        GtkClutter.init()

        resource = Gio.Resource.load(os.path.join(MEDIA_PATH, "tarrabme-checker-resources.gresource"))
        Gio.resources_register(resource)

        self.load_config()

        self.style_provider = Gtk.CssProvider()
        style_file = Gio.File.new_for_uri('resource://org/me/tarrab/Checker/style.css')
        self.style_provider.load_from_file(style_file)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self.style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        icon = GdkPixbuf.Pixbuf.new_from_resource('/org/me/tarrab/Checker/tarrab-me-icon.png')

        action = Gio.SimpleAction.new('preferences', None)
        action.connect('activate', self.preferences_cb)
        self.add_action(action)

        action = Gio.SimpleAction.new('quit', None)
        action.connect('activate', self.quit_cb)
        self.add_action(action)

        app_menu = Gio.Menu()
        app_menu.append('Preferences', 'app.preferences')
        app_menu.append('Quit', 'app.quit')

        self.set_app_menu(app_menu)

        for win in range(self.settings.get_int("window-count")):
            window = Gtk.ApplicationWindow(self, type=Gtk.WindowType.TOPLEVEL)
            window.set_icon(icon)
            window.set_wmclass("tarrab_checker", "tarrab.me Checker")
            window.set_title("tarrab.me Checker")
            window.set_default_size(790, 450)

            self.toolbar = Gtk.HeaderBar()
            self.toolbar.set_halign(Gtk.Align.FILL)

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.set_homogeneous(True)

            window.set_titlebar(box)

            self.add_window(window)

            grid = Gtk.Grid()
            grid.set_row_homogeneous(True)
            grid.set_column_homogeneous(True)

            for row in range(self.settings.get_int("row-count")):
                grid.insert_row(0)
            for column in range(self.settings.get_int("column-count")):
                grid.insert_column(0)

            row_count = self.settings.get_int("row-count")
            column_count = self.settings.get_int("column-count")
            index = 0
            for row in range(row_count):
                for column in range(column_count):
                    index += 1
                    reader = Reader(window, self, "reader_" + str(index),
                                    label="Reader " + str(index))

                    grid.attach(reader, column, row, 1, 1)

                    if row == 0:
                        reader.remove(reader.toolbar)
                        box.pack_start(reader.toolbar, True, True, 10)

            window.add(grid)
            window.show_all()

    def load_config(self):
        self.setting_schema_source = Gio.SettingsSchemaSource.new_from_directory(CONFIG_PATH, None, False)
        schema = self.setting_schema_source.lookup(self.CONFIG_SCHEMA, False)
        self.settings = Gio.Settings.new_full(schema, None, None)

    def preferences_cb(self, *args):
        dialog = PreferencesDialog(self.settings)
        icon = GdkPixbuf.Pixbuf.new_from_resource('/org/me/tarrab/Checker/tarrab-me-icon.png')
        dialog.set_icon(icon)
        self.settings.delay()
        if dialog.run() == Gtk.ResponseType.OK:
            self.settings.apply()
        else:
            self.settings.revert()
        dialog.destroy()

    def quit_cb(self, *args):
        self.quit()

    def on_commandline(self, app, command_line):
        return 0

    def activate_cb(self, app):
        pass

    def destroy(self, window):
        self.quit()