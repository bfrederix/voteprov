import datetime
import math
import random

from google.appengine.ext import ndb

from timezone import (get_mountain_time, back_to_tz, get_today_start,
                      get_tomorrow_start)

VOTE_AFTER_INTERVAL = 25
DISPLAY_VOTED = 10

VOTE_STYLE = ['all-players', 'player-pool', 'player-options', 'options']
OCCURS_TYPE = ['before', 'during']


def get_current_show():
	return Show.query(
			Show.scheduled >= get_today_start(),
			Show.scheduled < get_tomorrow_start()).order(-Show.scheduled).get()


class Player(ndb.Model):
    name = ndb.StringProperty(required=True)
    photo_filename = ndb.StringProperty(required=True, indexed=False)
    date_added = ndb.DateTimeProperty()
    
    @property
    def img_path(self):
        return "/static/img/players/%s" % self.photo_filename
    
    def get_live_action_vote_exists(self, show, interval, session_id):
        return bool(LiveActionVote.query(
                    LiveActionVote.interval == int(interval),
                    LiveActionVote.show == show,
                    LiveActionVote.session_id == str(session_id)).get())
    
    def get_role_vote(self, show, role):
        return RoleVote.query(
                    RoleVote.player == self.key,
                    RoleVote.show == show.key,
                    RoleVote.role == role).get()

class SuggestionPool(ndb.Model):
    name = ndb.StringProperty(required=True)
    display_name = ndb.StringProperty(required=True, indexed=False)
    
    created = ndb.DateProperty(required=True)
    
    def put(self, *args, **kwargs):
        if not self.created:
            self.created = get_mountain_time()
        return super(SuggestionPool, self).put(*args, **kwargs)


class Suggestion(ndb.Model):
    show = ndb.KeyProperty(kind=Show)
    suggestion_pool = ndb.KeyProperty(kind=SuggestionPool)
    used = ndb.BooleanProperty(default=False)
    voted_on = ndb.BooleanProperty(default=False)
    archived = ndb.BooleanProperty(default=False)
    value = ndb.StringProperty(required=True, indexed=False)
    # Pre-show upvotes
    preshow_value = ndb.IntegerProperty(default=0)
    # Aggregate of current live vote value, gets reset after each vote ends
    live_value = ndb.IntegerProperty(default=0)
    session_id = ndb.StringProperty(required=True)
    user = ndb.UserProperty(default=None)
    
    created = ndb.DateProperty()
    
    def clear_live_votes(self):
        """Delete all the live votes for this suggestion"""
        self.live_value = 0
        self.put()
    
    def get_live_vote_exists(self, show, session_id):
        """Determine if a live vote exists for this suggestion by this session"""
        return bool(LiveVote.query(
                    LiveVote.show == show,
                    LiveVote.session_id == str(session_id)).get())
    
    @property
    def get_voted_sessions(self):
        """Determine which sessions have voted for this suggestion pre-show"""
        psv = PreshowVote.query(PreshowVote.suggestion == self.key).fetch()
        return [x.session_id for x in psv]
        

    def put(self, *args, **kwargs):
        if not self.created:
            self.created = get_mountain_time()
        return super(Suggestion, self).put(*args, **kwargs)


class PreshowVote(ndb.Model):
    show = ndb.KeyProperty(kind=Show)
    suggestion = ndb.KeyProperty(kind=Suggestion, required=True)
    session_id = ndb.StringProperty(required=True)
    user = ndb.UserProperty(default=None)


class LiveVote(ndb.Model):
    show = ndb.KeyProperty(kind=Show, required=True)
    vote_type = ndb.KeyProperty(kind=VoteType, required=True)
    player = ndb.KeyProperty(kind=Player)
    suggestion = ndb.KeyProperty(kind=Suggestion)
    interval = ndb.IntegerProperty()
    session_id = ndb.StringProperty(required=True)
    user = ndb.UserProperty(default=None)
    
    def put(self, *args, **kwargs):
        """Increment the Suggestion's live value"""
        if self.suggestion:
            suggestion_entity = self.suggestion.get()
            suggestion_entity.live_value += 1
            suggestion_entity.voted_on = True
            suggestion_entity.put()
        return super(LiveVote, self).put(*args, **kwargs)


def vote_type_name_validator(prop, value):
    """Make sure the name field is unique"""
    if VoteType.query(VoteType.name == value).count() > 0:
        raise ValueError("Vote Type name already exists!")
    return None


class VoteType(ndb.Model):
    name = ndb.StringProperty(required=True, validator=vote_type_name_validator)
    display_name = ndb.StringProperty(required=True)
    suggestion_pool = ndb.KeyProperty(kind=SuggestionPool)
    has_intervals = ndb.BooleanProperty(required=True, default=False)
    current_interval = ndb.IntegerProperty()
    intervals = ndb.IntegerProperty(repeated=True)
    style = ndb.StringProperty(choices=VOTE_STYLE)
    occurs = ndb.StringProperty(choices=OCCURS_TYPE)
    ordering = ndb.IntegerProperty(default=0)
    options = ndb.IntegerProperty(default=3, indexed=False)
    randomize_amount = ndb.IntegerProperty(default=6, indexed=False)

    def get_next_interval(self, interval):
        # If given an interval
        if interval != None:
            # Loop through the intervals in order
            for i in range(0, len(self.intervals)):
                if interval == self.intervals[i]:
                    # Get the minutes elapsed between the next interval in the loop
                    # and the current interval in the loop
                    try:
                        return self.intervals[i+1]
                    except IndexError:
                        return None
        # Otherwise, assume first interval
        else:
            try:
                return self.intervals[0]
            except IndexError:
                return None
        return None
    
    def get_interval_gap(self, interval):
        next_interval = self.get_next_interval(interval)
        # If there is a next interval
        if interval != None and next_interval != None:
            return int(next_interval) - int(interval)
        return None
    
    @property
    def remaining_intervals(self):
        show = get_current_show()
        # If there's a show today
        if show:
            if self.current_interval == None:
                return len(self.intervals)
            try:
                interval_index = self.intervals.index(self.current_interval)
            except ValueError:
                return 0
            return len(self.intervals[interval_index:]) - 1
        return 0
    
    def get_randomized_unused_suggestions(self, show, interval=None):
        # Get the stored interval options
        interval_vote_options = VoteOptions.query(
                                    VoteOptions.vote_type == self.key,
                                    VoteOptions.show == show,
                                    VoteOptions.interval == interval).get()
        # If the interval options haven't been generated
        if not interval_vote_options:                    
            # Return un-used suggestion keys, sorted by vote
            unused_suggestion_keys = Suggestion.query(
                                         Suggestion.suggestion_pool == self.suggestion_pool,
                                         Suggestion.used == False,
                                             ).order(-Suggestion.vote_value,
                                                     Suggestion.created
                                                        ).fetch(self.randomize_amount,
                                                                keys_only=True)
            # Get a randomized sample of the top "option" amount of suggestion keys
            random_sample_keys = list(
                                     random.sample(
                                        set(unused_suggestion_keys),
                                        min(self.options, len(unused_suggestion_keys))))
            # Convert the keys into actual entities
            unused_suggestions = ndb.get_multi(random_sample_keys)
            # Create the corresponding vote options for that interval (or none interval)
            VoteOptions(vote_type=self.key,
                        show=show,
                        interval=interval,
                        option_list=random_sample_keys).put()
        else:
            # Convert the option list keys into actual entities
            unused_suggestions = ndb.get_multi(interval_vote_options.option_list)
        return unused_suggestions
    
    def get_live_vote_count(show, player=None, suggestion=None, interval=None):
        return LiveVote.query(LiveVote.show == show,
                              LiveVote.vote_type == self.key,
                              LiveVote.player == player,
                              LiveVote.suggestion == suggestion,
                              LiveVote.interval == interval).count()


class Show(ndb.Model):
    # Assigned to show on creation
    vote_length = ndb.IntegerProperty(default=25, indexed=False)
    result_length = ndb.IntegerProperty(default=10, indexed=False)
    vote_options = ndb.IntegerProperty(default=5, indexed=False)
    timezone = ndb.StringProperty(default='America/Denver', indexed=False)

    theme = ndb.KeyProperty(kind=Suggestion, indexed=False)
    vote_types = ndb.KeyProperty(kind=VoteType, repeated=True, indexed=False)
    # All players in the show
    players = ndb.KeyProperty(kind=Player, repeated=True, indexed=False)
    # Finite amount of players to select from during the show
    player_pool = ndb.KeyProperty(kind=Player, repeated=True, indexed=False)
    created = ndb.DateTimeProperty(required=True)
    
    # Changes during live show
    current_vote_type = ndb.KeyProperty(kind=VoteType, indexed=False)
    current_vote_init = ndb.DateTimeProperty(indexed=False)
    recap_type = ndb.KeyProperty(kind=VoteType, indexed=False)
    recap_init = ndb.DateTimeProperty(indexed=False)
    locked = ndb.BooleanProperty(default=False, indexed=False)
    showing_leaderboard = ndb.BooleanProperty(default=False, indexed=False)
    voted_items = ndb.KeyProperty(kind=VotedItem, repeated=True, indexed=False)
    
    def get_player_by_interval(self, interval, vote_type):
        return ShowInterval.query(ShowInterval.show == self.key,
                                  ShowInterval.interval == interval,
                                  ShowInterval.vote_type == vote_type).get()

    @property
    def is_today(self):
        return self.created.date() == get_mountain_time().date()    
    
    @property
    def current_vote_state(self):
        state_dict = {'state': 'default', 'display': 'default', 'used_types': []}
        vote_type = self.current_vote_type.get()
        now = get_mountain_time()
        # Get timezone for comparisons
        now_tz = back_to_tz(now)
        # Go through all the vote vote types to see if they've started
        for vote_type in self.vote_types:
            
            time_property = "%s_vote_init" % vote_type
            init_time = getattr(self, time_property, None)
        # If any vote has started
        if self.current_vote_init:
            # Get the timezone datetime of the start of the vote type
            init_time_tz = back_to_tz(self.current_vote_init)
            # Get the end of the voting period for the type
            vote_end = init_time_tz + datetime.timedelta(seconds=self.vote_length)
            # Get the end of the overall display of the type
            display_end = vote_end + datetime.timedelta(seconds=self.result_length)
            # If we're in the voting period of this type
            if now_tz >= init_time_tz and now_tz <= vote_end:
                state_dict.update(
                       {'state': vote_type.name,
                        'display': 'voting',
                        # Set the end of the voting period
                        'hour': vote_end.hour,
                        'minute': vote_end.minute,
                        'second': vote_end.second,
                        'voting_length': (vote_end - now_tz).seconds})
            elif now_tz >= vote_end and now_tz <= display_end:
                state_dict.update({'state': vote_type.name,
                                   'display': 'result',
                                   'hour': vote_end.hour,
                                   'minute': vote_end.minute,
                                   'second': vote_end.second})
        # If any recap exists
        if self.recap_init:
            recap_type_entity = self.recap_type.get()
            recap_start_tz = back_to_tz(self.recap_init)
            # Get the end of the recap display
            display_end = recap_start_tz + datetime.timedelta(seconds=self.result_length)
            # If we're in the display period of this recap type
            if now_tz >= recap_start_tz and now_tz <= display_end:
                state_dict.update({'state': recap_type_entity.name,
                                   'display': 'result',
                                   'hour': display_end.hour,
                                   'minute': display_end.minute,
                                   'second': display_end.second})
        
        # Get the list of already voted items
        for vt in self.voted_items:
            voted_item_entity = vt.get()
            vote_type = voted_item_entity.vote_type.get()
            # If the vote type has been used (and is not an interval)
            if not vote_type.has_intervals:
                state_dict['used_types'].append(vote_type.name)
                    
        return state_dict

    def current_vote_options(self, voting_only=False):
        vote_type = self.current_vote_type.get()
        current_interval = vote_type.current_interval
        vote_options = self.current_vote_state.copy()
        state = vote_options.get('state', 'default')
        display = vote_options.get('display')
        if display == 'voting':
            vote_options['options'] = []
            if vote_type.style == 'all-players':
                # Loop through all the players in the show
                for player in self.players:
                    count = vote_type.get_live_vote_count(self.key,
                                                          player=player,
                                                          interval=current_interval)
                    player_dict = {'photo_filename': player.photo_filename,
                                   'id': player.key.id(),
                                   'count': count}
                    vote_options['options'].append(player_dict)
            elif vote_type.style == 'player-pool':
                # Loop through all the players in the show's player pool
                for player in self.player_pool:
                    count = vote_type.get_live_vote_count(self.key,
                                                          player=player,
                                                          interval=current_interval)
                    player_dict = {'photo_filename': player.photo_filename,
                                   'id': player.key.id(),
                                   'count': count}
                    vote_options['options'].append(player_dict)
            elif vote_type.style == 'player-options':
                # Get the player
                player = self.get_player_by_interval(interval, self.current_vote_type)
                vote_options.update({'interval': current_interval,
                                     'player_id': player.id(),
                                     'player_photo': player.get().photo_filename})
                unused_suggestions = vote_type.get_randomized_unused_suggestions(self.key,
                                                                                 interval=current_interval)
                for unused_suggestion in unused_suggestions:
                    count = vote_type.get_live_vote_count(self.key,
                                                          player=player,
                                                          suggestion=unused_suggestion,
                                                          interval=current_interval)
                    vote_options['options'].append({'name': unused_suggestion.value,
                                                    'id': unused_suggestion.key.id(),
                                                    'count': count})
            elif vote_type.style == 'options':
                unused_suggestions = vote_type.get_randomized_unused_suggestions(self.key,
                                                                                 interval=current_interval)
                for unused_suggestion in unused_suggestions:
                    count = vote_type.get_live_vote_count(self.key,
                                                          suggestion=unused_suggestion,
                                                          interval=current_interval)
                    vote_options['options'].append({'name': unused_suggestion.value,
                                                    'id': unused_suggestion.key.id(),
                                                    'count': count})
            # If there is a 1 minute interval gap between this interval and the next
            if vote_type.get_interval_gap(current_interval) == 1:
                vote_options['speedup'] = True
        elif display == 'result' and not voting_only:
            if vote_type.style == 'all-players':
                role_player = getattr(show, state, None)
                # Set the role if it isn't already set
                if not role_player:
                    role_votes = RoleVote.query(RoleVote.role == state,
                                                RoleVote.show == show.key,
                                     ).order(-RoleVote.live_vote_value).fetch()
                    # Grab the first player
                    for rv in role_votes:
                        # Make sure they aren't already the hero/villain/lover
                        if rv.player != show.hero and rv.player != show.villain \
                            and rv.player != show.lover:
                            # We've found the voted role, break out of the loop
                            voted_role = rv
                            break
                    # Setting role for the show
                    setattr(show, state, voted_role.player)
                    show.put()
                    # Getting the player selected for the role
                    role_player = voted_role.player
                else:
                    voted_role = RoleVote.query(RoleVote.role == state,
                                                RoleVote.show == show.key,
                                                RoleVote.player == role_player).get()
                vote_options['voted'] = state.title()
                vote_options['photo_filename'] = role_player.get().photo_filename
                vote_options['count'] = voted_role.live_vote_value
            elif vote_type.style == 'player-pool':
            elif vote_type.style == 'player-options':
            elif vote_type.style == 'options':
        
        
        
        # If an test has been triggered
        if state == 'test':
            # If we're in the voting phase for the test
            if display == 'voting':
                vts = VotingTest.query().fetch(ITEM_AMOUNT)
                vote_options['options'] = []
                for vt in vts:
                    vote_options['options'].append({'name': vt.name,
                                                    'id': vt.key.id(),
                                                    'count': vt.live_vote_value})
            # If we are showing the results of the vote
            elif display == 'result' and not voting_only:
                # Set the most voted test if it isn't already set
                if not show.test:
                    voted_test = VotingTest.query().order(
                                             -VotingTest.live_vote_value).get()
                    show.test = voted_test.key
                    show.put()
                    voted_test.put()
                vote_options['voted'] = show.test.get().name
                vote_options['count'] = show.test.get().live_vote_value
        # If an incident has been triggered
        elif state == 'incident':
            # If we're in the voting phase for an incident
            if display == 'voting':
                actions = Action.query(Action.used == False,
                          ).order(-Action.vote_value,
                                  Action.created).fetch(INCIDENT_AMOUNT)
                vote_options['options'] = []
                for action in actions:
                    vote_options['options'].append({'name': action.description,
                                                    'id': action.key.id(),
                                                    'count': action.live_vote_value})
            # If we are showing the results of the vote
            elif display == 'result' and not voting_only:
                # Set the most voted incident if it isn't already set
                if not show.incident:
                    voted_incident = Action.query(Action.used == False,
                                   ).order(-Action.live_vote_value,
                                           -Action.vote_value,
                                           Action.created).get()
                    show.incident = voted_incident.key
                    show.put()
                    # Set the Action as used
                    voted_incident.used = True
                    voted_incident.put()
                vote_options['voted'] = show.incident.get().description
                vote_options['count'] = show.incident.get().live_vote_value
        # If a role vote has been triggered
        elif state in ROLE_TYPES:
            vote_options['role'] = True
            # If we're in the voting phase for the role
            if display == 'voting':
                vote_options['options'] = []
                # Loop through all the players in the show
                for player in show.players:
                    # Make sure the user isn't already the hero/lover/villain
                    if player.key != show.hero and player.key != show.villain \
                        and player.key != show.lover:
                        change_vote = get_or_create_role_vote(show, player, state)
                        player_dict = {'photo_filename': player.photo_filename,
                                       'id': player.key.id(),
                                       'count': change_vote.live_vote_value}
                        vote_options['options'].append(player_dict)
            # If we are showing the results of the vote
            elif display == 'result' and not voting_only:
                role_player = getattr(show, state, None)
                # Set the role if it isn't already set
                if not role_player:
                    role_votes = RoleVote.query(RoleVote.role == state,
                                                RoleVote.show == show.key,
                                     ).order(-RoleVote.live_vote_value).fetch()
                    # Grab the first player
                    for rv in role_votes:
                        # Make sure they aren't already the hero/villain/lover
                        if rv.player != show.hero and rv.player != show.villain \
                            and rv.player != show.lover:
                            # We've found the voted role, break out of the loop
                            voted_role = rv
                            break
                    # Setting role for the show
                    setattr(show, state, voted_role.player)
                    show.put()
                    # Getting the player selected for the role
                    role_player = voted_role.player
                else:
                    voted_role = RoleVote.query(RoleVote.role == state,
                                                RoleVote.show == show.key,
                                                RoleVote.player == role_player).get()
                vote_options['voted'] = state.title()
                vote_options['photo_filename'] = role_player.get().photo_filename
                vote_options['count'] = voted_role.live_vote_value
        # If an interval has been triggered
        elif state == 'interval':
            interval = self.current_interval
            # Get the player
            player = self.get_player_by_interval(interval)
            # Get the player action for this interval
            player_action = self.get_player_action_by_interval(interval)
            # If there is a 1 minute interval gap between this interval and the next
            if pool_type.get_interval_gap(interval) == 1:
                vote_options['speedup'] = True
            vote_options.update({'interval': interval,
                                 'player_id': player.id(),
                                 'player_photo': player.get().photo_filename})
            # If we're in the voting phase for the interval
            if display == 'voting':
                unused_actions = self.get_randomized_unused_actions(show, interval)
                vote_options['options'] = []
                for i in range(0, ACTION_OPTIONS):
                    try:
                        vote_options['options'].append({
                                            'name': unused_actions[i].description,
                                            'id': unused_actions[i].key.id(),
                                            'count': unused_actions[i].live_vote_value})
                    except IndexError:
                        pass
            # If we are showing the results of the vote
            elif display == 'result' and not voting_only:
                # If an action wasn't already chosen for this interval
                if not player_action.action:
                    voted_action = None
                    # Get the actions that were voted on this interval
                    unused_actions = self.get_randomized_unused_actions(show, interval)
                    # Take the action with the highest live_vote_value
                    # Or just default to the first action
                    for action in unused_actions:
                        if voted_action == None:
                            voted_action = action
                        elif action.live_vote_value > voted_action.live_vote_value:
                            voted_action = action
                    # If a voted action exists
                    if voted_action:
                        # Set the player action
                        player_action.action = voted_action.key
                        player_action.put()
                        # Set the action as used
                        voted_action.used = True
                        voted_action.put()
                        vote_options.update({'voted': voted_action.description,
                                             'count': voted_action.live_vote_value})
                else:
                    vote_options.update({'voted': player_action.action.get().description,
                                         'count': player_action.action.get().live_vote_value})
        return vote_options
    
    def put(self, *args, **kwargs):
        # If created wasn't specified yet
        if no self.created:
            self.created = get_mountain_time()
        # If a theme was specified, set the theme as used
        if self.theme:
            theme_entity = self.theme.get()
            theme_entity.used = True
            theme_entity.put()
        return super(Show, self).put(*args, **kwargs)


class ShowInterval(ndb.Model):
    show = ndb.KeyProperty(kind=Show, required=True)
    vote_type = ndb.KeyProperty(kind=VoteType, required=True)
    player = ndb.KeyProperty(kind=Player, required=True)
    interval = ndb.IntegerProperty(required=True)


class VoteOptions(ndb.Model):
    show = ndb.KeyProperty(kind=Show, required=True)
    vote_type = ndb.KeyProperty(kind=VoteType, required=True)
    interval = ndb.IntegerProperty()
    option_list = ndb.KeyProperty(kind=Suggestion, repeated=True)


class VotedItem(ndb.Model):
    vote_type = ndb.KeyProperty(kind=VoteType, required=True)
    suggestion = ndb.KeyProperty(kind=Suggestion, required=True)
    interval = ndb.IntegerProperty()
