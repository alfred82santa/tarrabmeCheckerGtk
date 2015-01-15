from gi.repository import GObject, Gst, GLib


class Notification():
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"

    def cb_pad_added(self, decodebin, pad):
        pad.link(self._convert.get_static_pad("sink"))

    def __init__(self, filename, name=None, balance=None, device_id=None,
                 volume=1.0, volume_ampl=1.0):
        self._pipe = Gst.Pipeline()

        self._src = Gst.ElementFactory.make("giosrc", "src")
        self._pipe.add(self._src)
        self._src.set_property("location", filename)

        self._decode = Gst.ElementFactory.make("decodebin", "decode")
        self._pipe.add(self._decode)
        self._src.link(self._decode)
        self._decode.connect("pad-added", self.cb_pad_added)

        self._convert = Gst.ElementFactory.make("audioconvert", "convert")
        self._pipe.add(self._convert)

        self._volume = Gst.ElementFactory.make("volume", "volume")
        self._volume.set_property("volume", volume)
        self._pipe.add(self._volume)
        self._convert.link(self._volume)

        self._volume_ampl = Gst.ElementFactory.make("volume", "volume_ampl")
        self._volume_ampl.set_property("volume", volume_ampl)
        self._pipe.add(self._volume_ampl)
        self._volume.link(self._volume_ampl)

        self._balance = Gst.ElementFactory.make("audiopanorama", "balance")
        self._pipe.add(self._balance)
        self._volume_ampl.link(self._balance)

        self._sink = Gst.ElementFactory.make("pulsesink", "sink")
        self._pipe.add(self._sink)
        self._balance.link(self._sink)

        if name:
            self.set_client_name(name)
        if balance:
            self.set_balance(balance)
        if device_id:
            self.set_pulse_device(device_id)

        self._bus = self._pipe.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect('message::eos', self.on_eos)

    def on_eos(self, bus, msg):
        self._pipe.set_state(Gst.State.NULL)

    def set_balance(self, balance):
        if balance == self.LEFT:
            self._balance.set_property("panorama", -1)
        elif balance == self.RIGHT:
            self._balance.set_property("panorama", 1)
        else:
            self._balance.set_property("panorama", 0)

    def set_volume(self, volume):
        self._volume.set_property("volume", volume)

    def set_volume_ampl(self, volume):
        self._volume_ampl.set_property("volume", volume)

    def set_pulse_device(self, pulse_device_id):
        self._sink.set_property("device", pulse_device_id)

    def set_client_name(self, name):
        self._sink.set_property("client-name", name)

    def play(self):
        self._pipe.set_state(Gst.State.NULL)
        self._pipe.set_state(Gst.State.PLAYING)
