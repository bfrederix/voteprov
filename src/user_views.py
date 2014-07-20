import datetime
import webapp2

from google.appengine.ext.webapp import template
from google.appengine.ext import ndb
from google.appengine.api import taskqueue

from views_base import ViewBase, redirect_locked
from timezone import get_mountain_time
from service import (get_suggestion_pool, get_suggestion, get_player,
                     get_current_show, get_live_vote_exists,
                     create_live_vote, pre_show_voting_post,
                     get_suggestion_pool_page_suggestions)


class MainPage(ViewBase):
    @redirect_locked
    def get(self):
        context = {'current_show': get_current_show()}
        self.response.out.write(template.render(self.path('home.html'),
                                                self.add_context(context)))


class LiveVote(ViewBase):
    def get(self):
        show = get_current_show()
        context = {'vote_options': show.show_option_list}
        self.response.out.write(template.render(self.path('live_vote.html'),
                                                self.add_context(context)))

    def post(self):
        voted = True
        vote_num = int(self.request.get('vote_num', '0'))
        session_id = str(self.session.get('id'))
        
        # Add the task to the default queue.
        taskqueue.add(url='/live_vote_worker/',
                      params={'show': self.context['current_show'],
                              'vote_num': vote_num,
                              'session_id': session_id})
        show = get_current_show()
        context = {'vote_options': show.show_option_list}
        self.response.out.write(template.render(self.path('live_vote.html'),
                                                self.add_context(context)))


class LiveVoteWorker(webapp2.RequestHandler):
    def post(self):
        player_key = None
        suggestion_key = None
        interval = None
        state = None
        # Get the current show
        show = get_current_show()
        vote_num = int(self.request.get('vote_num'))
        session_id = self.request.get('session_id')
        vote_data = show.current_vote_options(voting_only=True)
        # If we're in the voting period
        if vote_data.get('display') == 'voting':
            state = vote_data['state']
            try:
                voted_option = vote_data['options'][vote_num]
            except IndexError:
                state = None
        # Cast the interval to an int if it exists
        if vote_data.get('interval'):
            interval = int(vote_data.get('interval'))
        # Get the suggestion key, if it exist
        if voted_option.get('id'):
            # If this is a player vote
            if show.current_vote_type \
                and show.current_vote_type.get().style in ['player-pool', 'all-players']:
                player_key = get_player(key_id=voted_option.get('id'), key_only=True)
            # else this is a suggestion vote
            else:
                suggestion_key = get_suggestion(key_id=voted_option.get('id'), key_only=True)
        # Get the player key, if it exists
        if vote_data.get('player_id'):
            player_key = get_player(key_id=vote_data.get('player_id'), key_only=True)
        # If there is a voting state of some kind
        if state and state != 'default':
            # Determine if a live vote exists for this already
            vote_exists = get_live_vote_exists(show.key,
                                               show.current_vote_type,
                                               interval,
                                               session_id,
                                               player=player_key,
                                               suggestion=suggestion_key)
            # If they haven't voted yet, create the live vote
            if not vote_exists:
                create_live_vote({'suggestion': suggestion_key,
                                  'vote_type': show.current_vote_type,
                                  'player': player_key,
                                  'show': show.key,
                                  'interval': interval,
                                  'session_id': session_id})


class AddSuggestions(ViewBase):
    @redirect_locked
    def get(self, suggestion_pool_name=None):
        if suggestion_pool_name:
            current_suggestion_pool = get_suggestion_pool(name=suggestion_pool_name)
        else:
            try:
                current_suggestion_pool = self.context['current_suggestion_pools'][0]
            except IndexError:
                current_suggestion_pool = None
        # Get all the suggestions from the current pool
        suggestions = get_suggestion_pool_page_suggestions(
                        getattr(current_suggestion_pool, 'key', None))
        context = {'current_suggestion_pool': current_suggestion_pool,
                   'suggestions': suggestions,
                   'session_id': str(self.session.get('id', '0')),
                   'item_count': len(suggestions)}
        self.response.out.write(template.render(self.path('add_suggestions.html'),
                                                self.add_context(context)))

    @redirect_locked
    def post(self, suggestion_pool_name):
        if self.current_user:
            user_id = self.current_user.user_id()
        else:
            user_id = None
        current_suggestion_pool = get_suggestion_pool(name=suggestion_pool_name)
        context = pre_show_voting_post(getattr(self.current_show, 'key', None),
                                       current_suggestion_pool,
                                       self.request,
                                       str(self.session.get('id', '0')),
                                       user_id,
                                       self.context.get('is_admin', False))

        context.update({'current_suggestion_pool': current_suggestion_pool,
                        'item_count': len(context['suggestions'])})
        self.response.out.write(template.render(self.path('add_suggestions.html'),
                                                self.add_context(context)))


class AllTimeLeaderboard(ViewBase):
    @redirect_locked
    def get(self):            
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("All-Time Leaderboard")


# Used to handle the user leaderboard url properly
class UserLeaderboard(ViewBase):
    @redirect_locked
    def get(self, user_id):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("User ID: %s" % user_id)


# Used to handle the show leaderboard url properly
class ShowLeaderboard(ViewBase):
    @redirect_locked
    def get(self, show_id):
        # If user is an admin
        if self.context.get('is_admin', False):
            # Make sure to set the show leaderboard to hidden
            #(thwart race condition on the show admin page)
            show = get_show(key_id=show_id)
            show.showing_leaderboard = False
            show.put()
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("Show ID: %s" % show_id)