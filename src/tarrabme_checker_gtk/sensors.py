from .treestores import keyboard_store, KeyboardTreeStore, camera_store, CameraTreeStore, NoDeviceError
from gi.repository import Gst, GLib, GObject, Gdk

__author__ = 'alfred'


class BaseSensor(GObject.GObject):
    __gsignals__ = {
        'scan-code': (GObject.SIGNAL_RUN_FIRST, None,
                      (str,)),
        'error': (GObject.SIGNAL_RUN_FIRST, None,
                  (str,)),
        'start-scan': (GObject.SIGNAL_RUN_FIRST, None,
                       tuple())
    }

    def __init__(self, settings):
        GObject.GObject.__init__(self)
        self.setting = settings
        self._active = True

    def do_scan_code(self, code):
        code = code.strip()
        if not len(code):
            self.stop_emission('scan-code')
            return True
        print("Code scanned: {}".format(code))

    def do_error(self, error):
        print("Error on sensor: {}".format(error))

    def active(self, value=True):
        self._active = value


class KeyboardSensor(BaseSensor):
    SETTING_NAME = 'keyboard'

    def __init__(self, settings, widget):
        BaseSensor.__init__(self, settings)
        self.widget = widget
        self.device_id = None
        self.next_char = ''
        self.buffer = ''
        self.grabbed = False
        self.setting.connect('changed::' + self.SETTING_NAME,
                             self.change_device_cb)

        self.widget.connect("key-press-event", self.keypress_event_cb)
        self.widget.connect("key-release-event", self.keyrelease_event_cb)
        self.change_device_cb()

    def change_device_cb(self, *args):
        if self.device_id is not None:
            try:
                dev = keyboard_store.get_item_by_id(self.device_id)[KeyboardTreeStore.COLUMN_DEVICE]
                if dev is not None:
                    print("Ungrab dev: {}".format(self.device_id))
                    dev.ungrab(Gdk.CURRENT_TIME)
                    self.grabbed = False
            except NoDeviceError:
                pass

        try:
            dev_item = keyboard_store.get_item_by_id(self.setting.get_value(self.SETTING_NAME).get_string())
            self.device_id = dev_item[KeyboardTreeStore.COLUMN_DEVICE_ID]
        except NoDeviceError:
            self.device_id = None

        self.grab_device()

    def grab_device(self):
        if self.device_id is None:
            return

        try:
            dev = keyboard_store.get_item_by_id(self.device_id)[KeyboardTreeStore.COLUMN_DEVICE]
        except NoDeviceError:
            return

        if not dev or not self.widget.get_window() or self.grabbed:
            return

        self.widget.get_window().set_support_multidevice(True)
        self.widget.get_window().set_device_events(dev,
                                                   Gdk.EventMask.ALL_EVENTS_MASK)

        result = dev.grab(self.widget.get_window(),
                          Gdk.GrabOwnership.NONE,
                          False,
                          Gdk.EventMask.ALL_EVENTS_MASK,
                          None,
                          Gdk.CURRENT_TIME)
        if result == Gdk.GrabStatus.SUCCESS:
            self.grabbed = True
            dev.set_mode(Gdk.InputMode.WINDOW)
            print("Grab dev: {}".format(self.device_id))
        else:
            print(result)

        self.reset_buffer()

    def check_event(self, event):
        if not self.device_id:
            return False

        device_id = str(event.get_source_device().props.device_id)
        if device_id != self.device_id:
            return False

        return True

    def keypress_event_cb(self, widget, event):
        if not self.check_event(event):
            return
        if not self._active or len(event.string) < 1:
            self.widget.stop_emission('key-press-event')
            return True

        for c in event.string:
            self.add_char(c)

        self.widget.stop_emission('key-press-event')
        return True

    def add_char(self, char):
        if self.next_char != char:
            self.consolidate_char()

        if ord(char) == 13:
            self.emit('scan-code', self.buffer)
            self.reset_buffer()
        else:
            self.next_char = char

    def consolidate_char(self):
        self.buffer += self.next_char
        self.next_char = ''

    def keyrelease_event_cb(self, widget, event):
        if not self.check_event(event):
            return

        self.consolidate_char()
        return True

    def reset_buffer(self):
        self.buffer = ''
        self.emit('start-scan')


class CameraSensor(BaseSensor):
    SETTING_NAME = 'camera'

    def __init__(self, settings, texture):
        BaseSensor.__init__(self, settings)

        self.timeout_handler = None
        self.texture = texture

        self.setting.connect('changed::' + self.SETTING_NAME,
                             self.change_device_cb)

        self.pipe = Gst.Pipeline()
        self._src = Gst.ElementFactory.make("v4l2src")
        self.pipe.add(self._src)

        tee = Gst.ElementFactory.make("tee")
        self.pipe.add(tee)
        self._src.link(tee)

        zbarqueue = Gst.ElementFactory.make('queue')
        self.pipe.add(zbarqueue)
        tee.link(zbarqueue)

        zbarcolorspace = Gst.ElementFactory.make('videoconvert')
        self.pipe.add(zbarcolorspace)
        zbarqueue.link(zbarcolorspace)

        self.zbar = Gst.ElementFactory.make('zbar')
        self.zbar.set_property('message', True)
        self.zbar.set_property('cache', True)
        self.pipe.add(self.zbar)
        zbarcolorspace.link(self.zbar)

        fakesink = Gst.ElementFactory.make('fakesink')
        self.pipe.add(fakesink)
        self.zbar.link(fakesink)

        videoqueue = Gst.ElementFactory.make('queue')
        self.pipe.add(videoqueue)
        tee.link(videoqueue)

        self._sink = Gst.ElementFactory.make("autocluttersink")
        self.pipe.add(self._sink)
        self._sink.set_property("texture", self.texture)
        videoqueue.link(self._sink)

        self._bus = self.pipe.get_bus()
        self._bus.add_signal_watch()
        self._bus.enable_sync_message_emission()
        self._bus.connect('message', self.on_message)

        self.change_device_cb()

    def change_device_cb(self, *args):
        state_change, orig_state, pending_state = self.pipe.get_state(Gst.CLOCK_TIME_NONE)
        orig_device = self._src.get_property('device')
        if self._active and orig_device == '':
            orig_state = Gst.State.PLAYING
        self.pipe.set_state(Gst.State.NULL)
        dev_item = camera_store.get_item_by_id(self.setting.get_value(self.SETTING_NAME).get_string())
        dev = dev_item[CameraTreeStore.COLUMN_DEVICE]
        if not dev:
            self.stop()
            self._src.set_property('device', '')
            self.reset_timeout_handler()
            return
        self._src.set_property('device', dev.get_device_file())
        self.pipe.set_state(orig_state)

    def on_message(self, bus, msg):
        t = msg.type
        if t == Gst.MessageType.EOS:
            self.pipe.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ELEMENT and msg.get_structure().get_name() == 'barcode':
            if not self._active:
                self.restart()
                return
            self.emit('scan-code', msg.get_structure().get_string('symbol'))
        elif t == Gst.MessageType.ERROR:
            self.emit('error', msg.parse_error())

    def restart(self):
        self.pipe.set_state(Gst.State.NULL)
        if self._src.get_property('device'):
            self.pipe.set_state(Gst.State.PLAYING)
            self.emit('start-scan')
        else:
            self.emit('error', 'No device selected')

    def do_scan_code(self, code):
        result = super(CameraSensor, self).do_scan_code(code)
        if result:
            return result
        self.pipe.set_state(Gst.State.NULL)
        self.pipe.set_state(Gst.State.PAUSED)

        self.timeout_handler = GLib.timeout_add_seconds(1, self.timeout_cb)

    def timeout_cb(self):
        self.timeout_handler = None
        self.restart()

    def reset_timeout_handler(self):
        if self.timeout_handler:
            GLib.source_remove(self.timeout_handler)
            self.timeout_handler = None

    def active(self, value=True):
        super(CameraSensor, self).active(value)
        if not value:
            self.reset_timeout_handler()
            self.pipe.set_state(Gst.State.NULL)
        else:
            self.restart()

    def stop(self):
        self.reset_timeout_handler()
        self.pipe.set_state(Gst.State.NULL)
        self.pipe.get_state(Gst.CLOCK_TIME_NONE)

    def __del__(self):
        self.stop()
