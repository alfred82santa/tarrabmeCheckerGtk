from gi.repository import Gdk


def get_device_by_id(device_id):
        if device_id is None:
            return None
        man = Gdk.Display.get_default().get_device_manager()
        dev_list = man.list_devices(Gdk.DeviceType.SLAVE)
        for dev in dev_list:
            if str(dev.props.device_id) == device_id:
                return dev
        dev_list = man.list_devices(Gdk.DeviceType.FLOATING)
        for dev in dev_list:
            if str(dev.props.device_id) == device_id:
                return dev
        dev_list = man.list_devices(Gdk.DeviceType.MASTER)
        for dev in dev_list:
            if str(dev.props.device_id) == device_id:
                return dev
        return None
