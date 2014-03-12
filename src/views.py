import os
import json
import datetime
import random
import math
from functools import wraps

import webapp2
from webapp2_extras import sessions

from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import ndb

from models import (Show, Player, PlayerAction, ShowPlayer, ShowAction, Action,
					Theme, ActionVote, ThemeVote, LiveActionVote)

from timezone import get_mountain_time, back_to_tz

VOTE_AFTER_INTERVAL = 45


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not users.is_current_user_admin():
            redirect_uri = users.create_login_url(webapp2.get_request().uri)
            print redirect_uri
            return webapp2.redirect(redirect_uri, abort=True)
        return func(*args, **kwargs)
    return decorated_view


def get_today_start():
	today = get_mountain_time().date()
	return datetime.datetime.fromordinal(today.toordinal())


def get_tomorrow_start():
	today = get_mountain_time().date()
	tomorrow = today + datetime.timedelta(1)
	return datetime.datetime.fromordinal(tomorrow.toordinal())


def future_show():
	# See if there is a show today, otherwise users aren't allowed to submit actions
	today_start = get_today_start()
	return bool(Show.query(Show.scheduled >= today_start).get())


def get_live_vote(interval, session_id, player):
	return LiveActionVote.query(
					LiveActionVote.player == player,
					LiveActionVote.interval == int(interval),
					LiveActionVote.created == get_mountain_time().date(),
					LiveActionVote.session_id == str(session_id)).get()

def get_all_live_count(interval, player):
	return LiveActionVote.query(
					LiveActionVote.player == player,
					LiveActionVote.interval == int(interval),
					LiveActionVote.created == get_mountain_time().date()).count()


def get_live_percentage(action, interval, player, all_votes=None):
	action_votes = LiveActionVote.query(
					LiveActionVote.action == action,
					LiveActionVote.player == player,
					LiveActionVote.interval == int(interval),
					LiveActionVote.created == get_mountain_time().date()).count()
	if not all_votes:
		all_votes = get_all_live_count(interval, player)
	# If either of the two live action counts are zero, return zero percent
	if action_votes == 0 or action_votes == 0:
		return 0
	return int(math.floor(100 * float(action_votes)/float(all_votes)))


class ViewBase(webapp2.RequestHandler):
	def __init__(self, *args, **kwargs):
		super(ViewBase, self).__init__(*args, **kwargs)
		self.app = webapp2.get_app()
		user = users.get_current_user()
		if users.get_current_user():
			auth_url = users.create_logout_url(self.request.uri)
			auth_action = 'Logout'
		else:
			auth_url = users.create_login_url(self.request.uri)
			auth_action = 'Login'
		self.context = {
				    'image_path': self.app.registry.get('images'),
		            'css_path': self.app.registry.get('css'),
		            'js_path': self.app.registry.get('js'),
		            'audio_path': self.app.registry.get('audio'),
		            'player_image_path': self.app.registry.get('player_images'),
		            'is_admin': users.is_current_user_admin(),
					'user': user,
					'auth_url': auth_url,
					'auth_action': auth_action,
					'path_qs': self.request.path_qs}
	
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
			# Get a random has to store as the session id
			session['id'] = random.getrandbits(128)
		return session

		
class MainPage(ViewBase):
	def get(self):
		today_start = get_today_start()
		tomorrow_start = get_tomorrow_start()

		# Get the current show
		current_show = Show.query(
			Show.scheduled > today_start,
			Show.scheduled < tomorrow_start).order(-Show.scheduled).get()
		# Get the future shows
		future_shows = Show.query(
			Show.scheduled > tomorrow_start).order(Show.scheduled).filter()
		# Get the previous shows
		previous_shows = Show.query(Show.end_time != None).order(-Show.end_time).filter()
		context = {'current_show': current_show,
				   'future_shows': future_shows,
				   'previous_shows': previous_shows}
		self.response.out.write(template.render(self.path('home.html'),
												self.add_context(context)))


class ShowPage(ViewBase):
	def get(self, show_key):
		show = ndb.Key(Show, int(show_key)).get()
		available_actions = len(Action.query(
							   Action.used == False).fetch())
		context	= {'show': show,
				   'available_actions': available_actions,
				   'host_url': self.request.host_url,
				   'VOTE_AFTER_INTERVAL': VOTE_AFTER_INTERVAL}
		self.response.out.write(template.render(self.path('show.html'),
												self.add_context(context)))

	def post(self, show_key):
		voted = False
		show = ndb.Key(Show, int(show_key)).get()
		action_id = self.request.get('action_id')
		player_id = self.request.get('player_id')
		interval = self.request.get('interval')
		if self.request.get('start_show'):
			show.start_time = get_mountain_time()
			show.put()
		elif action_id and player_id and interval:
			action = ndb.Key(Action, int(action_id))
			player = ndb.Key(Player, int(player_id))
			session_id = str(self.session.get('id'))
			voted = True
			# If the user hasn't already voted
			if not get_live_vote(interval, session_id, player):
				LiveActionVote(action=action,
							   player=player,
							   interval=int(interval),
							   created=get_mountain_time().date(),
							   session_id=session_id).put()
						   
		context	= {'show': show,
				   'host_url': self.request.host_url,
				   'VOTE_AFTER_INTERVAL': VOTE_AFTER_INTERVAL,
				   'voted': voted}
		self.response.out.write(template.render(self.path('show.html'),
												self.add_context(context)))

class CreateShow(ViewBase):
	@admin_required
	def get(self):
		context = {'players': Player.query().fetch()}
		self.response.out.write(template.render(self.path('create_show.html'),
												self.add_context(context)))

	@admin_required
	def post(self):
		length = int(self.request.get('show_length'))
		scheduled_string = self.request.get('scheduled')
		theme = self.request.get('theme')
		player_list = self.request.get_all('player_list')
		action_intervals = self.request.get('action_intervals')
		context = {'players': Player.query().fetch()}
		if length and player_list and action_intervals:
			# Get the list of interval times
			try:
				interval_list = [int(x.strip()) for x in action_intervals.split(',')]
			except ValueError:
				raise ValueError("Invalid interval list '%s'. Must be comma separated.")
			# If there are more action intervals than players, raise an error
			if len(interval_list) > len(player_list):
				raise ValueError("Not enough players for action intervals.")
			if scheduled_string:
				scheduled = datetime.datetime.strptime(scheduled_string,
													   "%d.%m.%Y %H:%M")
			else:
				scheduled = get_mountain_time()
			show = Show(length=length, scheduled=scheduled, theme=theme).put()
			# Add the action intervals to the show
			for interval in interval_list:
				player_action = PlayerAction(interval=interval).put()
				ShowAction(show=show, player_action=player_action).put()
			# Add the players to the show
			for player in player_list:
				player_key = ndb.Key(Player, int(player)).get().key
				ShowPlayer(show=show, player=player_key).put()
			context['created'] = True
		self.response.out.write(template.render(self.path('create_show.html'),
												self.add_context(context)))


class DeleteShows(ViewBase):
	@admin_required
	def get(self):
		context = {'shows': Show.query().fetch()}
		self.response.out.write(template.render(self.path('delete_shows.html'),
												self.add_context(context)))

	@admin_required
	def post(self):
		show_id = int(self.request.get('show_id'))
		show = ndb.Key(Show, int(show_id))
		show_actions = ShowAction.query(ShowAction.show == show).fetch()
		for show_action in show_actions:
			action = show_action.player_action.get().action
			if action:
				action.delete()
			show_action.player_action.delete()
			show_action.key.delete()
		show_players = ShowPlayer.query(ShowPlayer.show == show).fetch()
		for show_player in show_players:
			show_player.key.delete()
		show.delete()
		context = {'deleted': True,
				   'shows': Show.query().fetch()}
		self.response.out.write(template.render(self.path('delete_shows.html'),
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
		date_added = self.request.get('date_added')
		if player_name and photo_filename:
			if date_added:
				date_added = datetime.datetime.strptime(scheduled_string,
													   "%d.%m.%Y %H:%M")
			else:
				date_added = get_mountain_time()
			Player(name=player_name,
				   photo_filename=photo_filename,
				   date_added=date_added).put()
			created = True
		context = {'created': created}
		self.response.out.write(template.render(self.path('add_players.html'),
												self.add_context(context)))


class AddActions(ViewBase):
	def get(self):
		actions = Action.query(
			Action.used == False).order(-Action.vote_value).fetch()
		context = {'actions': actions,
				   'future_show': future_show()}
		self.response.out.write(template.render(self.path('add_actions.html'),
												self.add_context(context)))

	def post(self):
		context = {'future_show': future_show()}
		action = None
		description = self.request.get('description')
		upvote = self.request.get('upvote')
		if description:
			action = Action(description=description).put().get()
			context['created'] = True
		elif upvote:
			action_key = ndb.Key(Action, int(upvote)).get().key
			av = ActionVote.query(
					ActionVote.action == action_key,
					ActionVote.session_id == str(self.session.get('id', '0'))).get()
			if not av:
				ActionVote(action=action_key,
					  	   session_id=str(self.session.get('id')),
					  	   value=1).put()
		if action:
			context['actions'] = Action.query(Action.used == False,
											  Action.key != action.key,
											  ).order(Action.key, -Action.vote_value).fetch()
			context['actions'].append(action)
		else:
			context['actions'] = Action.query(Action.used == False
											 ).order(-Action.vote_value).fetch()
			
		self.response.out.write(template.render(self.path('add_actions.html'),
												self.add_context(context)))


class AddThemes(ViewBase):
	def get(self):
		themes = Theme.query().order(-Theme.vote_value).fetch()
		context = {'themes': themes}
		self.response.out.write(template.render(self.path('add_themes.html'),
												self.add_context(context)))

	def post(self):
		context = {}
		theme = None
		theme_name = self.request.get('theme_name')
		upvote = self.request.get('upvote')
		if theme_name:
			theme = Theme(name=theme_name,
						  vote_value=0).put().get()
			context['created'] = True
		elif upvote:
			theme_key = ndb.Key(Theme, int(upvote)).get().key
			tv = ThemeVote.query(
					ThemeVote.theme == theme_key,
					ThemeVote.session_id == str(self.session.get('id', '0'))).get()
			if not tv:
				ThemeVote(theme=theme_key,
					  	  session_id=str(self.session.get('id')),
					  	  value=1).put()
		if theme:
			# Have to sort first by theme key, since we query on it. Dumb...
			themes = Theme.query(Theme.key != theme.key
								).order(Theme.key, -Theme.vote_value).fetch()
			context['themes'] = themes
			context['themes'].append(theme)
		else:
			themes = Theme.query().order(-Theme.vote_value).fetch()
			context['themes'] = themes
			
		self.response.out.write(template.render(self.path('add_themes.html'),
												self.add_context(context)))


class DeleteActions(ViewBase):
	@admin_required
	def get(self):
		actions = Action.query(
			Action.used == False).fetch()
		context = {'actions': actions}
		self.response.out.write(template.render(self.path('delete_actions.html'),
												self.add_context(context)))

	@admin_required
	def post(self):
		context = {}
		action_list = self.request.get_all('action_list')
		delete_unused = self.request.get_all('delete_unused')
		if action_list:
			for action in action_list:
				action_entity = ndb.Key(Action, int(action)).get()
				# Get all the related action votes and delete them
				action_votes = ActionVote.query(ActionVote.action == action_entity.key).fetch()
				for av in action_votes:
					av.key.delete()
				action_entity.key.delete()
			context['cur_deleted'] = True
		elif delete_unused:
			unused_actions = Action.query(Action.used == False).fetch()
			for unused in unused_actions:
				# Get all the related action votes and delete them
				action_votes = ActionVote.query(ActionVote.action == unused.key).fetch()
				for av in action_votes:
					av.key.delete()
				# Delete the un-used actions
				unused.key.delete()
			context['unused_deleted'] = True
		context['actions'] = Action.query(
			Action.used == False).fetch()
		self.response.out.write(template.render(self.path('delete_actions.html'),
												self.add_context(context)))


class DeleteThemes(ViewBase):
	@admin_required
	def get(self):
		context = {'themes': Theme.query().fetch()}
		self.response.out.write(template.render(self.path('delete_themes.html'),
												self.add_context(context)))

	@admin_required
	def post(self):
		context = {}
		delete_theme_list = self.request.get_all('delete_theme_list')
		if delete_theme_list:
			for theme in delete_theme_list:
				theme_entity = ndb.Key(Theme, int(theme)).get()
				# Get all the related theme votes and delete them
				theme_votes = ThemeVote.query(ThemeVote.theme == theme_entity.key).fetch()
				for tv in theme_votes:
					tv.key.delete()
				theme_entity.key.delete()
			context['cur_deleted'] = True
		context['themes'] = Theme.query().fetch()
		self.response.out.write(template.render(self.path('delete_themes.html'),
												self.add_context(context)))


class ActionsJSON(ViewBase):
	def get(self, show_id, interval):
		show = ndb.Key(Show, int(show_id)).get()
		# Get the player
		player = show.get_player_by_interval(interval)
		# Determine if we've already voted on this interval
		live_vote = get_live_vote(interval, self.session.get('id'), player)
		now = get_mountain_time()
		# Add timezone for comparisons
		now_tz = back_to_tz(now)
		interval_vote_end = show.start_time_tz + datetime.timedelta(minutes=int(interval)) \
							  + datetime.timedelta(seconds=VOTE_AFTER_INTERVAL)
		print "vote end: %s now: %s" % (interval_vote_end, now_tz)
		if now_tz > interval_vote_end:
			player_action = show.get_player_action_by_interval(interval)
			# If an action wasn't already chosen for this interval
			if not player_action.action:
				# Get the actions that were voted on this interval
				interval_voted_actions = []
				live_action_votes = LiveActionVote.query(
										LiveActionVote.player == player,
										LiveActionVote.interval == int(interval),
										LiveActionVote.created == now.date()).fetch()
				# Add the voted on actions to a list
				for lav in live_action_votes:
					interval_voted_actions.append(lav.action)
				# If the actions were voted on
				if interval_voted_actions:
					# Get the most voted, un-used action
					voted_action = Action.query(
									Action.used == False,
									Action.key.IN(interval_voted_actions),
									).order(-Action.live_vote_value).get()
				# If no live action votes were cast
				# take the highest regular voted action that hasn't been used
				else:
					# Get the most voted, un-used action
					voted_action = Action.query(
									Action.used == False,
									).order(-Action.vote_value).get()
				# Set the player action
				player_action.time_of_action = now
				player_action.action = voted_action.key
				player_action.put()
				# Set the action as used
				voted_action.used = True
				voted_action.put()
				percent = get_live_percentage(voted_action,
											  interval,
											  player,
											  all_votes=len(live_action_votes))
				action_data = {'current_action': voted_action.description,
							   'percent': percent}
			else:
				all_votes = get_all_live_count(interval, player)
				percent = get_live_percentage(player_action.action,
											  interval,
											  player,
											  all_votes=all_votes)
				action_data = {'current_action': player_action.action.get().description,
							   'percent': percent}
		elif not live_vote:
			# Return un-used actions, sorted by vote
			unused_actions = Action.query(Action.used == False,
										  ).order(-Action.vote_value).fetch(3)
			all_votes = get_all_live_count(interval, player)
			action_data = []
			for i in range(0, 3):
				percent = get_live_percentage(unused_actions[i].key,
											  interval,
											  player,
											  all_votes=all_votes)
				try:
					action_data.append({'name': unused_actions[i].description,
									    'id': unused_actions[i].key.id(),
									    'percent': percent})
				except IndexError:
					pass
		else:
			action_data = {'voted': True}
		self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
		self.response.out.write(json.dumps(action_data))


class MockObject(object):
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

class JSTestPage(ViewBase):
	@admin_required
	def get(self):
		
		player_freddy = MockObject(get = {'name':'Freddy',
						 			'photo_filename': 'freddy.jpg',
						 			'date_added': get_mountain_time().date()})
		player_dan = MockObject(get = {'name':'Dan',
						 			'photo_filename': 'dan.jpg',
						 			'date_added': get_mountain_time().date()})
		player_jeff = MockObject(get = {'name':'Jeff',
						 			'photo_filename': 'jeff.jpg',
						 			'date_added': get_mountain_time().date()})
		player_list = [player_freddy, player_dan, player_jeff]
		
		start_time = back_to_tz(get_mountain_time())
		end_time = start_time + datetime.timedelta(minutes=4)
		show_mock = type('Show',
						 (object,),
						 dict(scheduled = get_mountain_time(),
							  player_actions = [],
							  theme = 'Pirates',
							  length = 4,
							  start_time = start_time,
							  end_time = end_time,
							  start_time_tz = start_time,
							  end_time_tz = end_time,
							  running = True))
		available_actions = []
		for i in range(1, 4):
			
			player_action_mock = MockObject(interval = i,
							  player = player_list[i-1],
							  time_of_action = get_mountain_time(),
							  action = None)
			show_mock.player_actions.append(player_action_mock)
			action_mock = MockObject(description = 'Option %s' % i,
						 created_date = get_mountain_time().date(),
						 used = False,
						 vote_value = 0,
						 live_vote_value = 0)
			available_actions.append(action_mock)
		context	= {'show': show_mock,
				   'available_actions': available_actions,
				   'host_url': self.request.host_url,
				   'VOTE_AFTER_INTERVAL': VOTE_AFTER_INTERVAL,
				   'mocked': self.request.GET.get('mock', 'full'),
				   'sample': self.request.GET.get('sample'),
				   'is_admin': self.request.GET.get('is_admin')}
		self.response.out.write(template.render(self.path('js_test.html'),
												self.add_context(context)))
