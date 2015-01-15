from os import path
#BASE_URL = "http://127.0.0.1:8000"
#BASE_URL = "http://192.168.2.107"
#BASE_URL = "http://192.168.50.253"
LOGIN_PATH = "/users/login"
ABOUT_PATH = "/users/me"
ATTEMPT_PATH = "/codes/%code%/attempt"

MEDIA_PATH = path.join(path.dirname(path.realpath(__file__)), '..', 'media')
CONFIG_PATH = path.join(path.dirname(path.realpath(__file__)), '..', 'config')


def get_base_url():
    return BASE_URL


def get_login_path():
    return LOGIN_PATH


def get_about_path():
    return ABOUT_PATH


def get_attempt_path():
    return ATTEMPT_PATH


def get_read_sound():
    return "resource:///org/me/tarrab/Checker/read_sound.wav"


def get_success_sound():
    return "resource:///org/me/tarrab/Checker/success_sound.wav"


def get_fail_sound():
    return "resource:///org/me/tarrab/Checker/fail_sound.wav"


def get_app_icon_file():
    return path.join(MEDIA_PATH, "tarrabme.png")
