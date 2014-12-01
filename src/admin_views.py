import datetime
import json
import random
import csv
import StringIO

from google.appengine.ext.webapp import template

from views_base import ViewBase, get_or_default, admin_required

from service import (get_suggestion, get_player, get_show,
                     get_vote_type, get_voted_item, get_medal, get_user_profile,
                     get_suggestion_pool, get_email_opt_out, fetch_suggestions,
                     fetch_players, fetch_preshow_votes, fetch_vote_options,
                     fetch_shows, fetch_live_votes, fetch_suggestion_pools,
                     fetch_vote_types, fetch_voted_items, fetch_show_intervals,
                     fetch_leaderboard_entries, fetch_medals, create_medal,
                     create_show, create_show_interval, create_suggestion_pool,
                     create_vote_type, create_player, create_email_opt_out,
                     get_unused_suggestions, VOTE_STYLE, OCCURS_TYPE,
                     test_awarding)
from timezone import get_mountain_time, back_to_tz


class ShowControl(ViewBase):
    @admin_required
    def get(self, show_id):
        show = get_show(key_id=show_id)
        context = {'show': show,
                   'now_tz': back_to_tz(get_mountain_time())}
        show = get_show(key_id=show_id)
        context = {'show': show,
                   'now_tz': back_to_tz(get_mountain_time())}
        self.response.out.write(template.render(self.path('show_control.html'),
                                                self.add_context(context)))

    @admin_required
    def post(self, show_id):
        show = get_show(key_id=show_id)
        # Admin is starting the show
        if self.request.get('vote_start') and self.context.get('is_admin', False):
            vote_type = get_vote_type(name=self.request.get('vote_start'))
            # Set the current vote type for the show
            show.current_vote_type = vote_type.key
            # Set the start time of the current vote and show vote
            show.current_vote_init = get_mountain_time()
            vote_type.current_init = get_mountain_time()
            # If this suggestion vote has intervals
            if vote_type.has_intervals:
                # Get the next interval
                next_interval = vote_type.get_next_interval(show.key)
                # If there is a next interval
                if next_interval != None:
                    # Set the current interval to the next interval
                    vote_type.current_interval = next_interval
            # If it's a test vote, delete all the vote options
            if vote_type.name == 'test':
                # Delete the vote options
                fetch_vote_options(vote_type=vote_type.key,
                                   show=show.key,
                                   delete=True)
                # Delete the current voted item
                get_voted_item(vote_type=vote_type.key,
                               show=show.key,
                               delete=True)
            # Save the show and vote type's new current state
            vote_type.put()
            show.put()
        # Admin is starting a recap
        elif self.request.get('recap') and self.context.get('is_admin', False):
            show.recap_init = get_mountain_time()
            show.recap_type = getattr(get_vote_type(name=self.request.get('recap')),
                                      'key',
                                      None)
            show.put()
        # Admin is locking/unlocking the voting
        elif self.request.get('lock_vote') and self.context.get('is_admin', False):
            # Toggle the lock/unlock
            show.locked = not show.locked
            show.put()
        context = {'show': show,
                   'now_tz': back_to_tz(get_mountain_time()),
                   'host_url': self.request.host_url}
        self.response.out.write(template.render(self.path('show_control.html'),
                                                self.add_context(context)))


class ShowDisplay(ViewBase):
    @admin_required
    def get(self, show_id):
        show = get_show(key_id=show_id)
        context = {'show': show,
                   'now_tz': back_to_tz(get_mountain_time()),
                   'host_url': self.request.host_url}
        self.response.out.write(template.render(self.path('show_display.html'),
                                                self.add_context(context)))


def get_rand_player_list(players, star_players=[]):
    """Create a random list of players,
       putting star players at the front of the list for popping
    """
    # Make a copy of the list of players and randomize it
    rand_players = list(players)
    random.shuffle(rand_players, random.random)
    if star_players:
        for star in star_players:
            rand_players.append(star)
    return rand_players


class CreateShow(ViewBase):
    @admin_required
    def get(self):
        context = {'vote_types': fetch_vote_types(order_by_ordering=True),
                   'players': fetch_players()}
        self.response.out.write(template.render(self.path('create_show.html'),
                                                self.add_context(context)))

    @admin_required
    def post(self):
        player_list = self.request.get_all('player_list')
        vote_type_list = self.request.get_all('vote_type_list')
        context = {'vote_types': fetch_vote_types(order_by_ordering=True),
                   'players': fetch_players()}
        if player_list and vote_type_list:
            players = []
            star_players = []
            # Get the players for the show
            for player in player_list:
                player_key = get_player(key_id=player, key_only=True)
                # If they're a star player, add them to the star list
                if player_key.get().star:
                    star_players.append(player_key)
                else:
                    players.append(player_key)
            combined_players = players + star_players
            show = create_show({'players': combined_players,
                                'player_pool': combined_players}).get()
            # Get and sort the vote types by ordering
            vts = [get_vote_type(key_id=x) for x in vote_type_list]
            vote_types = sorted(vts, key=lambda x: x.ordering)
            # Add the vote types to the show
            for vote_type in vote_types:
                # Reset the vote type's current interval
                vote_type.current_interval = None
                vote_type.put()
                # Add the vote type to the show
                show.vote_types.append(vote_type.key)
                # Get the maximum voting options from the vote type
                # And store it if it's greater than the show's current vote options
                show.vote_options = max(show.vote_options, vote_type.options)
                # If the vote type has intervals
                if vote_type.has_intervals:                
                    # If this suggestion vote has players attached
                    if vote_type.interval_uses_players:
                        # Make a copy of the list of players and randomize it
                        rand_players = get_rand_player_list(players, star_players=star_players)
                        # Add the intervals to the show
                        for interval in vote_type.intervals:
                            # If random players list gets empty, refill it with more players
                            if len(rand_players) == 0:
                                rand_players = get_rand_player_list(players, star_players=star_players)
                            # Pop a random player off the list and create a ShowInterval
                            create_show_interval({'show': show.key,
                                                  'player': rand_players.pop(),
                                                  'interval': interval,
                                                  'vote_type': vote_type.key})
                    else:
                        # Add the suggestion intervals to the show
                        for interval in vote_type.intervals:
                            # Create a ShowInterval
                            create_show_interval({'show': show.key,
                                                  'interval': interval,
                                                  'vote_type': vote_type.key})
            # Save changes to the show
            show.put()
            context['created'] = True
        self.response.out.write(template.render(self.path('create_show.html'),
                                                self.add_context(context)))


class VoteTypes(ViewBase):
    @admin_required
    def get(self):
        context = context = {'vote_types': fetch_vote_types(),
                             'suggestion_pools': fetch_suggestion_pools(),
                             'vote_styles': VOTE_STYLE,
                             'occurs_types': OCCURS_TYPE}
        self.response.out.write(template.render(self.path('vote_types.html'),
                                                self.add_context(context)))

    @admin_required
    def post(self):
        action = None
        new_vote_type = None
        vote_type_ids = self.request.get_all('vote_type_ids')
        # Delete selected vote types
        if vote_type_ids:
            for vote_type_id in vote_type_ids:
                vote_type_key = get_vote_type(key_id=vote_type_id, key_only=True)
                vote_type_key.delete()
            action = 'deleted'
        # Create Vote Type
        elif self.request.get('name'):
            suggestion_pool_id = self.request.get('suggestion_pool_id')
            # If the vote type uses a suggestion pool
            if suggestion_pool_id:
                suggestion_pool_key = get_suggestion_pool(key_id=suggestion_pool_id,
                                                          key_only=True)
            # Otherwise, don't use a suggestion pool
            else:
                suggestion_pool_key = None
            intervals_string = self.request.get('interval_list')
            # Parse the intervals, if there are any
            if intervals_string:
                # Get the integer list of interval times
                try:
                    intervals = [int(x.strip()) for x in intervals_string.split(',')]
                except ValueError:
                    raise ValueError("Invalid interval list '%s'. Must be comma separated.")
            else:
                intervals = []
            # Create the vote type
            new_vote_type = create_vote_type({
                              'name': self.request.get('name'),
                              'display_name': self.request.get('display_name'),
                              'suggestion_pool': suggestion_pool_key,
                              'preshow_voted': bool(self.request.get('preshow_voted', False)),
                              'has_intervals': bool(self.request.get('has_intervals', False)),
                              'interval_uses_players': bool(self.request.get('interval_uses_players', False)),
                              'style': self.request.get('style'),
                              'occurs': self.request.get('occurs'),
                              'ordering': int(self.request.get('ordering', 10)),
                              'options': int(get_or_default(self.request.get('options'), 3)),
                              'randomize_amount': int(get_or_default(self.request.get('randomize_amount'), 6)),
                              'button_color': self.request.get('button_color', '#003D7A'),
                              'intervals': intervals})
            action = 'created'
        vote_types = fetch_vote_types()
        # Add the latest created vote type
        if new_vote_type:
            vote_types.append(new_vote_type.get())
        context = context = {'vote_types': vote_types,
                             'suggestion_pools': fetch_suggestion_pools(),
                             'vote_styles': VOTE_STYLE,
                             'occurs_types': OCCURS_TYPE,
                             'action': action}
        self.response.out.write(template.render(self.path('vote_types.html'),
                                                self.add_context(context)))


class SuggestionPools(ViewBase):
    @admin_required
    def get(self):
        context = {'suggestion_pools': fetch_suggestion_pools()}
        self.response.out.write(template.render(self.path('suggestion_pools.html'),
                                                self.add_context(context)))

    @admin_required
    def post(self):
        action = None
        suggestion_pool_ids = self.request.get('suggestion_pool_ids')
        # Delete selected suggestion pools
        if suggestion_pool_ids:
            for suggestion_pool_id in suggestion_pool_ids:
                suggestion_pool_key = get_suggestion_pool(key_id=suggestion_pool_id,
                                                          key_only=True)
                suggestion_pool_key.delete()
            action = 'deleted'
        # Create Suggestion pool
        elif self.request.get('name'):
            create_suggestion_pool({'name': self.request.get('name'),
                                    'display_name': self.request.get('display_name'),
                                    'description': self.request.get('description')})
            action = 'created'
        context = {'suggestion_pools': fetch_suggestion_pools(),
                   'action': action}
        self.response.out.write(template.render(self.path('suggestion_pools.html'),
                                                self.add_context(context)))


class CreateMedals(ViewBase):
    @admin_required
    def get(self):
        context = {'medals': fetch_medals()}
        self.response.out.write(template.render(self.path('create_medals.html'),
                                                self.add_context(context)))

    @admin_required
    def post(self):
        action = None
        medal_ids = self.request.get('medal_ids')
        # Delete selected medals
        if medal_ids:
            for medal_id in medal_ids:
                medal_key = get_medal(key_id=medal_id, key_only=True)
                medal_key.delete()
            action = 'deleted'
        # Create Medal
        elif self.request.get('name'):
            create_medal({'name': self.request.get('name'),
                          'display_name': self.request.get('display_name'),
                          'description': self.request.get('description'),
                          'image_filename': self.request.get('image_filename'),
                          'icon_filename': self.request.get('icon_filename')})
            action = 'created'
        context = {'medals': fetch_medals(),
                   'action': action}
        self.response.out.write(template.render(self.path('create_medals.html'),
                                                self.add_context(context)))


class DeleteTools(ViewBase):
    @admin_required
    def get(self):
        context = {'shows': fetch_shows(**{'archived': False}),
                   'suggestion_pools': get_unused_suggestions(getattr(self.current_show, 'key', None))}
        self.response.out.write(template.render(self.path('delete_tools.html'),
                                                self.add_context(context)))

    @admin_required
    def post(self):
        deleted = None
        unused_deleted = False
        show_list = self.request.get_all('show_list')
        suggestion_list = self.request.get_all('suggestion_list')
        delete_unused = self.request.get_all('delete_unused')
        # If suggestion(s) were deleted (archived)
        if suggestion_list:
            for suggestion in suggestion_list:
                suggestion_entity = get_suggestion(key_id=suggestion)
                # Get all the related preshow votes and delete them
                preshow_votes = fetch_preshow_votes(suggestion=suggestion_entity.key)
                for pv in preshow_votes:
                    pv.key.delete()
                suggestion_entity.key.delete()
            deleted = 'Suggestion(s)'
        # If show(s) were deleted
        if show_list:
            for show in show_list:
                show_key = get_show(key_id=show, key_only=True)
                # Delete the Vote Options attached to the show
                vote_options = fetch_vote_options(show=show_key)
                for vote_option in vote_options:
                    vote_option.key.delete()
                # Delete the Suggestions used in the show
                suggestions = fetch_suggestions(show=show_key)
                for suggestion in suggestions:
                    suggestion.key.delete()
                # Delete the Preshow Votes used in the show
                preshow_votes = fetch_preshow_votes(show=show_key)
                for preshow_vote in preshow_votes:
                    preshow_vote.key.delete()
                # Delete the Live Votes used in the show
                live_votes = fetch_live_votes(show=show_key)
                for live_vote in live_votes:
                    live_vote.key.delete()
                # Delete the Voted Items used in the show
                voted_items = fetch_voted_items(show=show_key)
                for voted_item in voted_items:
                    voted_item.key.delete()
                # Delete the Show Player Interval used in the show
                show_intervals = fetch_show_intervals(show=show_key)
                for show_interval in show_intervals:
                    show_interval.key.delete()
                # Delete the leaderboard entries for the show
                leaderboard_entries = fetch_leaderboard_entries(show=show_key)
                for leaderboard_entry in leaderboard_entries:
                    leaderboard_entry.key.delete()
                show_key.delete()
                deleted = 'Show(s)'
        # Delete ALL un-used things
        if delete_unused:
            # Fetch all the suggestions that weren't voted on or used
            suggestions = fetch_suggestions(used=False,
                                            voted_on=False)
            for suggestion in suggestions:
                # Delete the Preshow Votes used in the show
                preshow_votes = fetch_preshow_votes(suggestion=suggestion.key)
                for preshow_vote in preshow_votes:
                    preshow_votes.key.delete()
                # Delete the Live Votes used in the show
                live_votes = fetch_live_votes(suggestion=suggestion.key)
                for live_vote in live_votes:
                    live_vote.key.delete()
                suggestion.key.delete()
            deleted = 'All Un-used Actions'
        context = {'deleted': deleted,
                   'unused_deleted': unused_deleted,
                   'shows': fetch_shows(**{'archived': False}),
                   'suggestion_pools': get_unused_suggestions(getattr(self.current_show, 'key', None))}
        self.response.out.write(template.render(self.path('delete_tools.html'),
                                                self.add_context(context)))


class AddPlayers(ViewBase):
    @admin_required
    def get(self):
        self.response.out.write(template.render(self.path('add_players.html'),
                                                self.add_context()))

    @admin_required
    def post(self):
        created = False
        player_name = self.request.get('player_name')
        photo_filename = self.request.get('photo_filename')
        star = bool(self.request.get('star', False))
        if player_name and photo_filename:
            create_player({'name': player_name,
                           'photo_filename': photo_filename,
                           'star': star,
                           'date_added': get_mountain_time()})
            created = True
        context = {'created': created}
        self.response.out.write(template.render(self.path('add_players.html'),
                                                self.add_context(context)))


class ExportEmails(ViewBase):
    @admin_required
    def get(self):
        context = {'shows': fetch_shows()}
        self.response.out.write(template.render(self.path('export_emails.html'),
                                                self.add_context(context)))
    
    @admin_required
    def post(self):
        # Initialize opt out if necessary
        if not get_email_opt_out(email='tester@example.com'):
            create_email_opt_out({'email': 'tester@example.com'})
        if self.request.get('show_id'):
            # Get the suggestions for the give show
            show = get_show(key_id=self.request.get('show_id'))
            suggestions = fetch_suggestions(show=show.key)
            filehandle = StringIO.StringIO()
            writer = csv.writer(filehandle,
                                delimiter=',',
                                quotechar='"',
                                quoting=csv.QUOTE_NONNUMERIC)
            user_dict = {}
            for suggestion in suggestions:
                # Get the user that submitted the suggestion
                user_profile = get_user_profile(user_id=suggestion.user_id)
                # Make sure there is a user profile attached
                if user_profile and suggestion.user_id:
                    email = user_profile.email
                    # If an email is attached, and the user has not opted out of emails
                    if email and not get_email_opt_out(email=email):
                        user_dict.setdefault(email, [suggestion.user_id])
                        user_dict[email].append(suggestion.value)
            # Write the csv rows
            for user_email, suggestion_data_list in user_dict.items():
                row = [user_email]
                # Add all the suggestions to the user's csv entry
                for suggestion in suggestion_data_list:
                    row.append(suggestion)
                writer.writerow(row)
            # Write as csv
            self.response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            self.response.headers['Content-disposition'] = 'attachment;filename=emails_export.csv'
            filehandle.seek(0)
            self.response.out.write(filehandle.read())
        else:
            context = {'shows': fetch_shows()}
            self.response.out.write(template.render(self.path('export_emails.html'),
                                                    self.add_context(context)))


class MockObject(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class JSTestPage(ViewBase):
    @admin_required
    def get(self):
        state = self.request.get('state', 'action-intervals')
        display = self.request.get('display', 'voting')
        style = self.request.get('style', 'player-options')
        votes_used = self.request.get('votes_used', '')
        available_mock = [1,2,3]
        three_options = [{"value": "Walks into a house", "count": 20},
                        {"value": "Something else crazy long, so forget about what you know about options lenghts", "count": 30},
                        {"value": "Here is a super long option that nobody could have ever guessed because they never dreamed of such things", "count": 10}]
        five_options = [{"value": "Option 1", "count": 20},
                       {"value": "Option 2", "count": 50},
                       {"value": "Option 3", "count": 10},
                       {"value": "Option 4", "count": 15},
                       {"value": "Option 5", "count": 5}]
        player_options = [{'photo_filename': 'freddy.jpg', 'count': 30},
                           {'photo_filename': 'dan.jpg', 'count': 10},
                           {'photo_filename': 'eric.jpg', 'count': 15},
                           {'photo_filename': 'brogan.jpg', 'count': 5},
                           {'photo_filename': 'camilla.png', 'count': 20},
                           {'photo_filename': 'lindsay.png', 'count': 10},
                           {'photo_filename': 'greg.jpg', 'count': 5}]
        show_mock = type('Show',
                         (object,),
                         dict(is_today = True,
                              vote_types=fetch_vote_types()))
        mock_data = {'state': state, 'display': display, 'style': style,
                     'display_name': state}
        if style == 'player-options':
            if display == 'voting':
                mock_data.update({'player_name': 'Freddy',
                                  'photo_filename': 'freddy.jpg',
                                  'options': three_options})
            else:
                mock_data.update({'player_name': 'Freddy',
                                  'photo_filename': 'freddy.jpg',
                                  'voted': state,
                                  'value': three_options[1]['value'],
                                  'count': three_options[1]['count'],
                                  'username': 'Dude Guy'})
        elif style == 'test':
            if display == 'voting':
                mock_data.update({'options': five_options})
            else:
                mock_data.update({'voted': state,
                				  'value': five_options[1]['value'],
                                  'count': five_options[1]['count']})
        elif style == 'options' or style == 'preshow-voted':
            if display == 'voting' and not style == 'preshow-voted':
                mock_data.update({'options': five_options})
            else:
                mock_data.update({'voted': state,
                				  'value': five_options[1]['value'],
                                  'count': five_options[1]['count'],
                                  'username': 'Sparky'})
        elif style == 'all-players' or style == 'player-pool':
            if display == 'voting':
                player_num = int(self.request.get('players', '8'))
                mock_data.update({'role': True,
                                  'options': player_options[:player_num]})
            else:
                mock_data.update({'voted': state,
                                  'display_name': state.capitalize(),
                                  'photo_filename': player_options[0]['photo_filename'],
                                  'count': player_options[0]['count']})
        
        mock_data['used_types'] = []
        # Add used vote types
        for vt in ['test', 'peak-action']:
            if vt in votes_used:
                mock_data['used_types'].append(vt)
                setattr(show_mock, vt, True)
        
        # Add start of vote time
        now_tz = back_to_tz(get_mountain_time())
        end_vote_time = now_tz + datetime.timedelta(seconds=25)
        mock_data['hour'] = end_vote_time.hour
        mock_data['minute'] = end_vote_time.minute
        mock_data['second'] = end_vote_time.second
        mock_data['second'] = end_vote_time.second
        mock_data['voting_length'] = (end_vote_time - now_tz).seconds
        
        test_awarding()

        context = {'show': show_mock,
                   'now_tz': back_to_tz(get_mountain_time()),
                   'host_url': self.request.host_url,
                   'mocked': True,
                   'mock_data': json.dumps(mock_data)}
        self.response.out.write(template.render(self.path('js_test.html'),
                                                self.add_context(context)))
