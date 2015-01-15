import os
import sys
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib
from config import *
from widgets.combos import KeyboardCombo, AudioCombo
from audio.pipes import make_notification_emitter
from audio.notification import Notification
from utils import device


class SetupDialog(Gtk.ApplicationWindow):

    def __init__(self, app, parent, settings):
        Gtk.ApplicationWindow.__init__(self, app)

        self.settings = settings
        self.set_default_size(390, 350)
        self.set_title('Setup')
        scrolled_window = Gtk.ScrolledWindow()

        listBox = Gtk.ListBox()
        listBox.set_selection_mode(Gtk.SelectionMode.NONE)

        scrolled_window.add(listBox)

        keyboardRow = Gtk.ListBoxRow()
        keyboardBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        keyboardLabel = Gtk.Label("Scanner")
        keyboardBox.pack_start(keyboardLabel, False, False, 15)

        self.keyboard = KeyboardCombo()
        self.keyboard.set_can_focus(False)
        self.keyboard.connect("changed", self.on_keyboard_change)
        self.keyboard.set_property("width-request", 15)

        self.settings.bind('keyboard', self.keyboard, 'active_id', Gio.SettingsBindFlags.DEFAULT)

        keyboardDataBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        keyboardBox.pack_start(keyboardDataBox, True, True, 15)

        self._scanner_id = None
        self._cache_keypress = ''
        self.keyboard_test = Gtk.Label("Keyboard test")

        keyboardDataBox.pack_start(self.keyboard, True, True, 0)
        keyboardDataBox.pack_start(self.keyboard_test, True, True, 20)

        self.connect("key-press-event", self.on_keypress_event)

        listBox.add(keyboardRow)

        soundRow = Gtk.ListBoxRow()
        soundBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        soundLabel = Gtk.Label("Sound")
        soundBox.pack_start(soundLabel, False, False, 15)

        soundDataBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        soundBox.pack_start(soundDataBox, True, True, 15)

        self.sound_device = AudioCombo()
        self.sound_device.set_can_focus(False)
        #self.keyboard.connect("changed", self.on_keyboard_change)
        self.sound_device.set_property("width-request", 15)
        soundDataBox.pack_start(self.sound_device, True, True, 0)

        self.settings.bind('sound-card', self.sound_device, 'active_id', Gio.SettingsBindFlags.DEFAULT)

        soundButtonsBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        soundDataBox.pack_start(soundButtonsBox, True, True, 15)

        self.soundLeftAction = Gtk.RadioAction("left", "Channel Left",
                                               "Choose sound on channel left", None, value=0)

        import ipdb
        ipdb.set_trace()
        channel_action = self.settings.create_action('sound-card-channel')

        button = Gtk.RadioToolButton()
        icon = Gtk.Image.new_from_resource('/org/me/tarrab/Checker/sound-left.svg')
        button.set_icon_widget(icon)
        soundButtonsBox.pack_start(button, True, True, 0)
        button.set_action_name(channel_action.get_name())
        button.set_action_target_value(GLib.Variant.new_string('left'))

        button = Gtk.RadioToolButton()
        icon = Gtk.Image.new_from_resource('/org/me/tarrab/Checker/sound-stereo.svg')
        button.set_icon_widget(icon)
        soundButtonsBox.pack_start(button, True, True, 0)
        button.set_action_name(channel_action.get_name())
        button.set_action_target_value(GLib.Variant.new_string('center'))

        button = Gtk.RadioToolButton()
        icon = Gtk.Image.new_from_resource('/org/me/tarrab/Checker/sound-right.svg')
        button.set_icon_widget(icon)
        soundButtonsBox.pack_start(button, True, True, 0)
        button.set_action_name(channel_action.get_name())
        button.set_action_target_value(GLib.Variant.new_string('right'))

        # volumnhsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        #
        # soundVolumeGeneralBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # soundVolumeGeneralLabel = Gtk.Label("General")
        # soundVolumeGeneralBox.pack_start(soundVolumeGeneralLabel, False, False, 15)
        #
        # volumnhsize_group.add_widget(soundVolumeGeneralLabel)
        #
        # soundDataBox.pack_start(soundVolumeGeneralBox, True, True, 0)
        #
        # self.soundVolumeGeneral = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        # self.soundVolumeGeneral.set_digits(1)
        # self.soundVolumeGeneral.set_draw_value(False)
        # self.soundVolumeGeneral.set_range(0, 10.0)
        # self.soundVolumeGeneral.set_increments(0.1, 0.1)
        # self.soundVolumeGeneral.set_value(1.0)
        # self.soundVolumeGeneral.add_mark(1.0, Gtk.PositionType.BOTTOM, None)
        #
        # soundVolumeGeneralBox.pack_start(self.soundVolumeGeneral, True, True, 15)
        #
        # #####
        #
        # soundVolumeReadBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # soundVolumeReadLabel = Gtk.Label("Read")
        # soundVolumeReadBox.pack_start(soundVolumeReadLabel, False, False, 15)
        #
        # soundDataBox.pack_start(soundVolumeReadBox, True, True, 0)
        #
        # self.soundVolumeRead = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        # self.soundVolumeRead.set_digits(1)
        # self.soundVolumeRead.set_draw_value(False)
        # self.soundVolumeRead.set_range(0, 10.0)
        # self.soundVolumeRead.set_increments(0.1, 0.1)
        # self.soundVolumeRead.set_value(1.0)
        # self.soundVolumeRead.add_mark(1.0, Gtk.PositionType.BOTTOM, None)
        #
        # volumnhsize_group.add_widget(soundVolumeReadLabel)
        #
        # soundVolumeReadBox.pack_start(self.soundVolumeRead, True, True, 15)
        #
        # soundVolumeReadTest = Gtk.Button("Test")
        # soundVolumeReadTest.connect("clicked", self.on_click_read_test)
        # soundVolumeReadBox.pack_start(soundVolumeReadTest, False, False, 15)
        #
        # #####
        #
        # soundVolumeSuccessBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # soundVolumeSuccessLabel = Gtk.Label("Success")
        # soundVolumeSuccessBox.pack_start(soundVolumeSuccessLabel, False, False, 15)
        #
        # soundDataBox.pack_start(soundVolumeSuccessBox, True, True, 0)
        #
        # self.soundVolumeSuccess = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        # self.soundVolumeSuccess.set_digits(1)
        # self.soundVolumeSuccess.set_draw_value(False)
        # self.soundVolumeSuccess.set_range(0, 10.0)
        # self.soundVolumeSuccess.set_increments(0.1, 0.1)
        # self.soundVolumeSuccess.set_value(1.0)
        # self.soundVolumeSuccess.add_mark(1.0, Gtk.PositionType.BOTTOM, None)
        #
        # volumnhsize_group.add_widget(soundVolumeSuccessLabel)
        #
        # soundVolumeSuccessBox.pack_start(self.soundVolumeSuccess, True, True, 15)
        #
        # soundVolumeSuccessTest = Gtk.Button("Test")
        # soundVolumeSuccessTest.connect("clicked", self.on_click_success_test)
        # soundVolumeSuccessBox.pack_start(soundVolumeSuccessTest, False, False, 15)
        #
        # #####
        #
        # soundVolumeFailBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # soundVolumeFailLabel = Gtk.Label("Error")
        # soundVolumeFailBox.pack_start(soundVolumeFailLabel, False, False, 15)
        #
        # soundDataBox.pack_start(soundVolumeFailBox, True, True, 0)
        #
        # self.soundVolumeFail = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        # self.soundVolumeFail.set_digits(1)
        # self.soundVolumeFail.set_draw_value(False)
        # self.soundVolumeFail.set_range(0, 10.0)
        # self.soundVolumeFail.set_increments(0.1, 0.1)
        # self.soundVolumeFail.set_value(1.0)
        # self.soundVolumeFail.add_mark(1.0, Gtk.PositionType.BOTTOM, None)
        #
        # volumnhsize_group.add_widget(soundVolumeFailLabel)
        #
        # soundVolumeFailBox.pack_start(self.soundVolumeFail, True, True, 15)
        #
        # soundVolumeFailTest = Gtk.Button("Test")
        # soundVolumeFailTest.connect("clicked", self.on_click_fail_test)
        # soundVolumeFailBox.pack_start(soundVolumeFailTest, False, False, 15)

        hsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        hsize_group.add_widget(keyboardLabel)
        hsize_group.add_widget(soundLabel)

        soundRow.add(soundBox)
        listBox.add(soundRow)

        self.add(scrolled_window)
        self.set_modal(True)
        self.show_all()

    def _set_scanner(self, scanner_id=None):
        if (self._scanner_id is not None):
            dev = device.get_device_by_id(self._scanner_id)
            if dev is not None:
                dev.ungrab(Gdk.CURRENT_TIME)

        dev = device.get_device_by_id(scanner_id)

        if (scanner_id is None) or (dev is None):
            self._scanner_id = None
            self.keyboard.set_active(0)
            return

        self._scanner_id = scanner_id
        self.keyboard_test.get_window().set_support_multidevice(True)
        self.keyboard_test.get_window().set_device_events(dev, Gdk.EventMask.ALL_EVENTS_MASK)
        dev.grab(self.keyboard_test.get_window(), Gdk.GrabOwnership.NONE,
                 True, Gdk.EventMask.ALL_EVENTS_MASK, None, Gdk.CURRENT_TIME)
        dev.set_mode(Gdk.InputMode.SCREEN)

    def on_keypress_event(self, widget, event):
        device_id = str(event.get_source_device().props.device_id)
        if self._scanner_id == device_id:
            if len(event.string) > 0:
                for i in range(len(event.string)):
                    if ord(event.string[i]) != 13:
                        self._cache_keypress += event.string
                    elif len(self._cache_keypress):
                        self.keyboard_test.set_label(self._cache_keypress)
                        self._cache_keypress = ''
        return True

    def destroy(self):
        self.keyboard.disconnect_event_handlers()
        self._set_scanner(None)
        Gtk.Dialog.destroy(self)

    def on_keyboard_change(self, combo):
        self._set_scanner(combo.get_active_id())

    def on_click_read_test(self, button):
        self._test_sound('read')

    def on_click_success_test(self, button):
        self._test_sound('success')

    def on_click_fail_test(self, button):
        self._test_sound('fail')

    def _test_sound(self, notification):
        self._emitter = make_notification_emitter(
            name="Test " + self.get_title(),
            device_id=self.get_sound_device(),
            balance=self.get_sound_channel(),
            volume_general=self.soundVolumeGeneral.get_value(),
            volume_read=self.soundVolumeRead.get_value(),
            volume_success=self.soundVolumeSuccess.get_value(),
            volume_fail=self.soundVolumeFail.get_value())

        self._emitter.play_notification(notification)

    def set_scanner_device(self, device_id):
        if device_id is None:
            self.keyboard.set_active(0)
        else:
            self.keyboard.set_active_id(device_id)

    def get_scanner_device(self):
        return self.keyboard.get_active_id()

    def set_sound_device(self, device_id):
        if device_id is None:
            self.sound_device.set_active(0)
        else:
            self.sound_device.set_active_id(device_id)

    def get_sound_device(self):
        return self.sound_device.get_active_id()

    def set_sound_channel(self, channel):
        if channel == Notification.LEFT:
            self.soundLeftAction.set_current_value(0)
        elif channel == Notification.CENTER:
            self.soundLeftAction.set_current_value(1)
        else:
            self.soundLeftAction.set_current_value(2)

    def get_sound_channel(self):
        if self.soundLeftAction.get_current_value() == 0:
            return Notification.LEFT
        elif self.soundLeftAction.get_current_value() == 1:
            return Notification.CENTER
        else:
            return Notification.RIGHT

    def get_volume_general(self):
        return self.soundVolumeGeneral.get_value()

    def set_volume_general(self, value):
        return self.soundVolumeGeneral.set_value(value)

    def get_volume_read(self):
        return self.soundVolumeRead.get_value()

    def set_volume_read(self, value):
        return self.soundVolumeRead.set_value(value)

    def get_volume_success(self):
        return self.soundVolumeSuccess.get_value()

    def set_volume_success(self, value):
        return self.soundVolumeSuccess.set_value(value)

    def get_volume_fail(self):
        return self.soundVolumeFail.get_value()

    def set_volume_fail(self, value):
        return self.soundVolumeFail.set_value(value)
