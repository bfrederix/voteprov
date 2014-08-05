import os
import random
import datetime
from functools import wraps

import webapp2
from webapp2_extras import sessions
from google.appengine.api import users

from service import (get_current_show, get_current_suggestion_pools,
                     get_user_profile, create_user_profile)
from timezone import get_mountain_time

LIVE_VOTE_URI = '/live_vote/'


def get_or_default(item, default):
    if item == '' or item == None:
        return default
    return item


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not users.is_current_user_admin():
            redirect_uri = users.create_login_url(webapp2.get_request().uri)
            return webapp2.redirect(redirect_uri, abort=True)
        return func(*args, **kwargs)
    return decorated_view


def redirect_locked(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        show = get_current_show()
        if show and show.locked and not users.is_current_user_admin():
            return webapp2.redirect(LIVE_VOTE_URI, abort=True)
        return func(*args, **kwargs)
    return decorated_view


class ViewBase(webapp2.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(ViewBase, self).__init__(*args, **kwargs)
        self.app = webapp2.get_app()
        auth_url, auth_action = self.get_auth_data()
        self.current_show = get_current_show()
        self.context = {
                    'host_domain': self.request.host_url.replace('http://', ''),
                    'image_path': self.app.registry.get('images'),
                    'css_path': self.app.registry.get('css'),
                    'js_path': self.app.registry.get('js'),
                    'audio_path': self.app.registry.get('audio'),
                    'player_image_path': self.app.registry.get('player_images'),
                    'is_admin': users.is_current_user_admin(),
                    'user': self.user,
                    'username': self.username,
                    'auth_url': auth_url,
                    'auth_action': auth_action,
                    'path_qs': self.request.path_qs,
                    'current_show': self.current_show,
                    'show_today': bool(self.current_show),
                    'current_suggestion_pools': get_current_suggestion_pools(self.current_show)}
    
    def get_auth_data(self):
        """Used to get the auth action and the auth url
           based on if you are authenticated
        """
        # If the user is logged in
        if self.user:
            auth_url = users.create_logout_url(self.request.uri)
            auth_action = 'Logout'
        # If they aren't logged in
        else:
            # Attempt to update the user profile's session with google auth
            self.user = self.google_login()
            # If the user is now logged in
            if self.user:
                auth_url = users.create_logout_url(self.request.uri)
                auth_action = 'Logout'
            # If the user still isn't logged in
            else:
                auth_url = users.create_login_url(self.request.uri)
                auth_action = 'Login'
        return auth_url, auth_action
    
    def google_login(self):
        """Used to login and update the user profile session
           or create the initial user profile
        """
        user = users.get_current_user()
        # If the user is logged in via Google
        if user:
            # Try to get the user profile by user id
            user_profile = get_user_profile(user_id=user.user_id())
            # If we've found the user profile, update the session
            if user_profile:
                user_profile.current_session = self.session.get('id')
                user_profile.put()
                return user_profile
            else:
                # Try to get the user profile by email
                user_profile = get_user_profile(email=user.email())
                if user_profile:
                    # If the profile was found by email, set the current session
                    user_profile.current_session = self.session.get('id')
                    user_profile.put()
                    return user_profile
                else:
                    # Create the userprofile from the google login
                    user_profile = create_user_profile({'user_id': user.user_id(),
                                                        'email': user.email(),
                                                        'username': user.nickname(),
                                                        'created': get_mountain_time()})
                    return user_profile.get()
        return None
    
    def add_context(self, add_context={}):
        self.context.update(add_context)
        return self.context
    
    def path(self, filename):
        return os.path.join(self.app.registry.get('templates'), filename)

    def dispatch(self):
        self.session_store = sessions.get_store(request=self.request)
        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        session = self.session_store.get_session()
        if not session.get('id'):
            # Get a random hash to store as the session id
            session['id'] = random.getrandbits(128)
        return session
    
    @property
    def user_id(self):
        """Returns currently logged in user's id"""
        return getattr(self.user, 'user_id', None)
    
    @property
    def username(self):
        """Returns currently logged in user's id"""
        return getattr(self.user, 'username', None)
    
    @property
    def user(self):
        """Returns currently logged in user"""
        # Try to get the user profile by session id
        user_profile = get_user_profile(current_session=self.session.get('id', '-1'))
        if user_profile:
            return user_profile
        return None


class RobotsTXT(webapp2.RequestHandler):
    def get(self):
        # Set to not be indexed
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("User-agent: *\nDisallow: /")


class LoaderIO(webapp2.RequestHandler):
    def get(self):
        # Set to not be indexed
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("loaderio-9b6fa50492da1609dc61b9198b767688")