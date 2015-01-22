from google.appengine.api import memcache

from service import get_show_recap


def get_cached_show_recap(show_id):
    key = "recap-{0}".format(show_id)
    show_data = memcache.get(key)
    if show_data is not None:
        return show_data
    else:
        show_data = get_show_recap(show_id)
        # Cache for a week
        memcache.add(key, show_data, 604800)
        return show_data