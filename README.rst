Tarrab.me Checker Gtk
=====================

.. _TarrabServer: https://github.com/alfred82santa/tarrabserv/
.. _screenshots: docs/source/screenshots.rst 

Ticket checker for events. Gtk3 client for TarrabServer_.

Look at screenshots_.

Install requirements
====================

It must be execute in a Gnome 3.12 environment.

.. code-block:: bash
    
    $ sudo apt-get install gobject-introspection gir1.2-soup-2.4 gir1.2-gtk-3.0 \
      gir1.2-gtkclutter-1.0 gir1.2-gstreamer-1.0 gir1.2-clutter-gst-1.0 \
      gir1.2-glib-2.0 gir1.2-gudev-1.0 gir1.2-gdkpixbuf-2.0 \
      python3 python3-gi pulseaudio gstreamer1.0-pulseaudio gstreamer1.0-plugins-good \
      gstreamer1.0-plugins-ugly gstreamer1.0-plugins-bad
      
PulseAudio Config
-----------------

Tarrab.me Checker Gtk needs pulseaudio access via dbus. So you must add below line to ``/etc/pulse/default.pa`` file
and reboot pulseaudio.

.. code-block::

    load-module module-dbus-protocol
      
Run application
===============

On project root directory:

.. code-block:: bash

    $ make buildrun



