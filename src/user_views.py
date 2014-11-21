import datetime

import webapp2

from google.appengine.ext.webapp import template
from google.appengine.api import taskqueue

from views_base import ViewBase, redirect_locked, admin_required
from timezone import get_mountain_time
from service import (get_suggestion_pool, get_suggestion, get_player,
                     get_show, get_user_profile, get_leaderboard_entry,
                     fetch_shows, fetch_leaderboard_entries, fetch_user_profiles,
                     fetch_medals, fetch_leaderboard_spans, fetch_suggestions,
                     get_current_show, get_live_vote_exists,
                     create_live_vote, create_leaderboard_entry,
                     create_leaderboard_span, pre_show_voting_post,
                     get_suggestion_pool_page_suggestions,
                     award_leaderboard_medals, update_user_profile)


# HARDCODED SUGGESTION LIMIT
SHOW_SUGGESTION_LIMIT = 70
USER_SUGGESTION_LIMIT = 5


class MainPage(ViewBase):
    @redirect_locked
    def get(self):
        context = {'current_show': get_current_show()}
        self.response.out.write(template.render(self.path('home.html'),
                                                self.add_context(context)))


class LiveVote(ViewBase):
    def get(self):
        show = get_current_show()
        context = {'vote_options': getattr(show, 'show_option_list', None)}
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
                              'session_id': session_id,
                              'user_id': self.user_id})
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
        # Make sure there is a current vote type
        if show and show.current_vote_type:
            vote_type = show.current_vote_type.get()
        else:
            vote_type = None
            state = None
        vote_num = int(self.request.get('vote_num'))
        session_id = self.request.get('session_id')
        user_id = self.request.get('user_id')
        # Catch string "None"
        if user_id == "None":
            user_id = None
        # Only try to determine state if there is a current vote type
        if vote_type and show:
            vote_data = show.current_vote_options(voting_only=True)
            # If we're in the voting period
            if vote_data.get('display') == 'voting':
                state = vote_data['state']
                try:
                    voted_option = vote_data['options'][vote_num]
                except IndexError:
                    state = None
        # If there is a voting state of some kind
        if state and state != 'default':
            # Cast the interval to an int if it exists
            if vote_data.get('interval'):
                interval = int(vote_data.get('interval'))
            # Get the suggestion key, if it exist
            if voted_option.get('id'):
                # If this is a player vote
                if show.current_vote_type \
                    and vote_type.style in ['player-pool', 'all-players']:
                    player_key = get_player(key_id=voted_option.get('id'),
                                            key_only=True)
                # else this is a non-player related suggestion vote
                elif vote_type != 'player-options':
                    suggestion_key = get_suggestion(key_id=voted_option.get('id'),
                                                    key_only=True)
            # Get the player key elsewhere, if it exists
            if vote_data.get('player_id'):
                player_key = get_player(key_id=vote_data.get('player_id'),
                                        key_only=True)
            # Determine if a live vote exists for this
            # show-vote_type-interval-player-session_id already
            vote_exists = get_live_vote_exists(show.key,
                                               show.current_vote_type,
                                               interval,
                                               session_id)
            # If they haven't voted yet, create the live vote
            if not vote_exists:
                # Create the live vote
                create_live_vote({'suggestion': suggestion_key,
                                  'vote_type': show.current_vote_type,
                                  'player': player_key,
                                  'show': show.key,
                                  'interval': interval,
                                  'session_id': session_id})
                # If they are logged in, create a second live vote
                if user_id:
                    create_live_vote({'suggestion': suggestion_key,
                                      'vote_type': show.current_vote_type,
                                      'player': player_key,
                                      'show': show.key,
                                      'interval': interval,
                                      'session_id': session_id})
                # Check if the suggestion has a user id attached to it
                if suggestion_key and suggestion_key.get().user_id:
                    # Get the suggestion's user id
                    suggestion_user_id = suggestion_key.get().user_id
                    # If the current user is logged in
                    if user_id:
                        # Give the suggestion user two points
                        points = 2
                    else:
                        points = 1
                    # Get all leaderboard entries for this user for this show
                    leaderboard_entries = fetch_leaderboard_entries(show=show.key,
                                                                    user_id=suggestion_user_id)
                    # IF there are duplicates
                    if len(leaderboard_entries) > 1:
                        # Delete the additional entry
                        leaderboard_entries[1].key.delete()
                        # Take the first of the leaderboard entry items
                        leaderboard_entry = leaderboard_entries[0]
                    # If there is just one
                    elif len(leaderboard_entries) == 1:
                        # Take the first of the leaderboard entry items
                        leaderboard_entry = leaderboard_entries[0]
                    # If there isn't an entry yet
                    else:
                        leaderboard_entry = None
                    # If a leaderboard entry exists for the suggestion user and show
                    if leaderboard_entry:
                        # Add the points to the suggestion user's leaderboard entry
                        leaderboard_entry.points += points
                        leaderboard_entry.put()
                    else:
                        # Create the suggestion user's leaderboard entry
                        create_leaderboard_entry({'show': show.key,
                                                  'show_date': show.created,
                                                  'user_id': suggestion_user_id,
                                                  'points': points})


def user_suggestion_amount(user_id, session_id, suggestions):
    amount = 0
    for suggestion in suggestions:
        # If the user id matches the suggestion's user id
        if suggestion.user_id and suggestion.user_id == user_id:
            amount += 1
        # If the session id matches the suggestion's session id
        elif session_id and suggestion.session_id == session_id:
            amount += 1
    return amount


class AddSuggestions(ViewBase):
    @redirect_locked
    def get(self, suggestion_pool_name=None):
        session_id = str(self.session.get('id', '0'))
        threshold_met = False
        if suggestion_pool_name:
            current_suggestion_pool = get_suggestion_pool(name=suggestion_pool_name)
        else:
            try:
                current_suggestion_pool = self.context['current_suggestion_pools'][0]
            except IndexError:
                current_suggestion_pool = None
        # Get all the suggestions from the current pool
        suggestions = get_suggestion_pool_page_suggestions(
                        getattr(self.current_show, 'key', None),
                        getattr(current_suggestion_pool, 'key', None))
        # We've reached the limit of suggestions for this suggestion type
        if len(suggestions) >= SHOW_SUGGESTION_LIMIT or \
            user_suggestion_amount(self.user_id, session_id, suggestions) >= USER_SUGGESTION_LIMIT:
            threshold_met = True
        context = {'current_suggestion_pool': current_suggestion_pool,
                   'suggestions': suggestions,
                   'threshold_met': threshold_met,
                   'session_id': session_id,
                   'item_count': len(suggestions)}
        self.response.out.write(template.render(self.path('add_suggestions.html'),
                                                self.add_context(context)))

    @redirect_locked
    def post(self, suggestion_pool_name):
        session_id = str(self.session.get('id', '0'))
        threshold_met = False
        current_suggestion_pool = get_suggestion_pool(name=suggestion_pool_name)
        context = pre_show_voting_post(getattr(self.current_show, 'key', None),
                                       current_suggestion_pool,
                                       self.request,
                                       session_id,
                                       self.user_id,
                                       self.context.get('is_admin', False))
        # We've reached the limit of suggestions for this suggestion type
        if len(context['suggestions']) >= SHOW_SUGGESTION_LIMIT or \
            user_suggestion_amount(self.user_id, session_id, context['suggestions']) >= USER_SUGGESTION_LIMIT:
            threshold_met = True
        context.update({'current_suggestion_pool': current_suggestion_pool,
                        'item_count': len(context['suggestions']),
                        'threshold_met': threshold_met})
        self.response.out.write(template.render(self.path('add_suggestions.html'),
                                                self.add_context(context)))


class Leaderboards(ViewBase):
    @redirect_locked
    def get(self, start_date=None, end_date=None):
        leaderboard_kwargs = {'start_date': start_date,
                              'end_date': end_date,
                              'unique_by_user': True}
        leaderboard_entries = fetch_leaderboard_entries(**leaderboard_kwargs)
        leaderboard_spans = fetch_leaderboard_spans()
        # Create an initial leaderboard span if one doesn't exist yet
        if not leaderboard_spans:
            create_leaderboard_span({'name': "Test",
                                     'start_date': datetime.date.today(),
                                     'end_date': datetime.date.today()})
        context = {'shows': fetch_shows(**{'order_by_created': True}),
                   'leaderboard_spans': leaderboard_spans,
                   'leaderboard_entries': leaderboard_entries}
        self.response.out.write(template.render(self.path('leaderboards.html'),
                                                self.add_context(context)))


def get_medals_exist(leaderboard_entries):
    for entry in leaderboard_entries:
        if len(entry.medals) > 0:
            return True
    return False


# Used to handle the show leaderboard url properly
class ShowLeaderboard(ViewBase):
    @redirect_locked
    def get(self, show_id):
        medals_exist = True
        show = get_show(key_id=show_id)
        leaderboard_entries = fetch_leaderboard_entries(show=show.key,
                                                        order_by_points=True,
                                                        test=self.request.get('test'))
        # If user is an admin
        if self.context.get('is_admin', False):
            medals_exist = get_medals_exist(leaderboard_entries)
        context = {'show_id': int(show_id),
                   'shows': fetch_shows(),
                   'leaderboard_entries': leaderboard_entries,
                   'medals_exist': medals_exist}
        self.response.out.write(template.render(self.path('leaderboards.html'),
                                                self.add_context(context)))
    
    @admin_required
    def post(self, show_id):
        show = get_show(key_id=show_id)
        if self.request.get('award_medals'):
            # Set the medals awarded to the users
            award_leaderboard_medals(show.key)
        leaderboard_entries = fetch_leaderboard_entries(show=show.key,
                                                        order_by_points=True)
        context = {'show_id': int(show_id),
                   'shows': fetch_shows(),
                   'leaderboard_entries': leaderboard_entries,
                   'medals_exist': get_medals_exist(leaderboard_entries)}
        self.response.out.write(template.render(self.path('leaderboards.html'),
                                                self.add_context(context)))


# Used to handle the user account
class UserAccount(ViewBase):
    @redirect_locked
    def get(self, user_id):
        user_profiles = fetch_user_profiles(user_id=user_id)
        # Set the user profile as the first user profile found
        try:
            user_profile = user_profiles[0]
        except IndexError:
            self.response.write('Oops! This user does not exist!')
            self.response.set_status(404)
            return
        # IF a duplicate user profile was created, delete it!!
        if len(user_profiles) > 1:
            user_profiles[1].key.delete()
        user_suggestions = fetch_suggestions(**{'user_id': user_id})
        show_entries = fetch_leaderboard_entries(user_id=user_id,
                                                 order_by_show_date=True)
        try:
            leaderboard_stats = fetch_leaderboard_entries(user_id=user_id,
                                                          unique_by_user=True)[0]
        except IndexError:
            leaderboard_stats = {'level': 1, 'points': 0, 'medals': [], 'wins': 0,
                                 'suggestions': 0}

        context = {'show_entries': show_entries,
                   'user_suggestions': user_suggestions,
                   'leaderboard_stats': leaderboard_stats,
                   'user_profile': user_profile,
                   'page_user_id': user_id}
        self.response.out.write(template.render(self.path('user_account.html'),
                                                self.add_context(context)))
    
    @redirect_locked
    def post(self, user_id):
        update = 'unchanged'
        user_profile = None
        change_username = self.request.get('change_username')
        if change_username:
            # Update the user profile with the new username
            user_profile = update_user_profile(self.user.user_id, change_username)
            # If the username was already taken
            if not user_profile:
                # Just get the original user profile
                user_profile = get_user_profile(user_id=user_id)
            else:
                update = 'changed'
        show_entries = fetch_leaderboard_entries(user_id=user_id,
                                                 order_by_show_date=True)
        try:
            leaderboard_stats = fetch_leaderboard_entries(user_id=user_id,
                                                          unique_by_user=True)[0]
        except IndexError:
            leaderboard_stats = {'level': 1, 'points': 0, 'medals': [], 'wins': 0,
                                 'suggestions': 0}
        context = {'show_entries': show_entries,
                   'leaderboard_stats': leaderboard_stats,
                   'user_profile': user_profile,
                   'page_user_id': user_id,
                   'update': update}
        self.response.out.write(template.render(self.path('user_account.html'),
                                                self.add_context(context)))


class MedalsPage(ViewBase):
    @redirect_locked
    def get(self):
        context = {'medals': fetch_medals()}
        self.response.out.write(template.render(self.path('medals.html'),
                                                self.add_context(context)))
