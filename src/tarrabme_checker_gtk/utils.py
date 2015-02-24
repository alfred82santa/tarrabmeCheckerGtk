import time
from datetime import datetime, timezone, timedelta
from gi.repository import GLib

__author__ = 'alfred'


def get_utcdatetime_from_iso8601(date_str):
    success, g_time = GLib.TimeVal.from_iso8601(date_str)
    dt = datetime.utcfromtimestamp(g_time.tv_sec)
    return dt.replace(microsecond=g_time.tv_usec).replace(tzinfo=timezone.utc)


def get_timedelta_text(base_date, item_date):
    t_delta = base_date - item_date
    tz = timezone(timedelta(seconds=-time.timezone))
    item_date = item_date.astimezone(tz)

    if t_delta.days == 0:
        if t_delta.seconds == 0:
            return "Just now"
        minutes = int(t_delta.seconds / 60)
        if minutes == 0:
            return "{0} seconds ago".format(t_delta.seconds)
        hours = int(minutes / 60)
        if hours == 0:
            return "{0}:{1:02d} minutes ago".format(minutes,
                                                    t_delta.seconds - (minutes * 60))

        return "{0}:{1:02d} hours ago".format(hours,
                                              minutes - (hours * 60))

    elif t_delta.days == 1:
        return "Yesterday at {0}".format(item_date.strftime('%H:%M'))
    else:
        return "{0} days ago at {0}".format(t_delta.days, item_date.strftime('%H:%M'))


def get_datetime_label(value):
    dt = get_utcdatetime_from_iso8601(value)
    txt = get_timedelta_text(datetime.utcnow().replace(tzinfo=timezone.utc),
                             dt)
    tz = timezone(timedelta(seconds=-time.timezone))
    return "\n".join([txt, dt.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')])
