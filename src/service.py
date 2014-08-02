from google.appengine.ext import ndb

from models import (Show, Player, VoteType, Suggestion, PreshowVote,
                    ShowInterval, VoteOptions, LiveVote, SuggestionPool,
                    VotedItem, LeaderboardEntry, Medal, UserProfile,
                    get_current_show, VOTE_STYLE, OCCURS_TYPE)
from timezone import (get_today_start, get_tomorrow_start)


def get_show(**kwargs):
    return get_model_entity(Show, **kwargs)


def get_vote_type(**kwargs):
    return get_model_entity(VoteType, **kwargs)


def get_player(**kwargs):
    return get_model_entity(Player, **kwargs)


def get_suggestion(**kwargs):
    return get_model_entity(Suggestion, **kwargs)


def get_suggestion_pool(**kwargs):
    return get_model_entity(SuggestionPool, **kwargs)


def get_voted_item(**kwargs):
    return get_model_entity(VotedItem, **kwargs)


def get_medal(**kwargs):
    return get_model_entity(Medal, **kwargs)


def get_leaderboard_entry(**kwargs):
    return get_model_entity(LeaderboardEntry, **kwargs)


def get_user_profile(**kwargs):
    return get_model_entity(UserProfile, **kwargs)


def get_model_entity(model, key_id=None, name=None, key_only=False, delete=False,
                     show=None, vote_type=None, user_id=None, username=None):
    # If key id is given, just return the key
    if key_id:
        key = ndb.Key(model, int(key_id))
        # Return just the key
        if key_only == True:
            return key
        # If a key was found, return the entity
        elif key:
            return key.get()
        # Otherwise, return nothing
        else:
            return None
    args = []
    if name:
        args.append(model.name == name)
    if show:
        args.append(model.show == show)
    if vote_type:
        args.append(model.vote_type == vote_type)
    if user_id:
        args.append(model.user_id == user_id)
    if username:
        args.append(model.username == username)
    item_entity = model.query(*args).get()
    # If we should delete the item
    if delete and item_entity:
        item_entity.key.delete()
        return
    return item_entity


def fetch_shows(**kwargs):
    return fetch_model_entities(Show, **kwargs)


def fetch_suggestions(**kwargs):
    return fetch_model_entities(Suggestion, **kwargs)


def fetch_players(**kwargs):
    return fetch_model_entities(Player, **kwargs)


def fetch_vote_types(**kwargs):
    return fetch_model_entities(VoteType, **kwargs)

def fetch_suggestion_pools(**kwargs):
    # Get SuggestionPool's that are used before the show
    if kwargs.get('occurs'):
        suggestion_pools = []
        # Get the suggestion pools grouped by when they occur
        vts = VoteType.query(VoteType.occurs == kwargs.get('occurs'),
                             VoteType.name != 'test').fetch()
        for vt in vts:
            if getattr(vt, 'suggestion_pool', None):
                # Get the suggestion pool
                suggestion_pool_entity = vt.suggestion_pool.get()
                # Make sure that suggestion pool hasn't already been added
                # to the suggestion pool list
                if not suggestion_pool_entity in suggestion_pools:
                    suggestion_pools.append(suggestion_pool_entity)
        return suggestion_pools
    else:
        return fetch_model_entities(SuggestionPool, **kwargs)

def fetch_preshow_votes(**kwargs):
    return fetch_model_entities(PreshowVote, **kwargs)


def fetch_vote_options(**kwargs):
    return fetch_model_entities(VoteOptions, **kwargs)


def fetch_live_votes(**kwargs):
    return fetch_model_entities(LiveVote, **kwargs)


def fetch_voted_items(**kwargs):
    return fetch_model_entities(VotedItem, **kwargs)


def fetch_show_intervals(**kwargs):
    return fetch_model_entities(ShowInterval, **kwargs)


def fetch_user_medals(**kwargs):
    return fetch_model_entities(UserMedal, **kwargs)


def fetch_leaderboard_entries(**kwargs):
    entries = fetch_model_entities(LeaderboardEntry, **kwargs)
    if kwargs.get('unique_by_user'):
        user_dict = {}
        for entry in entries:
            # Set defaults for wins and points if nothing exists
            user_dict.setdefault(entry.user_id, {})
            user_dict[entry.user_id].setdefault('points', 0)
            user_dict[entry.user_id].setdefault('wins', 0)
            user_dict[entry.user_id].setdefault('medals', 0)
            # Add the wins and points for the user from this particular show
            user_dict[entry.user_id]['points'] += entry.points
            user_dict[entry.user_id]['wins'] += entry.wins
            # Fetch the number of suggestions the user made in the show
            user_dict[entry.user_id]['suggestions'] += fetch_suggestions(user_id=user_id,
                                                                         show=entry.show,
                                                                         count=True)
            # Fetch the number of medals the user earned in the show
            user_dict[entry.user_id]['medals'] += fetch_user_medals(user_id=user_id,
                                                                    show=entry.show,
                                                                    count=True)
    else:
        return entities


def fetch_model_entities(model, show=None, vote_type=None, suggestion_pool=None,
                         used=None, voted_on=None,
                         suggestion=None, uses_suggestions=None,
                         month=None, year=None, user_id=None,
                         limit=None, offset=None, keys_only=False,
                         order_by_preshow_value=False, delete=False, count=False,
                         order_by_ordering=False,
                         order_by_points=False):
    args = []
    fetch_args = {}
    ordering = None
    # Fetch by show key
    if show:
        args.append(model.show == show)
    # Fetch by VoteType name
    if vote_type:
        args.append(model.vote_type == vote_type)
    # Fetch by SuggestionPool
    if suggestion_pool:
        args.append(model.suggestion_pool == suggestion_pool)
    # Fetch by whether it's used or not
    if used != None:
        args.append(model.used == used)
    # Fetch by whether it's been voted on or not
    if voted_on != None:
        args.append(model.voted_on == voted_on)
    # Fetch related to a suggestion
    if suggestion != None:
        args.append(model.suggestion == suggestion)
    # Fetch related to a suggestion
    if uses_suggestions != None:
        args.append(model.uses_suggestions == uses_suggestions)
    # Fetch by month
    if month != None:
        ## ADD THIS LATER ##
        pass
    # Fetch by year
    if year != None:
        ## ADD THIS LATER ##
        pass
    # Fetch by user_id
    if user_id != None:
        args.append(model.user_id == user_id)
    
    # Delete the queried items
    if delete:
        item_keys = model.query(*args).fetch(keys_only=True)
        # Delete all the items
        ndb.delete_multi(item_keys)
        return
    
    # Fetch the limit given
    if limit:
        fetch_args['limit'] = limit
    # If we just need the keys
    if keys_only:
        fetch_args['keys_only'] = keys_only
    ordering = []
    # Order by preshow_value
    if order_by_preshow_value:
        ordering += [-model.preshow_value]
    # Order by ordering
    if order_by_ordering:
        ordering += [model.ordering]
    # Order by points
    if order_by_points:
        ordering += [model.points]
        
    if ordering:
        return model.query(*args).order(*ordering).fetch(**fetch_args)
    elif count:
        return model.query(*args).count()
    else:
        return model.query(*args).fetch(**fetch_args)


def create_show(create_data):
    return create_model_entity(Show, create_data)


def create_player(create_data):
    return create_model_entity(Player, create_data)


def create_show_interval(create_data):
    return create_model_entity(ShowInterval, create_data)


def create_vote_type(create_data):
    return create_model_entity(VoteType, create_data)


def create_suggestion_pool(create_data):
    return create_model_entity(SuggestionPool, create_data)


def create_preshow_vote(create_data):
    return create_model_entity(PreshowVote, create_data)


def create_live_vote(create_data):
    return create_model_entity(LiveVote, create_data)


def create_user_profile(create_data):
    if not get_user_profile(username=create_data.get('username')):
        return create_model_entity(UserProfile, create_data)
    else:
        return None


def create_model_entity(model, create_data):
    create_kwargs = {}
    for key, value in create_data.items():
        create_kwargs[key] = value
    return model(**create_kwargs).put()


def get_live_vote_exists(show, vote_type, interval, session_id):
    query_args = [LiveVote.show == show,
                  LiveVote.vote_type == vote_type,
                  LiveVote.interval == interval,
                  LiveVote.session_id == str(session_id)]
    return bool(LiveVote.query(*query_args).count())


def get_unused_suggestions():
    """Get unused suggestions for all vote types, categorized by vote type"""
    suggestion_pools = fetch_suggestion_pools()
    for suggestion_pool in suggestion_pools:
        suggestions = fetch_suggestions(suggestion_pool=suggestion_pool.key,
                                        used=False,
                                        voted_on=False)
        setattr(suggestion_pool, 'suggestions', suggestions)
    return suggestion_pools


def pre_show_voting_post(show_key, suggestion_pool, request, session_id, user_id, is_admin):
    context = {'session_id': session_id}
    suggestion_entity = None
    # Get the value of the entry that was added
    entry_value = request.get('entry_value')
    # Get the upvote
    upvote = request.get('upvote')
    # If a delete was requested on an entry
    delete_id = request.get('delete_id')
    # If this is a brand new entry
    if entry_value:
        already_exists = Suggestion.query(
                             Suggestion.value == entry_value,
                             Suggestion.suggestion_pool == suggestion_pool.key).get()
        if not already_exists:
            # Create the suggestion
            suggestion_entity = Suggestion(value=entry_value,
                                           show=show_key,
                                           suggestion_pool=suggestion_pool.key,
                                           preshow_value=0,
                                           session_id=session_id,
                                           user_id=user_id).put().get()
            context['created'] = True
    elif upvote:
        suggestion_key = ndb.Key(Suggestion, int(upvote)).get().key
        # Get the pre-show vote if it exists for that suggestion and session id
        pv = PreshowVote.query(
                PreshowVote == suggestion_key,
                PreshowVote.session_id == session_id).get()
        # If it doesn't exist, create it
        if not pv:
            PreshowVote(show=show_key,
                        suggestion=suggestion_key,
                        session_id=session_id).put()
    # If a delete was requested
    elif delete_id:
        # Fetch the suggestion entity
        suggestion_entity = ndb.Key(Suggestion, int(delete_id)).get()
        # Make sure the entry was either the session id that created it
        # Or this is an admin user
        if session_id == suggestion_entity.session_id or is_admin:
            suggestion_entity.key.delete()
    
    # If an new suggestion entity was created
    if suggestion_entity:
        # Have to sort first by suggestion key, since we query on it. Dumb...
        suggestion_entities = get_suggestion_pool_page_suggestions(suggestion_pool.key,
                                                                   ignore_key=suggestion_entity.key,
                                                                   ordered=False)
        suggestion_entities.sort(key=lambda x: (x.preshow_value, x.created), reverse=True)
        # If the entity wasn't deleted
        if not delete_id:
            # Add the newly added suggestion entity
            suggestion_entities.append(suggestion_entity)
    else:
        suggestion_entities = get_suggestion_pool_page_suggestions(suggestion_pool.key)
    context['suggestions'] = suggestion_entities
    
    return context


def get_current_suggestion_pools(current_show):
    if current_show:
        suggestion_pools = fetch_suggestion_pools(occurs='during')
    else:
        # Fetch before show creation pools
        suggestion_pools = fetch_suggestion_pools(occurs='before')
    return suggestion_pools


def get_suggestion_pool_page_suggestions(suggestion_pool, ignore_key=None,
                                         ordered=True):
    query_args = [Suggestion.suggestion_pool == suggestion_pool,
                  Suggestion.used == False]
    # If we should ignore a specific key
    if ignore_key:
        query_args.append(Suggestion.key != ignore_key)
    # If it should be ordered
    if ordered:
        return Suggestion.query(*query_args).order(-Suggestion.preshow_value,
                                                    Suggestion.created).fetch()
    # Otherwise return results without ordering
    else:
        return Suggestion.query(*query_args).fetch()


def add_medal(show, medal_name, user_id):
    # Get the user id of the medal winner
    user_id = medal_dict[medal_name]['user_id']
    # If a user did win
    if user_id:
        # Get the medal winner
        medal_winner = get_leaderboard_entry(show=show, user_id=user_id)
        # Add the medal to the winner
        medal_winner.medals.append(get_medal(name=medal_name))
        medal_winner.put()


def award_leaderboard_medals(show, test=None):
    if not test:
        leaderboard_entries = fetch_leaderboard_entries(show=show,
                                                        order_by_points=True)
    else:
        ### TEST MOCK ###
        leaderboard_entries = test
    medal_dict = {'points': {'max': 0, 'user_id': None},
                  'points_with_wins': {'max': 0, 'user_id': None},
                  'points_without_win': {'max': 0, 'user_id': None},
                  'win_percentage': {'max': 0, 'user_id': None}}
    for entry in leaderboard_entries:
        # Determine if a user has reached a new high for points
        if entry.points > medal_dict['points']['max']:
            medal_dict['points']['max'] = entry.points
            medal_dict['points']['user_id'] = entry.user_id
        win_addition = entry.wins * 5
        # Determine if a user has reached a new high for points with wins factored in
        if (entry.points + win_addition) > medal_dict['points_with_wins']['max']:
            medal_dict['points_with_wins']['max'] = entry.points + win_addition
            medal_dict['points_with_wins']['user_id'] = entry.user_id
        # Determine if a user has reached a new high for points without a win
        if not entry.wins and entry.points > medal_dict['points_without_win']['max']:
            medal_dict['points_without_win']['max'] = entry.points
            medal_dict['points_without_win']['user_id'] = entry.user_id
        ### TEST MOCK ###
        if not test:
            user_suggestions = fetch_suggestions(show=show,
                                                 user_id=entry.user_id,
                                                 count=True)
        else:
            user_suggestions = entry.user_suggestions
        try:
            win_percentage = int(100 * (float(entry.wins) / float(user_suggestions)))
        except ZeroDivisionError:
            win_percentage = 0
        # Determine if a user has reached a new high for points with wins factored in
        if win_percentage > medal_dict['win_percentage']['max']:
            medal_dict['win_percentage']['max'] = win_percentage
            medal_dict['win_percentage']['user_id'] = entry.user_id
    
    if not test:
        # Award the points medal
        add_medal(show, 'points', medal_dict['points']['user_id'])
    
        # Award the points factored with wins medal
        add_medal(show, 'points_with_wins', medal_dict['points_with_wins']['user_id'])
    
        # Award the points without a win medal
        add_medal(show, 'points_without_win', medal_dict['points_without_win']['user_id'])
    
        # Award the win percentage medal
        add_medal(show, 'win_percentage', medal_dict['win_percentage']['user_id'])
    ### TEST MOCK ###
    else:
        return [medal_dict['points']['user_id'],
                medal_dict['points_with_wins']['user_id'],
                medal_dict['points_without_win']['user_id'],
                medal_dict['win_percentage']['user_id']]


def test_awarding():
    test_entries = [
        type('LeaderboardEntry',(object,), dict(user_id=1, points=30, wins=1, user_suggestions=10)),
        type('LeaderboardEntry',(object,), dict(user_id=2, points=5, wins=1, user_suggestions=10)),
        type('LeaderboardEntry',(object,), dict(user_id=3, points=21, wins=3, user_suggestions=10)),
        type('LeaderboardEntry',(object,), dict(user_id=4, points=20, wins=0, user_suggestions=5)),
        type('LeaderboardEntry',(object,), dict(user_id=5, points=15, wins=0, user_suggestions=5)),
        type('LeaderboardEntry',(object,), dict(user_id=6, points=15, wins=1, user_suggestions=2))]
    results = award_leaderboard_medals(None, test=test_entries)
    assert results == [1, 3, 4, 6]
