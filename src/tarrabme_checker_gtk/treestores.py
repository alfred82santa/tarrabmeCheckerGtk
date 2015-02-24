__author__ = 'alfred'
from gi.repository import Gtk, Gdk, Gio, GLib, GUdev


class NoDeviceError(Exception):
    pass


class BaseTreeStore(Gtk.TreeStore):
    NO_DEVICE_STR = "--NO DEVICE SELECTED--"

    def get_item_by_id(self, identifier, idx=0):
        for dev in self:
            if dev[idx] == identifier:
                return dev

        raise NoDeviceError("No device")


class KeyboardTreeStore(BaseTreeStore):
    COLUMN_DEVICE_ID = 0
    COLUMN_LABEL = 1
    COLUMN_DEVICE = 2
    COLUMN_FLOATING = 3

    def __init__(self):
        Gtk.TreeStore.__init__(self,
                               str,  # COLUMN_DEVICE_ID
                               str,  # COLUMN_LABEL
                               Gdk.Device,  # COLUMN_DEVICE
                               bool)  # COLUMN_FLOATING

        # Add initial option "--NO DEVICE SELECTED--"
        self.append(None, [str(-1),
                           self.NO_DEVICE_STR,
                           None,
                           False])

        self.man = Gdk.Display.get_default().get_device_manager()

        # Add events handlers to manage devices. It allow to add or remove device when it is plugged or unplugged
        self._event_handler_added = self.man.connect("device-added",
                                                     self.on_device_added)
        self._event_handler_removed = self.man.connect("device-removed",
                                                       self.on_device_removed)
        self._event_handler_changed = self.man.connect("device-changed",
                                                       self.on_device_changed)

        # Retrieve slave devices (devices attached to a master device)
        dev_list = self.man.list_devices(Gdk.DeviceType.SLAVE)

        for dev in dev_list:
            if dev.get_source() == Gdk.InputSource.KEYBOARD:
                self.add_device(dev)

        # Retrieve float devices (devices no attached to a master device)
        dev_list = self.man.list_devices(Gdk.DeviceType.FLOATING)
        for dev in dev_list:
            if dev.get_source() == Gdk.InputSource.KEYBOARD:
                self.add_device(dev)

    def add_device(self, device):
        self.append(None,
                    [str(device.props.device_id),
                     "{0} [DeviceId: {1}]".format(device.get_name(), device.props.device_id),
                     device,
                     device.get_device_type() == Gdk.DeviceType.FLOATING])

    def remove_device(self, device):
        dev = self.get_item_by_id(str(device.props.device_id), self.COLUMN_DEVICE_ID)
        if dev:
            self.remove(dev.iter)

    def disconnect_event_handlers(self):
        if self._event_handler_added:
            self.man.disconnect(self._event_handler_added)
            self._event_handler_added = None

        if self._event_handler_removed:
            self.man.disconnect(self._event_handler_removed)
            self._event_handler_removed = None

        if self._event_handler_changed:
            self.man.disconnect(self._event_handler_changed)
            self._event_handler_changed = None

    def destroy(self):
        self.disconnect_event_handlers()

    def on_device_added(self, device_manager, device):
        if device.get_source() == Gdk.InputSource.KEYBOARD and \
            device.get_device_type() in [Gdk.DeviceType.FLOATING,
                                         Gdk.DeviceType.SLAVE]:
            self.add_device(device)

    def on_device_changed(self, device_manager, device):
        dev_item = self[str(device.props.device_id)]
        if dev_item:
            if device.get_source() == Gdk.InputSource.KEYBOARD and \
                device.get_device_type() in [Gdk.DeviceType.FLOATING,
                                             Gdk.DeviceType.SLAVE]:
                dev_item[self.COLUMN_LABEL] = device.get_name()
                dev_item[self.COLUMN_FLOATING] = device.get_device_type() == Gdk.DeviceType.FLOATING
            else:
                self.remove_device(device)
        elif device.get_source() == Gdk.InputSource.KEYBOARD and \
            device.get_device_type() in [Gdk.DeviceType.FLOATING,
                                         Gdk.DeviceType.SLAVE]:
            self.add_device(device)

    def on_device_removed(self, device_manager, device):
        self.remove_device(device)


keyboard_store = KeyboardTreeStore()


class AudioDeviceTreeStore(BaseTreeStore):
    COLUMN_DEVICE_ID = 0
    COLUMN_LABEL = 1
    COLUMN_DEVICE = 2

    DBUS_DESTINATION = 'org.PulseAudio1'
    DBUS_PATH = '/org/pulseaudio/server_lookup1'
    DBUS_INTERFACE = 'org.PulseAudio.ServerLookup1'
    DBUS_CORE_PATH = '/org/pulseaudio/core1'
    DBUS_CORE_INTERFACE = 'org.PulseAudio.Core1'

    def __init__(self):
        Gtk.TreeStore.__init__(self,
                               str,  # COLUMN_DEVICE_ID
                               str,  # COLUMN_LABEL
                               GLib.Variant)  # COLUMN_DEVICE

        # Add initial option "--NO DEVICE SELECTED--"
        self.append(None, [str(-1),
                           self.NO_DEVICE_STR,
                           None])

        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self.proxy = Gio.DBusProxy.new_sync(self.bus,
                                                Gio.DBusProxyFlags.NONE,
                                                None,
                                                self.DBUS_DESTINATION,
                                                self.DBUS_PATH,
                                                self.DBUS_INTERFACE,
                                                None)

            address = self.proxy.get_cached_property('Address').get_string()
            self.connection = Gio.DBusConnection.new_for_address_sync(address,
                                                                      Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT,
                                                                      None,
                                                                      None)

            self.proxy = Gio.DBusProxy.new_sync(self.connection,
                                                Gio.DBusProxyFlags.NONE,
                                                None,
                                                None,
                                                self.DBUS_CORE_PATH,
                                                self.DBUS_CORE_INTERFACE,
                                                None)

            for dev_path in self.proxy.get_cached_property('Sinks'):
                self.append_sink_by_path(dev_path)
        except Exception as ex:
            print(ex)

    def append_sink_by_path(self, path):
        proxy = Gio.DBusProxy.new_sync(self.connection,
                                       Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
                                       None,
                                       None,
                                       path,
                                       'org.freedesktop.DBus.Properties',
                                       None)

        proplist = proxy.call_sync('Get',
                                   GLib.Variant('(ss)', ('org.PulseAudio.Core1.Device', 'PropertyList')),
                                   Gio.DBusCallFlags.NONE,
                                   -1,
                                   None)

        proplist = {k: bytes(v).decode(encoding='UTF-8').strip('\x00') for k, v in proplist[0].items()}
        self.append(None, [path, proplist['device.description'], GLib.Variant('a{ss}', proplist)])

        return proplist


audio_store = AudioDeviceTreeStore()


class UdevTreeStore(BaseTreeStore):
    UDEV_SUBSYSTEM = ''

    COLUMN_DEVICE_ID = 0
    COLUMN_LABEL = 1
    COLUMN_DEVICE = 2

    def __init__(self):
        Gtk.TreeStore.__init__(self,
                               str,  # COLUMN_DEVICE_ID
                               str,  # COLUMN_LABEL
                               GUdev.Device)  # COLUMN_DEVICE

        # Add initial option "--NO DEVICE SELECTED--"
        self.append(None, [str(-1),
                           self.NO_DEVICE_STR,
                           None])

        self.client = GUdev.Client()
        self.client.connect('uevent', self.uevent_cb)
        self.initial_list()

    def uevent_cb(self, client, action, device):
        if action == 'add':
            self.add_device(device)
        elif action == 'remove':
            self.remove_device(device)
        elif action == 'change':
            self.update_device(device)

    def initial_list(self):
        for dev in self.client.query_by_subsystem(self.UDEV_SUBSYSTEM):
            self.add_device(dev)

    def get_iter_by_device(self, device):
        try:
            return self.get_item_by_id(device.get_sysfs_path(), self.COLUMN_DEVICE_ID)
        except NoDeviceError:
            return None

    def check_device(self, device):
        if device.get_subsystem() != self.UDEV_SUBSYSTEM:
            return False
        if not device.get_is_initialized():
            return False

        return True

    def add_device(self, device):
        if not self.check_device(device):
            self.remove_device(device)
            return
        if self.get_iter_by_device(device):
            self.update_device(device)
            return
        self.append(None, [device.get_sysfs_path(),
                           # device.get_property returns a UTF-8 string with escaped chars (It looks like a bug)
                           device.get_property('ID_MODEL_ENC').encode('UTF-8').decode('unicode_escape'),
                           device])

    def remove_device(self, device):
        it = self.get_iter_by_device(device)
        if it:
            self.remove(it)

    def update_device(self, device):
        if not self.check_device(device):
            self.remove_device(device)
            return

        it = self.get_iter_by_device(device)
        if not it:
            self.add_device(device)
            return

        it[self.COLUMN_LABEL] = device.get_property('ID_MODEL_ENC').encode('UTF-8').decode('unicode_escape')


class CameraTreeStore(UdevTreeStore):
    UDEV_SUBSYSTEM = 'video4linux'


camera_store = CameraTreeStore()
