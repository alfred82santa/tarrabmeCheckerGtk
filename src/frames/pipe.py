from gi.repository import GObject, Gst

class Pipe:
    def on_pad_added(self, dbin, pad):
        pad.link(self.convert.get_static_pad("sink"))    
        
    def __init__(self, name, filename):
        self.pipe = Gst.Bin.new(name)
        
        self.src = Gst.ElementFactory.make ("filesrc", name + "_src")
        self.src.set_property("location", filename)
        self.pipe.add(self.src)
        
        self.decode = Gst.ElementFactory.make ("decodebin", name + "_decode")
        self.pipe.add(self.decode)
        #caps = Gst.caps_from_string("audio/x-raw")
        #self.decode.set_property("caps", caps)
        self.src.link(self.decode)
        self.decode.connect("pad-added", self.on_pad_added)
        
        self.convert = Gst.ElementFactory.make ("audioconvert", name + "_convert")
        self.pipe.add(self.convert)
        
        #self.convert2 = Gst.ElementFactory.make ("audioconvert", name + "_convert2")
        #self.pipe.add(self.convert2)
        #self.convert.link_filtered(self.convert2, caps)
        
        self.volume = Gst.ElementFactory.make ("volume", "volume")
        self.pipe.add(self.volume)
        #self.volume.set_property("caps", caps)
        #caps = Gst.caps_from_string("audio/x-raw,channels=2")
        #caps = Gst.caps_from_string("audio/x-raw,channels=1")
        #self.convert.link_filtered(self.volume, caps)
        self.convert.link(self.volume)

        self.ghost = Gst.GhostPad.new('src', self.volume.get_static_pad('src'))
        self.ghost.set_active(True)
        self.pipe.add_pad(self.ghost)
