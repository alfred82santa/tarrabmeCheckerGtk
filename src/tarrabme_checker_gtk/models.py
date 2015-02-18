from gi.repository import GObject

__author__ = 'alfred'


class DictObject(GObject.GObject):

    def __init__(self, data):
        GObject.GObject.__init__(self)
        self.data = data
