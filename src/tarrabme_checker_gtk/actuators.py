import json
import re
from gi.repository import Gst, GObject, Gio, Soup

__author__ = 'alfred'


class BaseActuator(GObject.GObject):
    READ_ACTION = 'read'
    SUCCESS_ACTION = 'success'
    ERROR_ACTION = 'error'

    def __init__(self, settings):
        GObject.GObject.__init__(self)
        self.settings = settings

    def action(self, action_type):
        pass


class SoundActuator(BaseActuator):
    SOUND_CARD_SETTING_NAME = 'sound-card'
    SOUND_CHANNEL_SETTING_NAME = 'sound-card-channel'

    READ_SOUND_RESOURCE = "resource:///org/me/tarrab/Checker/read_sound.wav"
    SUCCESS_SOUND_RESOURCE = "resource:///org/me/tarrab/Checker/success_sound.wav"
    ERROR_SOUND_RESOURCE = "resource:///org/me/tarrab/Checker/fail_sound.wav"

    CHANNEL_LEFT = 'left'
    CHANNEL_CENTER = 'center'
    CHANNEL_RIGHT = 'right'

    def __init__(self, settings):
        BaseActuator.__init__(self, settings)

        self.pipe = Gst.Pipeline()

        self._src = Gst.ElementFactory.make("giosrc", "src")
        self.pipe.add(self._src)
        self._src.set_property("location", self.READ_SOUND_RESOURCE)

        self._decode = Gst.ElementFactory.make("decodebin", "decode")
        self.pipe.add(self._decode)
        self._src.link(self._decode)
        self._decode.connect("pad-added", self._pad_added_cb)

        self._convert = Gst.ElementFactory.make("audioconvert", "convert")
        self.pipe.add(self._convert)

        self._volume = Gst.ElementFactory.make("volume", "volume")
        self.settings.bind('volume-general', self._volume, 'volume', Gio.SettingsBindFlags.GET)
        self.pipe.add(self._volume)
        self._convert.link(self._volume)

        self._volume_ampl = Gst.ElementFactory.make("volume", "volume_ampl")
        self.settings.bind('volume-read', self._volume_ampl, 'volume', Gio.SettingsBindFlags.GET)
        self.pipe.add(self._volume_ampl)
        self._volume.link(self._volume_ampl)

        self._balance = Gst.ElementFactory.make("audiopanorama", "balance")
        self.pipe.add(self._balance)
        self._volume_ampl.link(self._balance)

        self._sink = Gst.ElementFactory.make("pulsesink", "sink")
        self.pipe.add(self._sink)
        self._balance.link(self._sink)

        self._bus = self.pipe.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect('message::eos', self._eos_cb)

        self.settings.connect('changed::' + self.SOUND_CARD_SETTING_NAME,
                              self._change_device_cb)

        self.settings.connect('changed::' + self.SOUND_CHANNEL_SETTING_NAME,
                              self._change_channel_cb)

        self._change_device_cb()
        self._change_channel_cb()

    def _pad_added_cb(self, decodebin, pad):
        pad.link(self._convert.get_static_pad("sink"))

    def _eos_cb(self, bus, msg):
        self.pipe.set_state(Gst.State.NULL)

    def __del__(self):
        self.pipe.set_state(Gst.State.NULL)

    def _emit_sound(self, sound_file, setting_name):
        self.pipe.set_state(Gst.State.NULL)
        self.pipe.get_state(Gst.CLOCK_TIME_NONE)
        self._src.set_property("location", sound_file)
        self.settings.bind(setting_name, self._volume_ampl, 'volume', Gio.SettingsBindFlags.GET)
        self.pipe.set_state(Gst.State.PLAYING)

    def action(self, action):
        if action == self.READ_ACTION:
            self._emit_sound(self.READ_SOUND_RESOURCE, 'volume-read')
        elif action == self.SUCCESS_ACTION:
            self._emit_sound(self.SUCCESS_SOUND_RESOURCE, 'volume-success')
        elif action == self.ERROR_ACTION:
            self._emit_sound(self.ERROR_SOUND_RESOURCE, 'volume-fail')

    def _change_device_cb(self, *args):
        re_search = re.search('.*sink(\d+)$',
                              self.settings.get_value(self.SOUND_CARD_SETTING_NAME).get_string())
        if not re_search:
            self._sink.props.device = 'unknown'
            return

        self._sink.props.device = re_search.group(1)

    def _change_channel_cb(self, *args):
        channel = self.settings.get_value(self.SOUND_CHANNEL_SETTING_NAME).get_string()
        if channel == self.CHANNEL_LEFT:
            self._balance.set_property("panorama", -1)
        elif channel == self.CHANNEL_CENTER:
            self._balance.set_property("panorama", 0)
        elif channel == self.CHANNEL_RIGHT:
            self._balance.set_property("panorama", 1)


class NeoPixelsActuator(BaseActuator):

    SECTOR_SETTING_NAME = 'sector'
    ENDPOINT_SETTING_NAME = 'neopixels-endpoint'

    READ_STATUS = 'read'
    SUCCESS_STATUS = 'success'
    ERROR_STATUS = 'error'
    NOOP_STATUS = 'noop'

    def __init__(self, settings, app_settings):
        BaseActuator.__init__(self, settings)
        self.session = Soup.Session()
        self.app_settings = app_settings

    def map_action_to_status(self, action_type):
        return action_type

    def action(self, action_type):
        self.send_status(self.map_action_to_status(action_type))

    def send_status(self, status):
        sector = self.settings.get_string(self.SECTOR_SETTING_NAME)
        if not sector:
            return

        data = {'sector': sector,
                'status': status}

        endpoint = self.app_settings.get_string(self.ENDPOINT_SETTING_NAME)

        message = Soup.Message.new('POST', endpoint)
        message.set_request("application/json",
                            Soup.MemoryUse.COPY,
                            json.dumps(data).encode('UTF-8'))

        self.session.queue_message(message)
