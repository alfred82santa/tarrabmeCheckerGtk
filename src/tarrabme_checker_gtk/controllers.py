import json
from .models import DictObject

__author__ = 'alfred'
from gi.repository import GObject, Soup, GLib, Gio, Gtk


class TarrabmeController(GObject.GObject):
    __gsignals__ = {
        "request-change-step": (GObject.SIGNAL_RUN_LAST, bool, (str, str,)),
        "leaving-step": (GObject.SIGNAL_RUN_LAST, None, (str, str,)),
        "change-step": (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        "result": (GObject.SIGNAL_RUN_FIRST, None, (str, str, DictObject, )),
        "login": (GObject.SIGNAL_RUN_FIRST, None, (DictObject, )),
        "login-error": (GObject.SIGNAL_RUN_FIRST, None, (DictObject, )),
        "logout": (GObject.SIGNAL_RUN_FIRST, None, []),
    }

    STEP_LOGIN = 'login'
    STEP_CHECK_LOGIN = 'check_login'
    STEP_SCAN = 'scan'
    STEP_REQUEST = 'request'
    STEP_RESPONSE = 'response'
    STEP_NOP = 'nop'

    RESULT_SUCCESS = 'success'
    RESULT_ALREADY_USED_ERROR = 'already_used_error'
    RESULT_NOT_FOUND_ERROR = 'not_found_error'
    RESULT_DISABLED_ERROR = 'disabled_error'
    RESULT_UNKNOWN_ERROR = 'unknown_error'

    code = GObject.property(type=str)

    def __init__(self, reader):
        GObject.GObject.__init__(self)
        self.reader = reader
        self.step = self.STEP_NOP
        self.socket = Soup.Session()
        self.cookie_session = Soup.CookieJar()
        self.socket.add_feature(self.cookie_session)
        self.code = None
        self.last_response = None
        self.last_data = None
        self._last_message = None
        self._logged = False
        self._login_message = None
        self.cancellable = Gio.Cancellable()
        self.check_login()

    def go_forward_step(self):
        if self.step == self.STEP_LOGIN:
            if self.has_login_request():
                self.next_step()
        elif self.step == self.STEP_CHECK_LOGIN:
            if self.has_session():
                self.next_step()
            elif not self.has_login_request():
                self.set_step(self.STEP_LOGIN)
        elif self.step == self.STEP_REQUEST:
            if not self.has_session():
                self.set_step(self.STEP_LOGIN)
            elif not self.has_code_request():
                self.set_step(self.STEP_SCAN)
            elif self.has_response():
                self.next_step()
        elif self.step == self.STEP_SCAN:
            if not self.has_session():
                self.set_step(self.STEP_LOGIN)
            elif self.has_code_request():
                self.next_step()

        return False

    def next_step(self):
        if self.step == self.STEP_LOGIN:
            self.set_step(self.STEP_CHECK_LOGIN)
        elif self.step == self.STEP_CHECK_LOGIN:
            self.set_step(self.STEP_SCAN)
        elif self.step == self.STEP_SCAN:
            self.set_step(self.STEP_REQUEST)
        elif self.step == self.STEP_REQUEST:
            self.set_step(self.STEP_RESPONSE)

    def has_session(self):
        return self._logged

    def has_code_request(self):
        return self.code is not None

    def has_response(self):
        return self.last_response is not None

    def has_login_request(self):
        return self._login_message is not None

    def async_go_forward_step(self):
        GLib.idle_add(self.go_forward_step)

    def async_set_step(self, step):
        def inner_set_step():
            self.set_step(step)
            return False
        GLib.idle_add(inner_set_step)

    def set_step(self, step):
        if self.step == step:
            print('Alredy step: {}'.format(step))
            self.async_go_forward_step()
            return False

        print('Request next step: {}'.format(step))
        deny_change = self.emit('request-change-step', self.step, step)
        if deny_change:
            print('Deny next step: {}'.format(step))
            self.async_go_forward_step()
            return False

        print('Leaving step: {}'.format(self.step))
        self.emit('leaving-step', self.step, step)
        self.step = step
        self.emit('change-step', self.step)
        print('Changed to step: {}'.format(step))
        self.async_go_forward_step()
        return True

    def do_request_change_step(self, current_step, next_step, *args, **kwargs):
        if next_step == self.STEP_NOP:
            return False
        if next_step == self.STEP_CHECK_LOGIN and not self.has_login_request():
            self.stop_emission('request-change-step')
            return True
        if current_step == self.STEP_LOGIN and not self.has_login_request():
            self.stop_emission('request-change-step')
            return True
        if next_step in [self.STEP_SCAN, self.STEP_REQUEST] and not self.has_session():
            self.stop_emission('request-change-step')
            return True
        if next_step == self.STEP_RESPONSE and not self.has_response():
            self.stop_emission('request-change-step')
            return True
        if next_step == self.STEP_REQUEST and not self.has_code_request():
            self.stop_emission('request-change-step')
            return True

    def do_change_step(self, step):
        if self.step == self.STEP_LOGIN:
            self.login_action()
        elif self.step == self.STEP_CHECK_LOGIN:
            self.check_login_action()
        elif self.step == self.STEP_SCAN:
            self.scan_action()
        elif self.step == self.STEP_REQUEST:
            self.request_action()
        elif self.step == self.STEP_RESPONSE:
            self.response_action()
        elif self.step == self.STEP_NOP:
            self.nop_action()

    def do_leaving_step(self, step, next_step):
        if step == self.STEP_RESPONSE:
            self.last_response = None
            self.last_data = None
            self.code = None
        elif step == self.STEP_CHECK_LOGIN:
            self._login_message = None
        elif step == self.STEP_REQUEST:
            if self._last_message:
                self.socket.cancel_message(self._last_message, Soup.STATUS_CANCELLED)

    def request_new_code(self, code):
        print("Request code: {}".format(code))
        if self.step != self.STEP_SCAN:
            return
        self.code = code
        self.go_forward_step()

    def request_action(self):
        path = self.reader.app.settings.get_string("attempt-path").format(code=self.code)
        url = self.get_uri_from_path(path)

        self._last_message = Soup.Message.new(self.reader.app.settings.get_string("attempt-method"),
                                              url)
        self.send_message(self._last_message, self.scan_code_response_cb)

    def scan_code_response_cb(self, session, message, data):
        self._last_message = None
        if message.props.status_code != Soup.Status.CANCELLED:
            self.last_response = message
        self.go_forward_step()

    def response_action(self):
        self.last_response.props.response_body.flatten()

        try:
            self.last_data = json.loads(self.last_response.props.response_body.data)

            result_map = {201: self.RESULT_SUCCESS,
                          404: self.RESULT_NOT_FOUND_ERROR,
                          471: self.RESULT_DISABLED_ERROR,
                          470: self.RESULT_ALREADY_USED_ERROR}
            result = result_map[self.last_response.props.status_code]
        except (KeyError, ValueError):
            result = self.RESULT_UNKNOWN_ERROR

        self.emit('result', self.code, result, DictObject(self.last_data))

        if self.last_response.props.status_code not in [201, 404, 470, 471]:
            self.check_login()

    def login_action(self):
        if self._logged:
            self.logout()
        self._logged = False

    def scan_action(self):
        pass

    def nop_action(self):
        pass

    def check_login_action(self):
        pass

    def get_uri_from_path(self, path):
        return "/".join([self.reader.app.settings.get_string("baseurl").rstrip('/'),
                         path.lstrip('/')])

    def prepare_message(self, msg):
        msg.props.request_headers.append('Accept', 'application/json')
        for cookie in self.cookie_session.all_cookies():
            if cookie.get_name() == 'csrftoken':
                msg.props.request_headers.append("X-CSRFToken", cookie.get_value())
                break

    def send_message(self, message, callback, cancellable=None):
        self.prepare_message(message)
        self.socket.queue_message(message, callback, cancellable or self.cancellable)

    def set_credentials(self, username, password):
        if self.step != self.STEP_LOGIN:
            return
        path = self.reader.app.settings.get_string("login-path")
        url = self.get_uri_from_path(path)
        data = {'username': username, 'password': password}
        self._login_message = Soup.Message.new(self.reader.app.settings.get_string("login-method"),
                                               url)

        self._login_message.set_request("application/json",
                                        Soup.MemoryUse.COPY,
                                        json.dumps(data).encode('UTF-8'))
        self.send_message(self._login_message, self.login_cb)
        self.go_forward_step()

    def check_login(self):
        path = self.reader.app.settings.get_string("account-path")
        url = self.get_uri_from_path(path)
        self._login_message = Soup.Message.new('GET', url)
        self.send_message(self._login_message, self.login_cb)
        self.async_go_forward_step()

    def logout(self):
        path = self.reader.app.settings.get_string("logout-path")
        url = self.get_uri_from_path(path)
        self._login_message = Soup.Message.new(self.reader.app.settings.get_string("logout-method"), url)
        self.send_message(self._login_message, self.logout_cb)
        self.async_go_forward_step()

    def logout_cb(self, session, message, data):
        self._logged = False
        self._login_message = None
        self.emit('logout')
        self.go_forward_step()

    def login_cb(self, session, message, data):
        self._login_message = None
        message.props.response_body.flatten()
        if message.props.response_body.data:
            data = json.loads(message.props.response_body.data)
        else:
            data = {"error": "Unknown error"}
        if message.props.status_code == 200:
            self._logged = True
            self.emit('login', DictObject(data))
        else:
            self._logged = False
            self.emit('login_error', DictObject(data))
        self.async_go_forward_step()

    def cancel_operations(self):
        self.cancellable.cancel()
        self.cancellable = Gio.Cancellable()
        self._last_message = None
        self.check_login()


class RecentAttemptsController(GObject.GObject):

    max_items = 1

    def __init__(self, reader, max_items=1):
        assert max_items > 0, "Recent attempts stack length must be greater than 0"
        GObject.GObject.__init__(self)

        self.stack = []
        self.max_items = max_items
        self.reader = reader
        self.label = self.reader.builder.get_object('last_scanned_code_label')
        self.image = self.reader.builder.get_object('last_scanned_code_image')

        self.reader.controller.connect('change-step', self.change_step_cb)
        self.reader.controller.connect('result', self.result_cb)
        self.refresh_widget()

    def result_cb(self, controller, code, status, data):
        self.stack.insert(0, {'code': code, 'status': status})
        while len(self.stack) > self.max_items:
            self.stack.pop()

    def change_step_cb(self, controller, step):
        if step == TarrabmeController.STEP_REQUEST:
            self.refresh_widget()

    def refresh_widget(self):
        labig_map = {TarrabmeController.RESULT_SUCCESS: ('SUCCESS: {code}',
                                                         'emblem-default'),
                     TarrabmeController.RESULT_NOT_FOUND_ERROR: ('CODE NOT FOUND: {code}',
                                                                 'dialog-error'),
                     TarrabmeController.RESULT_ALREADY_USED_ERROR: ('ALREADY USED CODE: {code}',
                                                                    'dialog-error'),
                     TarrabmeController.RESULT_DISABLED_ERROR: ('DISABLED CODE: {code}',
                                                                'dialog-error'),
                     TarrabmeController.RESULT_UNKNOWN_ERROR: ('UNKNOWN ERROR: {code}',
                                                               'dialog-error')}

        try:
            data = self.stack[0]
            label, image = labig_map[data['status']]
            label = label.format(code=data['code'])
        except KeyError:
            label = 'SYSTEM ERROR!'
            image = 'gtk-dialog-error'
        except IndexError:
            label = 'No scanned code, yet'
            image = 'dialog-warning'

        self.label.set_label(label)
        self.image.set_from_icon_name(image, Gtk.IconSize.DIALOG)


class AutoScanController(GObject.GObject):

    REFRESH_MS = 10
    MAX_PROGRESS = 100

    def __init__(self, reader):
        GObject.GObject.__init__(self)

        self.reader = reader

        self.progress_bar = self.reader.builder.get_object('waiting_bar')
        self.progress_bar_revealer = self.reader.builder.get_object('waiting_bar_revealer')
        self.progress_bar.set_max_value(self.MAX_PROGRESS)
        self.reader.controller.connect('change-step', self.change_step_cb)

        self.timeout_handler = None

    def change_step_cb(self, controller, step):
        if step != TarrabmeController.STEP_RESPONSE:
            if self.timeout_handler:
                self.progress_bar_revealer.props.reveal_child = False
                GLib.source_remove(self.timeout_handler)
                self.timeout_handler = None
            return
        delay = self.reader.settings.get_double("delay")
        if delay:
            self.progress_bar_revealer.props.reveal_child = True
            self.progress_bar.set_value(0)
            value = self.MAX_PROGRESS * self.REFRESH_MS / (delay * 1000)
            self.timeout_handler = GLib.timeout_add(self.REFRESH_MS, self.get_timeout_callback(value))
        else:
            self.progress_bar_revealer.props.reveal_child = False
            self.reader.controller.async_set_step(TarrabmeController.STEP_SCAN)

    def get_timeout_callback(self, value):
        def cb():
            self.progress_bar.set_value(self.progress_bar.get_value() + value)
            if self.progress_bar.get_value() >= self.MAX_PROGRESS:
                self.timeout_handler = None
                self.progress_bar_revealer.props.reveal_child = False
                self.reader.controller.async_set_step(TarrabmeController.STEP_SCAN)
                return False

            return True

        return cb
