from gi.repository import Gtk, Gdk, GObject, Pango
from utils.pulse import PulseAudio, PulseSink


class CellRendererDevice(Gtk.CellRendererText):
    _device = None

    def get_device(self):
        return self._device

    def set_device(self, device):
        self._device = device
        self.props.sensitive = True
        self.props.ellipsize_set = True
        self.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        if device is not None:
            self.props.text = device.get_name() + " [DeviceID: " + str(device.props.device_id) + "]"
            if device.get_device_type() == Gdk.DeviceType.MASTER:
                self.props.sensitive = False
        else:
            self.props.text = "--NO DEVICE SELECTED--"

    device = GObject.property(type=Gdk.Device,
                              flags=GObject.PARAM_READWRITE,
                              setter=set_device,
                              getter=get_device)


class KeyboardCombo(Gtk.ComboBox):

    COLUMN_DEVICE_ID = 0
    COLUMN_DEVICE = 1
    COLUMN_ICON_ID = 2
    COLUMN_USING_ICON_ID = 3
    COLUMN_ENABLED = 4
    COLUMN_TIMER_HANDLER = 5

    def __init__(self):
        Gtk.ComboBox.__init__(self)

        self._event_handler_added = None
        self._event_handler_removed = None
        self._event_handler_changed = None

        self.set_model(self._create_store_list())

        renderer_device = CellRendererDevice()
        renderer_image = Gtk.CellRendererPixbuf()
        renderer_active = Gtk.CellRendererPixbuf()

        self.pack_start(renderer_image, False)
        self.pack_start(renderer_device, True)
        self.pack_start(renderer_active, False)

        self.add_attribute(renderer_device, "device", self.COLUMN_DEVICE)
        self.add_attribute(renderer_device, "sensitive", self.COLUMN_ENABLED)

        self.add_attribute(renderer_image, "stock-id", self.COLUMN_ICON_ID)
        self.add_attribute(renderer_image, "sensitive", self.COLUMN_ENABLED)

        self.add_attribute(renderer_active, "stock-id", self.COLUMN_USING_ICON_ID)
        self.add_attribute(renderer_active, "sensitive", self.COLUMN_ENABLED)

        GObject.add_emission_hook(Gtk.Menu, "key-press-event", self.on_key_press_event)
        #self.connect("key-press-event", self.on_keypress)
        self.props.id_column = self.COLUMN_DEVICE_ID
        self.set_active(0)

        self.__signal_sockets = []

    def _create_store_list(self):
        tree_store = Gtk.TreeStore(str,  # COLUMN_DEVICE_ID
                                   Gdk.Device,  # COLUMNS_DEVICE
                                   str,  # COLUMN_ICON_ID
                                   str,  # COLUMN_USING_ICON_ID
                                   bool,  # COLUMN_ENABLED
                                   int)  # COLUMN_TIMER_HANDLER

        # Add initial option "--NO DEVICE SELECTED--"
        tree_store.append(None, [str(-1), None, Gtk.STOCK_CAPS_LOCK_WARNING, None, True, -1])

        man = Gdk.Display.get_default().get_device_manager()

        # Add events handlers to manage devices. It allow to add or remove device when it is plugged or unplugged
        self._event_handler_added = man.connect("device-added",
                                                self.on_device_added)
        self._event_handler_removed = man.connect("device-removed",
                                                  self.on_device_removed)
        self._event_handler_changed = man.connect("device-changed",
                                                  self.on_device_changed)

        # Retrieve master devices (device groups)
        dev_list = man.list_devices(Gdk.DeviceType.MASTER)

        for master_dev in dev_list:
            if master_dev.get_source() == Gdk.InputSource.KEYBOARD:
                master_iter = tree_store.append(None,
                                                [str(master_dev.props.device_id), master_dev,
                                                 Gtk.STOCK_CAPS_LOCK_WARNING, None,
                                                 False, -1])
            for slave_dev in master_dev.list_slave_devices():
                tree_store.append(master_iter,
                                  [str(slave_dev.props.device_id), slave_dev,
                                   Gtk.STOCK_CAPS_LOCK_WARNING, None, True, -1])

        return tree_store

    def disconnect_event_handlers(self):
        man = Gdk.Display.get_default().get_device_manager()

        if self._event_handler_added:
            man.disconnect(self._event_handler_added)
            self._event_handler_added = None

        if self._event_handler_removed:
            man.disconnect(self._event_handler_removed)
            self._event_handler_removed = None

        if self._event_handler_changed:
            man.disconnect(self._event_handler_changed)
            self._event_handler_changed = None

    def destroy(self):
        self.disconnect_event_handlers()

    def on_keypress(self, widget, event):
        if event.type in [Gdk.EventType.KEY_PRESS, Gdk.EventType.KEY_RELEASE] and \
                len(event.string) and \
                (ord(event.string) == 13):
            return True
        device_id = event.get_source_device().props.device_id
        for dev in self.get_model():
            if dev[self.COLUMN_DEVICE_ID] == str(device_id):
                def on_timeout():
                    dev[self.COLUMN_USING_ICON_ID] = ''
                    GObject.source_remove(dev[self.COLUMN_TIMER_HANDLER])
                    dev[self.COLUMN_TIMER_HANDLER] = -1
                    return False
                if dev[self.COLUMN_TIMER_HANDLER] != -1:
                    try:
                        GObject.source_remove(dev[self.COLUMN_TIMER_HANDLER])
                    finally:
                        dev[self.COLUMN_TIMER_HANDLER] = -1
                dev[self.self.COLUMN_USING_ICON_ID] = Gtk.STOCK_CAPS_LOCK_WARNING
                dev[self.COLUMN_TIMER_HANDLER] = GObject.timeout_add(10000, on_timeout)
                break
        return False

    def on_key_press_event(self, ihint, event):
        if ihint.__class__.__name__ == "gtk.TreeMenu" and ihint not in self.__signal_sockets:
            self.__signal_sockets.append(ihint)
            ihint.connect("event", self.on_keypress)
        return True

    def on_device_added(self, device_manager, device):
        self.get_model().append(None,
                                [str(device.props.device_id), device,
                                 Gtk.STOCK_CONNECT, None, True, -1])

    def on_device_changed(self, device_manager, device):
        dev = self.get_model()[str(device.props.device_id)]
        if dev:
            if device.get_device_type() == Gdk.DeviceType.FLOATING and self.get_model().iter_depth(dev):
                dev[self.COLUMN_ENABLED] = False
                dev[self.COLUMN_USING_ICON_ID] = Gtk.STOCK_CAPS_LOCK_WARNING
                self.get_model().append(None, dev)
            else:
                dev[self.COLUMN_USING_ICON_ID] = True
        else:
            self.get_model().append(None,
                                    [str(device.props.device_id), device,
                                     Gtk.STOCK_CONNECT, None, True, -1])

    def on_device_removed(self, device_manager, device):
        if self.props.active_id == str(device.props.device_id):
            self.set_active(0)
        for dev in self.get_model():
            if dev[0] == str(device.props.device_id):
                self.get_model().remove(dev.iter)
                break

    def on_device_selected_by_other(self, widget, device_id):
        if widget != self:
            for dev in self.get_model():
                if dev[0] == device_id:
                    dev[4] = False
                    break

    def on_device_unselected_by_other(self, widget, device_id):
        for dev in self.get_model():
            if dev[0] == device_id:
                dev[4] = True
                break


class CellRendererAudioDevice(Gtk.CellRendererText):
    _device = None

    def get_device(self):
        return self._device

    def set_device(self, device):
        self._device = device
        self.props.sensitive = True
        self.props.ellipsize_set = True
        self.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        if device is not None:
            self.props.text = device.get_name() + " [DeviceID: " + str(device.get_id()) + "]"
        else:
            self.props.text = "--NO DEVICE SELECTED--"

    device = GObject.property(type=PulseSink,
                              flags=GObject.PARAM_READWRITE,
                              setter=set_device,
                              getter=get_device)


class AudioCombo(Gtk.ComboBox):

    def __init__(self):
        Gtk.ComboBox.__init__(self)

        self.set_model(self._create_store_list())

        renderer_device = CellRendererAudioDevice()
        renderer_image = Gtk.CellRendererPixbuf()

        self.pack_start(renderer_image, False)
        self.pack_start(renderer_device, True)

        self.add_attribute(renderer_device, "device", 1)
        self.add_attribute(renderer_device, "sensitive", 3)

        self.add_attribute(renderer_image, "icon-name", 2)
        self.add_attribute(renderer_image, "sensitive", 3)

        self.props.id_column = 0
        self.set_active(0)

    def _create_store_list(self):
        # ID, Object, Icon, Sensitive
        tree_store = Gtk.TreeStore(str, PulseSink, str, bool)

        self.pulse = PulseAudio()

        dev_list = self.pulse.get_sinks()
        for dev in dev_list:
            dev_iter = tree_store.append(None,
                                         [str(dev.get_id()), dev, dev.get_icon(), True])
        return tree_store
