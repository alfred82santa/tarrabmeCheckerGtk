from gi.repository import Gtk, Gio

__author__ = 'alfred'


class PreferencesDialog(Gtk.Dialog):

    def __init__(self, settings):
        Gtk.Dialog.__init__(self, "Preferences", None,
                            Gtk.DialogFlags.USE_HEADER_BAR | Gtk.DialogFlags.MODAL,
                            [], use_header_bar=True)

        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        button = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        button.get_style_context().add_class('suggested-action')
        self.settings = settings
        self.set_default_size(490, 350)

        self.builder = Gtk.Builder.new_from_resource('/org/me/tarrab/Checker/tarrabme-preferences.ui')

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.builder.get_object('PerferencesView'))

        entry = self.builder.get_object('basepath_entry')
        self.settings.bind('baseurl', entry, 'text', Gio.SettingsBindFlags.DEFAULT)

        entry = self.builder.get_object('login_endpoint_entry')
        self.settings.bind('login-path', entry, 'text', Gio.SettingsBindFlags.DEFAULT)

        combo = self.builder.get_object('login_method_combo')
        self.settings.bind('login-method', combo, 'active_id', Gio.SettingsBindFlags.DEFAULT)

        entry = self.builder.get_object('logout_endpoint_entry')
        self.settings.bind('logout-path', entry, 'text', Gio.SettingsBindFlags.DEFAULT)

        combo = self.builder.get_object('logout_method_combo')
        self.settings.bind('logout-method', combo, 'active_id', Gio.SettingsBindFlags.DEFAULT)

        entry = self.builder.get_object('attempt_endpoint_entry')
        self.settings.bind('attempt-path', entry, 'text', Gio.SettingsBindFlags.DEFAULT)

        combo = self.builder.get_object('attempt_method_combo')
        self.settings.bind('attempt-method', combo, 'active_id', Gio.SettingsBindFlags.DEFAULT)

        entry = self.builder.get_object('attempt_list_endpoint_entry')
        self.settings.bind('attempt-list-path', entry, 'text', Gio.SettingsBindFlags.DEFAULT)

        combo = self.builder.get_object('attempt_list_method_combo')
        self.settings.bind('attempt-list-method', combo, 'active_id', Gio.SettingsBindFlags.DEFAULT)

        entry = self.builder.get_object('account_entry')
        self.settings.bind('account-path', entry, 'text', Gio.SettingsBindFlags.DEFAULT)

        adjustment = self.builder.get_object('windows_adjustment')
        self.settings.bind('window-count', adjustment, 'value', Gio.SettingsBindFlags.DEFAULT)

        adjustment = self.builder.get_object('columns_adjustment')
        self.settings.bind('column-count', adjustment, 'value', Gio.SettingsBindFlags.DEFAULT)

        adjustment = self.builder.get_object('rows_adjustment')
        self.settings.bind('row-count', adjustment, 'value', Gio.SettingsBindFlags.DEFAULT)

        self.get_content_area().pack_start(scrolled_window, True, True, 0)
        self.show_all()
