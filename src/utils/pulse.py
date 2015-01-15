from gi.repository import Gio, GLib, GObject
from time import sleep
import re
import dbus


class PulseAudio:

    def __init__(self):
        destination = 'org.PulseAudio1'
        path = '/org/pulseaudio/server_lookup1'
        interface = 'org.PulseAudio.ServerLookup1'
        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self.proxy = Gio.DBusProxy.new_sync(self.bus, Gio.DBusProxyFlags.NONE, None,
                                                destination, path, interface, None)

            address = self.proxy.get_cached_property('Address').get_string()
            self.connection = dbus.connection.Connection(address)
            self.core = self.connection.get_object(object_path="/org/pulseaudio/core1")

        except:
            print("Exception: %s" % sys.exec_info()[1])

    def get_sinks(self):
        result = []
        paths = self.core.Get("org.PulseAudio.Core1", "Sinks", dbus_interface="org.freedesktop.DBus.Properties")

        for sinkPath in paths:
            result.append(self.get_sink(sinkPath))

        return result

    def get_sink(self, path):
        return PulseSink(self.connection.get_object(object_path=path), path)


class PulseSink(GObject.GObject):

    def __init__(self, proxy, path):
        GObject.GObject.__init__(self)

        self.proxy = proxy
        self.path = path

    def get_properties(self):
        return self.proxy.Get('org.PulseAudio.Core1.Device', "PropertyList",
                              dbus_interface="org.freedesktop.DBus.Properties", byte_arrays=True)

    def get_name(self):
        properties = self.get_properties()
        try:
            return properties['device.description'].decode()[:-1]
        except (KeyError):
            return "unknown"

    def get_icon(self):
        properties = self.get_properties()
        try:
            return properties['device.icon_name'].decode()[:-1]
        except (KeyError):
            return "audio-speakers-symbolic"

    def get_id(self):
        result = re.match("\/org\/pulseaudio\/core1\/sink(\d+)", self.path)
        return result.group(1)
