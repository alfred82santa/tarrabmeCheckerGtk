import os, sys
from gi.repository import WebKit, Gtk, Gdk, Soup
from config import *
import pprint
class LoginDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "Login", parent, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.cookieJar = Soup.CookieJar()
        WebKit.get_default_session().add_feature(self.cookieJar)
        self.browser = WebKit.WebView()
        self.browser.connect("navigation-policy-decision-requested", self.on_request)
        self.set_default_size(390, 350)
        self._onload_handler = None
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.browser)
        box = self.get_content_area()
        box.pack_start(scrolled_window, True, True, 0)
        self.browser.open(get_base_url() + get_login_path())
        self.set_modal(True)
        self.show_all()   
    def destroy(self):
        WebKit.get_default_session().remove_feature(self.cookieJar)
        Gtk.Dialog.destroy(self)     
    def on_request(self, web_view, web_frame, request, navigation_action, policy_decision):
        if navigation_action.get_reason() == WebKit.WebNavigationReason.FORM_SUBMITTED and self._onload_handler is None:
            self._onload_handler = self.browser.connect("onload-event", self.on_response)
        return False
    def on_response(self, web_view, web_frame):
        if web_frame.get_network_response().get_message().props.status_code == 200 \
                and web_frame.get_network_response().get_uri() == get_base_url() + get_about_path():
            self.username = web_view.props.title.split('|', 1)[0].strip()
            self.response(Gtk.ResponseType.ACCEPT) 
        
        

