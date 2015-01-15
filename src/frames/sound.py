from gi.repository import GObject, Gst, GLib
from pipe import Pipe
import os

MEDIA_PATH = "/home/alfred/Projectes/safeTicketGtkApp/media/"


class SoundEmiter:

    def __init__(self):
        self.pipe = Gst.Pipeline()
        #self.adder = Gst.ElementFactory.make ("adder", "adder")
        # self.pipe.add(self.adder)
        self.convert = Gst.ElementFactory.make("audioconvert", "convert")
        self.pipe.add(self.convert)

        self.balance = Gst.ElementFactory.make("audiopanorama", "balance")
        self.pipe.add(self.balance)
        caps = Gst.caps_from_string("audio/x-raw,channels=2")
        #self.convert.link_filtered(self.balance, caps)
        self.convert.link(self.balance)
        # self.adder.link(self.balance)autoaudiosink
        #sink = Gst.ElementFactory.make ("autoaudiosink", "sink")
        sink = Gst.ElementFactory.make("pulsesink", "sink")
        self.pipe.add(sink)
        self.balance.link(sink)
        sink.set_property("client-name", "Tarrap.me Code Reader")

        self.read_pipe = Pipe("read_pipe", os.path.join(MEDIA_PATH, "read_sound.wav"))
        # self.read_pipe.pipe.set_state(Gst.State.PAUSED)
        self.pipe.add(self.read_pipe.pipe)
        self.read_pipe.volume.set_property("volume", 1.0)
        #newpad = self.adder.get_request_pad("sink%d")
        #newpad = self.balance.get_static_pad("sink")
        # self.read_pipe.ghost.link(newpad)

        self.ok_pipe = Pipe("ok_pipe", os.path.join(MEDIA_PATH, "ok_sound.wav"))
        self.ok_pipe.volume.set_property("volume", 0.2)
        # self.ok_pipe.pipe.set_state(Gst.State.PAUSED)
        # self.pipe.add(self.ok_pipe.pipe)
        #newpad = self.adder.get_request_pad("sink%d")
        # self.ok_pipe.ghost.link(newpad)

        self.fail_pipe = Pipe("fail_pipe", os.path.join(MEDIA_PATH, "fail_sound.wav"))
        # self.fail_pipe.pipe.set_state(Gst.State.PAUSED)
        # self.pipe.add(self.fail_pipe.pipe)
        #newpad = self.adder.get_request_pad("sink%d")
        # self.fail_pipe.ghost.link(newpad)

        # self.pipe.set_state(Gst.State.PLAYING)
    def __del__(self):
        self.pipe.set_state(Gst.State.NULL)

    def sound_read(self):
        print "Play Read"
        self.pipe.set_state(Gst.State.NULL)
        pad = self.convert.get_static_pad("sink")
        if self.pipe.get_by_name("ok_pipe"):
            print "Ok pipe was found. Removing"
            self.pipe.remove(self.ok_pipe.pipe)
        if self.pipe.get_by_name("fail_pipe"):
            print "Fail pipe was found. Removing"
            self.pipe.remove(self.fail_pipe.pipe)
        if not self.pipe.get_by_name("read_pipe"):
            print "Read pipe was not found. Adding..."
            self.pipe.add(self.read_pipe.pipe)
        if pad.is_linked():
            pad.get_peer().unlink(pad)
        self.read_pipe.pipe.link(self.convert)

        self.read_pipe.pipe.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        self.pipe.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        self.pipe.set_state(Gst.State.PLAYING)

        # self.read_pipe.ghost.set_blocked(True)
        # self.pipe.set_state(Gst.State.NULL)
        """self.read_pipe.pipe.seek_simple(Gst.Format.BYTES, Gst.SeekFlags.FLUSH, 0)
        #self.read_pipe.ghost.set_blocked(False)
        self.pipe.set_state(Gst.State.READY)
        self.read_pipe.pipe.set_state(Gst.State.PLAYING)"""

    def sound_ok(self):
        print "Play Ok"
        self.pipe.set_state(Gst.State.NULL)
        pad = self.convert.get_static_pad("sink")
        if pad.is_linked():
            pad.get_peer().unlink(pad)
        if self.pipe.get_by_name("read_pipe"):
            self.pipe.remove(self.read_pipe.pipe)
        if self.pipe.get_by_name("fail_pipe"):
            self.pipe.remove(self.fail_pipe.pipe)
        if not self.pipe.get_by_name("ok_pipe"):
            self.pipe.add(self.ok_pipe.pipe)
        self.ok_pipe.pipe.link(self.convert)

        self.ok_pipe.pipe.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        self.pipe.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        self.pipe.set_state(Gst.State.PLAYING)

    def sound_fail(self):
        print "Play Fail"
        self.pipe.set_state(Gst.State.NULL)
        pad = self.convert.get_static_pad("sink")
        if pad.is_linked():
            pad.get_peer().unlink(pad)
        if self.pipe.get_by_name("read_pipe"):
            self.pipe.remove(self.read_pipe.pipe)
        if self.pipe.get_by_name("ok_pipe"):
            self.pipe.remove(self.ok_pipe.pipe)
        if not self.pipe.get_by_name("fail_pipe"):
            self.pipe.add(self.fail_pipe.pipe)
        self.fail_pipe.pipe.link(self.convert)

        self.fail_pipe.pipe.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        self.pipe.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        self.pipe.set_state(Gst.State.PLAYING)

    def set_balance(self, balance):
        self.balance.set_property("panorama", balance)
