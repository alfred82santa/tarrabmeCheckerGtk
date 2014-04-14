#!/usr/bin/python3
#
# safeticketapp.py
# Copyright (C) Alfred 2012 <alfred82santa@gmail.com>
# 
# safeTicketApp is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# safeTicketApp is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, sys
from gi.repository import Gtk, Gio, GObject, Gst, GdkPixbuf, GLib
from frames.reader import Reader
from config import *


WINDOWS = 1
ROWS_PER_WINDOWS = 2
COLUMNS_PER_WINDOW = 2


class TarrabmeCheckerApp(Gtk.Application):
    CONFIG_SCHEMA = "apps.tarrabme.checker"
    
    def __init__(self):
        Gtk.Application.__init__(self, application_id="org.me.tarrab.Checker", 
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
                                 
        GLib.set_application_name("Tarrab.me Checker")
        GLib.set_prgname('tarrabme-Checker')
        
        self.register(None)
        
        if not self.get_is_remote():
            self.connect('activate', self.on_activate)
            
            self.settings = Gio.Settings.new(self.CONFIG_SCHEMA)
            
            resource = Gio.Resource.load(os.path.join(MEDIA_PATH, "tarrabme-checker-resources.gresource"))
            
            Gio.Resource._register(resource)
            
            self.readers = []
            self._cache_keypress = {}
            Gst.init_check(None)
            icon = GdkPixbuf.Pixbuf.new_from_resource('/org/me/tarrab/Checker/tarrab-me-icon.png')
            for win in range(self.settings.get_int("window-count")):
                window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
                window.set_icon(icon)
                window.set_wmclass("tarrab_checker", "tarrab.me Checker")
                window.set_title("tarrab.me Checker")
                
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                box.set_homogeneous(True)
                
                window.set_titlebar(box)
                
                self.add_window(window)
                
                grid = Gtk.Grid()
                grid.set_row_homogeneous(True)
                grid.set_column_homogeneous(True)
                
                for row in range(self.settings.get_int("row-count")):
                    grid.insert_row(0)
                for column in range(self.settings.get_int("column-count")):
                    grid.insert_column(0)

                    
                for row in range(self.settings.get_int("row-count")):
                    for column in range(self.settings.get_int("column-count")):
                        index = row * self.settings.get_int("column-count") + column + 1
                        reader = Reader(window, "reader " + index)
                        
                        grid.attach(reader, column, row, 1 , 1)
                        
                        reader.set_settings(self.settings, index)
                        
                        self.readers.append(reader)
                        
                        reader.connect("key-press-event", self.on_keypress_event)
                        
                        if row == 0:
                            #if column != 0:
                                #box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
                            hsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
                            reader.remove(reader.toolbar)
                            box.pack_start(reader.toolbar, True, True, 0)
                            hsize_group.add_widget(reader.toolbar)
                            hsize_group.add_widget(reader)
                        
                window.add(grid)
                window.show_all()
        else:
            print("Application already running")
            self.quit()
    def on_activate(self, app):
        pass
    def on_keypress_event(self, widget, event):
        device_id = str(event.get_source_device().props.device_id)
        for reader in self.readers:
            if reader.scanner_id == device_id:
                if device_id not in self._cache_keypress:
                    self._cache_keypress[device_id] = ''
                if len(event.string) > 0:
                    for i in range(len(event.string)):
                        if ord(event.string[i]) != 13:
                            self._cache_keypress[device_id] += event.string
                        elif len(self._cache_keypress[device_id]):
                            reader.on_scan_barcode(self._cache_keypress[device_id])
                            self._cache_keypress[device_id] = ''
                break
        return True
                            
    def on_commandline(self, app, command_line):
        return 0       
    def destroy(self, window):
        self.quit()

if __name__ == "__main__":
    GObject.threads_init()
    app = TarrabmeCheckerApp()
    sys.exit(app.run(sys.argv))

