from .notification import Notification
from config import *


class NotificationEmitter():

    def __init__(self, name="notificationEmitter", balance=Notification.CENTER,
                 device_id=None, volume=1.0):
        self._notifications = {}
        self._balance = balance
        self._device_id = device_id
        self._volume = volume
        self.set_name(name)

    def set_balance(self, balance):
        self._balance = balance
        for key in self._notifications:
            self._notifications[key].set_balance(self._balance)

    def set_device_id(self, device):
        self._device_id = device
        for key in self._notifications:
            self._notifications[key].set_pulse_device(self._device_id)

    def set_name(self, name):
        self._name = name
        for key in self._notifications:
            self._notifications[key].set_name(self._name + "." + key)

    def add_notification(self, name, filename, volume):
        self._notifications[name] = Notification(filename,
                                                 name=self._name + "." + name,
                                                 balance=self._balance,
                                                 device_id=self._device_id,
                                                 volume=self._volume,
                                                 volume_ampl=volume)

    def play_notification(self, name):
        if name in self._notifications:
            self._notifications[name].play()


def make_notification_emitter(name='default', device_id=None, balance=Notification.CENTER,
                              volume_general=1.0, volume_read=1.0, volume_success=1.0, volume_fail=1.0):
    emitter = NotificationEmitter(name, balance, device_id, volume_general)
    emitter.add_notification('read', get_read_sound(), volume_read)
    emitter.add_notification('success', get_success_sound(), volume_success)
    emitter.add_notification('fail', get_fail_sound(), volume_fail)
    return emitter
