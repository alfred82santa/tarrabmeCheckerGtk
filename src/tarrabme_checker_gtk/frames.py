#!/usr/bin/python
#
# frames.py
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
import json

from gi.repository import Gtk, Soup, Pango, Gio, GtkClutter, Clutter
from .sensors import CameraSensor, KeyboardSensor
from .actuators import BaseActuator, SoundActuator
from .controllers import TarrabmeController, RecentAttemptsController, AutoScanController
from .utils import get_datetime_label
from .treestores import keyboard_store, audio_store, camera_store, KeyboardTreeStore, AudioDeviceTreeStore, \
    CameraTreeStore


class Reader(Gtk.Box):
    CONFIG_SCHEMA = "apps.tarrabme.checker.checker"

    def __init__(self, parent, app, name='default', label='Default', *args, **kwargs):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, *args, **kwargs)
        self.parent = parent
        self.app = app

        self.connect('show', self.show_cb)

        self.sensors = {}
        self.actuators = {}

        self.controller = TarrabmeController(self)
        self.controller.connect('leaving-step', self.leaving_step_cb)
        self.controller.connect('change-step', self.change_step_cb)
        self.controller.connect('result', self.result_cb)
        self.controller.connect('login', self.login_cb)
        self.controller.connect('login-error', self.login_error_cb)
        self.controller.connect('logout', self.login_error_cb)

        schema = self.app.setting_schema_source.lookup(self.CONFIG_SCHEMA, False)
        self.settings = Gio.Settings.new_full(schema, None,
                                              "/apps/tarrabme/checker/{0}/".format(name))

        self.builder = Gtk.Builder.new_from_resource('/org/me/tarrab/Checker/tarrabme-reader.ui')

        self.toolbar = self.builder.get_object('ReaderHeader')
        self.toolbar_title_label = self.builder.get_object('reader_title')
        self.toolbar_title_label.set_label(label)
        self.pack_start(self.toolbar, False, False, 0)

        self.toolbar_username_label = self.builder.get_object('username_title')

        self.info_bar_scanner = self.builder.get_object('infobar_no_scanner')
        self.pack_start(self.info_bar_scanner, False, False, 0)

        self.info_bar_login = self.builder.get_object('infobar_no_login')
        self.pack_start(self.info_bar_login, False, False, 0)

        self.stack = Gtk.Stack()
        self.pack_start(self.stack, True, True, 0)
        self.stack.set_transition_type(Gtk.StackTransitionType.OVER_LEFT)
        self.stack.set_transition_duration(300)

        self.login_button = self.builder.get_object('login_button')
        self.login_button.connect("clicked", self.clicked_login_cb)

        self.logout_button = self.builder.get_object('logout_button')
        self.logout_button.connect("clicked", self.clicked_logout_cb)

        self.setup_button = self.builder.get_object('setup_button')
        self.setup_button.connect("clicked", self.clicked_setup_cb)

        self.camera_button = self.builder.get_object('cam_button')
        self.camera_button.connect("clicked", self.clicked_camera_cb)

        self.scan_button = self.builder.get_object('scan_button')
        self.scan_button.connect("clicked", self.clicked_scan_cb)

        self.last_code = self.builder.get_object('LastCodeView')
        self.pack_start(self.last_code, False, False, 0)

        self.last_stack_controller = RecentAttemptsController(self)
        self.autoscan_controller = AutoScanController(self)

        self.add_actuator('sound', SoundActuator(self.settings))

        self.stack.add_named(SetupFrame(self), 'setup')
        self.stack.add_named(LoginFrame(self), 'login')
        self.stack.add_named(WaitingFrame(self), 'waiting')
        self.stack.add_named(ScanReadyFrame(self), 'scan_ready')
        self.stack.add_named(ResultFrame(self), 'result')
        self.camera_frame = CameraFrame(self)
        self.stack.add_named(self.camera_frame, 'camera')

        self.settings.connect('changed::keyboard', self.changed_keyboard_cb)
        self.changed_keyboard_cb()

    def changed_keyboard_cb(self, *args):
        if self.settings.get_string('keyboard') == '-1':
            self.info_bar_scanner.set_visible(True)
        else:
            self.info_bar_scanner.set_visible(False)

    def show_cb(self, *args):
        self.changed_keyboard_cb()
        self.stack.set_visible_child_name('waiting')
        self.stack.set_visible_child_name('setup')

    def clicked_login_cb(self, button):
        self.controller.set_step(TarrabmeController.STEP_LOGIN)

    def clicked_logout_cb(self, button):
        self.controller.logout()

    def clicked_setup_cb(self, button):
        self.controller.set_step(TarrabmeController.STEP_NOP)

    def clicked_camera_cb(self, button):
        if self.controller.step == TarrabmeController.STEP_SCAN or \
                self.controller.set_step(TarrabmeController.STEP_SCAN):
            self.stack.set_visible_child_name('camera')
            if self.camera_frame.sensor:
                self.camera_frame.sensor.restart()

    def clicked_scan_cb(self, button):
        if self.controller.step == TarrabmeController.STEP_SCAN or \
                self.controller.set_step(TarrabmeController.STEP_SCAN):
            self.stack.set_visible_child_name('scan_ready')

    def leaving_step_cb(self, controller, step, next_step):
        if step == TarrabmeController.STEP_CHECK_LOGIN and next_step == TarrabmeController.STEP_SCAN:
            self.stack.set_visible_child_name('scan_ready')

    def change_step_cb(self, controller, step):
        if step == TarrabmeController.STEP_LOGIN:
            self.stack.set_visible_child_name('login')
        elif step == TarrabmeController.STEP_REQUEST:
            self.stack.set_visible_child_name('waiting')
        elif step == TarrabmeController.STEP_RESPONSE:
            self.stack.set_visible_child_name('result')
        elif step == TarrabmeController.STEP_NOP:
            self.stack.set_visible_child_name('setup')

    def result_cb(self, controller, code, result, data):
        if result == TarrabmeController.RESULT_SUCCESS:
            self.send_action(BaseActuator.SUCCESS_ACTION)
        else:
            self.send_action(BaseActuator.ERROR_ACTION)

    def login_cb(self, controller, data):
        self.info_bar_login.set_visible(False)
        self.toolbar_username_label.set_label(data.data.get('first_name',
                                                            data.data.get('username', '')))

    def login_error_cb(self, *args):
        self.info_bar_login.set_visible(True)
        self.toolbar_username_label.set_label("Not logged in")

    def add_sensor(self, name, sensor):
        self.sensors[name] = {"sensor": sensor,
                              "signal_handler": sensor.connect('scan-code',
                                                               self.scan_code_cb)}

    def get_sensor(self, name):
        return self.sensors[name]['sensor']

    def get_sensor_signal_handler(self, name):
        return self.sensors[name]['signal_handler']

    def scan_code_cb(self, sensor, code):
        self.send_action(BaseActuator.READ_ACTION)
        self.controller.request_new_code(code)

    def add_actuator(self, name, actuator):
        self.actuators[name] = actuator

    def send_action(self, action):
        for actuator in self.actuators.values():
            actuator.action(action)


class BaseChildFrame(Gtk.ScrolledWindow):

    def __init__(self, reader, *args, **kwargs):
        Gtk.ScrolledWindow.__init__(self, *args, **kwargs)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.reader = reader
        self.get_style_context().add_class('reader-frame')


class VideoFrameMixin:

    def __init__(self, *args, **kwargs):
        super(VideoFrameMixin).__init__(*args, **kwargs)
        self.sensor = None
        self.drawingarea = GtkClutter.Embed()
        self.drawingarea.set_size_request(100, 100)
        self.drawingarea.set_vexpand(True)
        self.drawingarea.set_hexpand(True)
        self.drawingarea.get_stage().connect("notify::allocation", self.drawingarea_size_change_cb)
        self.texture = Clutter.Texture()
        self.texture.connect("size-change", self.texture_size_change_cb)
        self.drawingarea.get_stage().add_child(self.texture)

        self.image = Gtk.Image()
        self.image.set_from_icon_name('dialog-warning', Gtk.IconSize.DIALOG)
        self.image.set_no_show_all(True)
        self.drawingarea.set_no_show_all(True)

        self.label = Gtk.Label()
        self.label.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        self.label.set_label('Camera')

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(self.drawingarea, True, True, 0)
        self.box.pack_start(self.image, True, True, 0)
        self.box.pack_start(self.label, False, False, 15)

        self.drawingarea.show()
        self.image.hide()

        self.add(self.box)

        self.connect('realize', self.realize_cb)
        self.connect('unrealize', self.unrealize_cb)

    def scan_code_cb(self, sensor, code):
        self.label.set_label(code)

    def error_cb(self, sensor, error):
        self.label.set_label('Error: {}'.format(error))
        self.drawingarea.hide()
        self.image.show()

    def start_scan_cb(self, sensor):
        self.label.set_label('')
        self.drawingarea.show()
        self.image.hide()

    def realize_cb(self, *args):
        self.sensor = CameraSensor(self.reader.settings, self.texture)
        self.sensor.restart()

    def unrealize_cb(self, *args):
        self.sensor.stop()

    def drawingarea_size_change_cb(self, *args, **kwargs):
        self.texture_size_change_cb(self.texture, *self.texture.get_size())

    def texture_size_change_cb(self, texture, base_width, base_height):
        stage_width, stage_height = texture.get_stage().get_size()

        """
        base_width and base_height are the actual dimensions of the buffers before
        taking the pixel aspect ratio into account. We need to get the actual
        size of the texture to display
        """
        try:
            new_height = (base_height * stage_width) / base_width
            if new_height <= stage_height:
                new_width = stage_width
                new_x = 0
                new_y = (stage_height - new_height) / 2
            else:
                new_width = (base_width * stage_height) / base_height
                new_height = stage_height
                new_x = (stage_width - new_width) / 2
                new_y = 0
            texture.set_position(new_x, new_y)
            texture.set_size(new_width, new_height)
        except ZeroDivisionError:
            pass


class SetupFrame(BaseChildFrame):

    def __init__(self, *args, **kwargs):
        super(SetupFrame, self).__init__(*args, **kwargs)

        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group('setup', self.action_group)
        self.action_group.add_action(self.reader.settings.create_action('sound-card-channel'))

        self.add(self.reader.builder.get_object('SetupView'))

        adjustment = self.reader.builder.get_object('general_volume_adjustment')
        self.reader.settings.bind('volume-general', adjustment, 'value', Gio.SettingsBindFlags.DEFAULT)

        adjustment = self.reader.builder.get_object('read_volume_adjustment')
        self.reader.settings.bind('volume-read', adjustment, 'value', Gio.SettingsBindFlags.DEFAULT)

        button = self.reader.builder.get_object('read_sound_test_button')
        button.connect('clicked',
                       lambda *args: self.reader.actuators['sound'].action(BaseActuator.READ_ACTION))

        adjustment = self.reader.builder.get_object('success_volume_adjustment')
        self.reader.settings.bind('volume-success', adjustment, 'value', Gio.SettingsBindFlags.DEFAULT)

        button = self.reader.builder.get_object('success_sound_test_button')
        button.connect('clicked',
                       lambda *args: self.reader.actuators['sound'].action(BaseActuator.SUCCESS_ACTION))

        adjustment = self.reader.builder.get_object('error_volume_adjustment')
        self.reader.settings.bind('volume-fail', adjustment, 'value', Gio.SettingsBindFlags.DEFAULT)

        button = self.reader.builder.get_object('error_sound_test_button')
        button.connect('clicked',
                       lambda *args: self.reader.actuators['sound'].action(BaseActuator.ERROR_ACTION))

        adjustment = self.reader.builder.get_object('delay_adjustment')
        self.reader.settings.bind('delay', adjustment, 'value', Gio.SettingsBindFlags.DEFAULT)

        button_left = self.reader.builder.get_object('sound_left_channel')
        button_stereo = self.reader.builder.get_object('sound_stereo_channel')
        button_right = self.reader.builder.get_object('sound_right_channel')

        button_left.set_detailed_action_name("setup.sound-card-channel::{}".format(SoundActuator.CHANNEL_LEFT))
        button_right.set_detailed_action_name("setup.sound-card-channel::{}".format(SoundActuator.CHANNEL_RIGHT))
        button_stereo.set_detailed_action_name("setup.sound-card-channel::{}".format(SoundActuator.CHANNEL_CENTER))

        def do_device_deleted(combo):
            def inner_func(model, path):
                try:
                    if model[path][0] == combo.prop.active_id:
                        combo.set_active_id('-1')
                except IndexError:
                    combo.set_active_id('-1')

            return inner_func

        combo = self.reader.builder.get_object('keyboard_combo')
        combo.set_model(keyboard_store)
        combo.get_model().connect('row-deleted', do_device_deleted(combo))

        render = Gtk.CellRendererText()
        render.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        combo.pack_start(render, True)
        combo.add_attribute(render, "text", KeyboardTreeStore.COLUMN_LABEL)
        self.reader.settings.bind('keyboard', combo, 'active_id', Gio.SettingsBindFlags.DEFAULT)

        combo = self.reader.builder.get_object('sound_combo')
        combo.set_model(audio_store)
        combo.get_model().connect('row-deleted', do_device_deleted(combo))

        render = Gtk.CellRendererText()
        render.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        combo.pack_start(render, True)
        combo.add_attribute(render, "text", AudioDeviceTreeStore.COLUMN_LABEL)
        self.reader.settings.bind('sound-card', combo, 'active_id', Gio.SettingsBindFlags.DEFAULT)

        combo = self.reader.builder.get_object('cam_combo')
        combo.set_model(camera_store)
        combo.get_model().connect('row-deleted', do_device_deleted(combo))

        render = Gtk.CellRendererText()
        render.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        combo.pack_start(render, True)
        combo.add_attribute(render, "text", CameraTreeStore.COLUMN_LABEL)
        self.reader.settings.bind('camera', combo, 'active_id', Gio.SettingsBindFlags.DEFAULT)

        button = self.reader.builder.get_object('camera_test_button')
        button.connect('clicked', self.camera_test_click_cb)

        # self.reader.controller.connect('leaving-step', self.leaving_step_cb)
        self.reader.controller.connect('change-step', self.change_step_cb)

        self.scan_code_keyboard_event_handler = None

    def change_step_cb(self, controller, step):
        if step == TarrabmeController.STEP_NOP:
            try:
                sensor = self.reader.get_sensor('keyboard')
                sensor.grab_device()
                if not self.scan_code_keyboard_event_handler:
                    self.scan_code_keyboard_event_handler = sensor.connect('scan-code',
                                                                           self.scan_code_keyboard_cb)
            except KeyError:
                pass

    def scan_code_keyboard_cb(self, sensor, code):
        label = self.reader.builder.get_object('keyboard_test_label')
        label.set_label(code)

    def camera_test_click_cb(self, *args, **kwargs):
        dialog = Gtk.Dialog("Test camera", self.get_toplevel(), Gtk.DialogFlags.MODAL,
                            None, use_header_bar=True)
        dialog.set_modal(True)
        dialog.set_default_size(390, 350)
        box = dialog.get_content_area()
        camera_frame_test = CameraTestFrame(self.reader)
        box.pack_start(camera_frame_test, True, True, 0)
        dialog.show_all()
        dialog.run()
        camera_frame_test.sensor.stop()
        dialog.destroy()


class LoginFrame(BaseChildFrame):

    def __init__(self, *args, **kwargs):
        super(LoginFrame, self).__init__(*args, **kwargs)

        self.add(self.reader.builder.get_object('LoginView'))
        self.username_entry = self.reader.builder.get_object('username_entry')
        self.password_entry = self.reader.builder.get_object('password_entry')
        self.avatar_image = self.reader.builder.get_object('avatar_image')
        self.login_spinner = self.reader.builder.get_object('login_spinner')
        self.button = self.reader.builder.get_object('login_post_button')
        self.error_label = self.reader.builder.get_object('error_login_label')
        self.button.connect('clicked', self.login_clicked_cb)
        self.reader.controller.connect('change-step', self.change_step_cb)
        self.reader.controller.connect('login-error', self.login_error_cb)

    def login_clicked_cb(self, *args, **kwargs):
        self.button.set_sensitive(False)
        self.reader.controller.set_credentials(self.username_entry.get_text(),
                                               self.password_entry.get_text())
        self.password_entry.set_text('')
        self.error_label.set_visible(False)

    def change_step_cb(self, controller, step):
        if step == TarrabmeController.STEP_CHECK_LOGIN:
            self.button.set_sensitive(False)
            self.avatar_image.set_visible(False)
            self.login_spinner.set_visible(True)
            self.login_spinner.start()
            self.username_entry.set_sensitive(False)
            self.password_entry.set_sensitive(False)
        elif step == TarrabmeController.STEP_LOGIN:
            self.button.set_sensitive(True)
            self.avatar_image.set_visible(True)
            self.login_spinner.set_visible(False)
            self.login_spinner.start()
            self.username_entry.set_sensitive(True)
            self.password_entry.set_sensitive(True)

    def login_error_cb(self, controller, data):
        self.error_label.set_visible(True)
        self.error_label.set_label('Login error')


class WaitingFrame(BaseChildFrame):

    def __init__(self, *args, **kwargs):
        super(WaitingFrame, self).__init__(*args, **kwargs)

        self.add(self.reader.builder.get_object('WaitingView'))
        self.label = self.reader.builder.get_object('waitng_code_label')
        self.button = self.reader.builder.get_object('scan_cancel_button')

        self.reader.controller.connect('change-step', self.change_step_cb)
        self.button.connect('clicked', self.button_clicked_cb)

    def change_step_cb(self, controller, step):
        if step == TarrabmeController.STEP_REQUEST:
            self.label.set_label(controller.code)

    def button_clicked_cb(self, *args):
        self.reader.controller.cancel_operations()


class ResultFrame(BaseChildFrame):

    def __init__(self, *args, **kwargs):
        super(ResultFrame, self).__init__(*args, **kwargs)

        self.view = self.reader.builder.get_object('ResultView')
        self.add(self.view)

        self.title_result = self.reader.builder.get_object('title_result')
        self.image_result = self.reader.builder.get_object('image_result')
        self.code_label = self.reader.builder.get_object('code_label')
        self.event_label = self.reader.builder.get_object('event_label')
        self.ticket_pack_label = self.reader.builder.get_object('ticket_pack_label')
        self.ticket_number_label = self.reader.builder.get_object('ticket_number_label')
        self.ticket_id_label = self.reader.builder.get_object('ticket_id_label')
        self.last_update_label = self.reader.builder.get_object('last_update_label')
        self.update_by_label = self.reader.builder.get_object('update_by_label')
        self.external_id_label = self.reader.builder.get_object('external_id_label')
        self.customer_name_label = self.reader.builder.get_object('customer_name_label')
        self.fiscal_number_label = self.reader.builder.get_object('fiscal_number_label')
        self.locator_label = self.reader.builder.get_object('locator_label')

        self.result_data = self.reader.builder.get_object('result_data')

        self.attempts_frame = self.reader.builder.get_object('attempts_frame')
        self.attempts_label = self.reader.builder.get_object('attempts_label')
        self.attempts_spinner = self.reader.builder.get_object('attempts_spinner')
        self.attempts_box = self.reader.builder.get_object('attempts_box')
        self.attempts_list = None
        self.next_uri = None
        self.load_more_attempts_button = self.reader.builder.get_object('load_more_button')
        self.load_more_attempts_button.connect('clicked', self.load_attempts_cb)
        self.reader.controller.connect('result', self.result_cb)

    def result_cb(self, controller, code, status, data):
        status_map = {TarrabmeController.RESULT_SUCCESS: 'SUCCESS!',
                      TarrabmeController.RESULT_NOT_FOUND_ERROR: 'CODE NOT FOUND',
                      TarrabmeController.RESULT_ALREADY_USED_ERROR: 'ALREADY USED CODE',
                      TarrabmeController.RESULT_DISABLED_ERROR: 'DISABLED CODE',
                      TarrabmeController.RESULT_UNKNOWN_ERROR: 'UNKNOWN ERROR'}

        self.title_result.set_label(status_map[status])
        self.code_label.set_label(code)
        if status == TarrabmeController.RESULT_SUCCESS:
            self.view.get_style_context().remove_class('fail')
            self.view.get_style_context().add_class('success')
            self.image_result.set_from_icon_name('emblem-default', Gtk.IconSize.DIALOG)
        else:
            self.view.get_style_context().remove_class('success')
            self.view.get_style_context().add_class('fail')
            self.image_result.set_from_icon_name('gtk-dialog-error', Gtk.IconSize.DIALOG)

        if status in [TarrabmeController.RESULT_SUCCESS,
                      TarrabmeController.RESULT_DISABLED_ERROR,
                      TarrabmeController.RESULT_ALREADY_USED_ERROR]:
            self.apply_data(data.data)
            self.result_data.set_visible(True)

            if self.attempts_list:
                self.attempts_box.remove(self.attempts_list)
                self.attempts_list = None

            if status == TarrabmeController.RESULT_ALREADY_USED_ERROR:
                self.attempts_frame.set_visible(True)
                self.attempts_spinner.set_visible(True)
                self.get_attempt_list(data.data)
            else:
                self.attempts_frame.set_visible(False)
        else:
            self.result_data.set_visible(False)
            self.attempts_frame.set_visible(False)

    def apply_data(self, data):
        ticket_code = data.get('ticket_code', {})
        value = ticket_code.get('ticket_pack', {}).get('code', '')
        self.set_value_label(value, self.code_label)

        value = ticket_code.get('ticket_pack', {}).get('event', {}).get('name', '')
        self.set_value_label(value, self.event_label)

        value = ticket_code.get('ticket_pack', {}).get('name', '')
        self.set_value_label(value, self.ticket_pack_label)

        value = ticket_code.get('ticket_number', '')
        self.set_value_label(value, self.ticket_number_label)

        value = ticket_code.get('id', '')
        self.set_value_label(value, self.ticket_id_label)

        value = ticket_code.get('modified_date', '')
        self.set_datetime_label(value, self.last_update_label)

        value = ticket_code.get('modified_by', {}).get('username', '')
        self.set_value_label(value, self.update_by_label)

        value = ticket_code.get('external_id', '')
        self.set_value_label(value, self.external_id_label)

        value = ticket_code.get('external_customer_name', '')
        self.set_value_label(value, self.customer_name_label)

        value = ticket_code.get('external_fiscal_number', '')
        self.set_value_label(value, self.fiscal_number_label)

        value = ticket_code.get('external_locator', '')
        self.set_value_label(value, self.locator_label)

    def set_value_label(self, value, label):
        if value is not None:
            value = str(value).strip()
        if value:
            label.set_label(value)
            label.get_parent().set_visible(True)
        else:
            label.get_parent().set_visible(False)

    def set_datetime_label(self, value, label):
        self.set_value_label(get_datetime_label(value), label)

    def get_attempt_list(self, data):
        code = data.get('ticket_code', {}).get('code', '')
        path = self.reader.app.settings.get_string("attempt-list-path").format(code=code)
        uri = self.reader.controller.get_uri_from_path(path)
        msg = Soup.Message.new('GET', uri)
        self.reader.controller.send_message(msg, self.attempt_list_cb)

    def load_attempts_cb(self, *args):
        if not self.next_uri:
            return

        msg = Soup.Message.new('GET', self.next_uri)
        self.reader.controller.send_message(msg, self.attempt_list_cb)
        self.attempts_spinner.set_visible(True)

    def attempt_list_cb(self, session, message, data):
        self.attempts_spinner.set_visible(False)
        if message.props.status_code != 200:
            return

        message.props.response_body.flatten()
        data = json.loads(message.props.response_body.data)

        self.apply_attempt_list(data)

    def apply_attempt_list(self, data):
        self.attempts_label.set_label("Attempts ({0})".format(data.get('count', 0)))
        self.next_uri = data.get('next', None)
        if self.attempts_list is None:
            self.attempts_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.attempts_box.pack_start(self.attempts_list, True, True, 0)

        for attempt in data.get('results', []):
            self.attempts_list.pack_start(self.create_attempt_box(attempt), True, True, 0)

        self.attempts_box.show_all()

    def create_attempt_box(self, data):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.get_style_context().add_class('attempt-item')
        if data.get('success', False):
            box.get_style_context().add_class('success')
        label = Gtk.Label(label=data.get('user', {}).get('first_name'))
        box.pack_start(label, False, False, 10)
        label = Gtk.Label(label=get_datetime_label(data.get('date')))
        box.pack_start(label, True, True, 10)
        return box


class ScanReadyFrame(BaseChildFrame):

    def __init__(self, *args, **kwargs):
        super(ScanReadyFrame, self).__init__(*args, **kwargs)

        self.sensor = None

        self.add(self.reader.builder.get_object('ScanReadyView'))
        self.slave_widget = self.reader  # .builder.get_object('entry1')
        self.slave_widget.connect_after('realize', self.reader_realize_cb)
        self.reader.controller.connect('change-step', self.change_step_cb)

    def reader_realize_cb(self, *args):
        self.sensor = KeyboardSensor(self.reader.settings, self.get_toplevel())
        self.reader.add_sensor('keyboard', self.sensor)

    def change_step_cb(self, controller, step):
        if step == TarrabmeController.STEP_SCAN:
            self.sensor.grab_device()


class CameraTestFrame(BaseChildFrame, VideoFrameMixin):

    def __init__(self, *args, **kwargs):
        BaseChildFrame.__init__(self, *args, **kwargs)
        VideoFrameMixin.__init__(self)


class CameraFrame(CameraTestFrame):

    def __init__(self, *args, **kwargs):
        CameraTestFrame.__init__(self, *args, **kwargs)
        self.sensor = None
        self.reader.controller.connect('leaving-step', self.leaving_step_cb)

    def realize_cb(self, *args):
        super(CameraFrame, self).realize_cb(*args)
        self.reader.add_sensor('camera', self.sensor)
        self.sensor.connect('scan-code', self.scan_code_cb)
        self.sensor.connect('error', self.error_cb)
        self.sensor.connect('start-scan', self.start_scan_cb)

    def leaving_step_cb(self, controller, step, next_step):
        if step == TarrabmeController.STEP_SCAN and self.sensor:
            self.sensor.stop()

    def start_sensor(self):
        if self.sensor:
            self.sensor.restart()
