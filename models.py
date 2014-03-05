import datetime
import random

from google.appengine.ext import ndb

from timezone import mountain_time, get_mountain_time, today


class Player(ndb.Model):
	name = ndb.StringProperty(required=True)
	photo_filename = ndb.StringProperty(required=True)
	date_added = ndb.DateTimeProperty()
	
	@property
	def img_path(self):
		return "/static/img/players/%s" % self.photo_filename


class Show(ndb.Model):
	scheduled = ndb.DateTimeProperty()
	theme = ndb.StringProperty()
	length = ndb.IntegerProperty(required=True)
	start_time = ndb.DateTimeProperty()
	end_time = ndb.DateTimeProperty()
	
	@property
	def players(self):
		show_players = ShowPlayer.query(ShowPlayer.show == self.key).fetch()
		return [x.player.get() for x in show_players if getattr(x, 'player', None)]
	
	@property
	def player_actions(self):
		action_intervals = ShowAction.query(ShowAction.show == self.key).fetch()
		return [x.player_action.get() for x in action_intervals if getattr(x, 'player_action', None) and x.player_action.get()]
	
	@property
	def running(self):
		#return True
		if not self.start_time or not self.end_time:
			return False
		now = get_mountain_time()
		if now >= self.start_time and now <= self.end_time:
			return True
		return False

	@property
	def is_today(self):
		return self.scheduled.date() == today
	
	@property
	def in_future(self):
		return self.scheduled.date() > today
	
	@property
	def in_past(self):
		return self.scheduled.date() < today
	
	def put(self, *args, **kwargs):
		# If start_time is specified, it must mean a show has started
		if self.start_time and self.length:
			# Set the end time of the show
			self.end_time = self.start_time + datetime.timedelta(minutes=self.length)
			# Make a copy of the list of players and randomize it
			rand_players = self.players
			random.shuffle(rand_players, random.random)
			for player_action in self.player_actions:
				# Pop a random player off the list
				player_action.player = rand_players.pop().key
				player_action.time_of_action = self.start_time + \
									  datetime.timedelta(minutes=player_action.interval)
				player_action.put()
		return super(Show, self).put(*args, **kwargs)


class Action(ndb.Model):
	description = ndb.StringProperty(required=True)
	created_date = ndb.DateProperty(required=True)
	used = ndb.BooleanProperty(default=False)
	vote_value = ndb.IntegerProperty(default=0)

	def put(self, *args, **kwargs):
		self.created_date = mountain_time
		return super(Action, self).put(*args, **kwargs)	


class Theme(ndb.Model):
	created_date = ndb.DateTimeProperty(required=True)
	name = ndb.StringProperty(required=True)
	vote_value = ndb.IntegerProperty(default=0)
	
	def put(self, *args, **kwargs):
		self.created_date = mountain_time
		return super(Theme, self).put(*args, **kwargs)
	

class PlayerAction(ndb.Model):
	interval = ndb.IntegerProperty(required=True)
	player = ndb.KeyProperty(kind=Player)
	time_of_action = ndb.DateTimeProperty()
	action = ndb.KeyProperty(kind=Action)


class ShowPlayer(ndb.Model):
	show = ndb.KeyProperty(kind=Show, required=True)
	player = ndb.KeyProperty(kind=Player, required=True)


class ShowAction(ndb.Model):
	show = ndb.KeyProperty(kind=Show, required=True)
	player_action = ndb.KeyProperty(kind=PlayerAction, required=True)


class ActionVote(ndb.Model):
	action = ndb.KeyProperty(kind=Action, required=True)
	value = ndb.IntegerProperty(required=True, choices=[1, -1])
	session_id = ndb.StringProperty(required=True)
	
	def put(self, *args, **kwargs):
		action = Action.query(Action.key == self.action).get()
		action.vote_value += self.value
		action.put()
		return super(ActionVote, self).put(*args, **kwargs)


class ThemeVote(ndb.Model):
	theme = ndb.KeyProperty(kind=Theme, required=True)
	value = ndb.IntegerProperty(required=True, choices=[1, -1])
	session_id = ndb.StringProperty(required=True)

	def put(self, *args, **kwargs):
		theme = Theme.query(Theme.key == self.theme).get()
		theme.vote_value += self.value
		theme.put()
		return super(ThemeVote, self).put(*args, **kwargs)


class LiveActionVote(ndb.Model):
	action = ndb.KeyProperty(kind=Action, required=True)
	player = ndb.KeyProperty(kind=Player, required=True)
	interval = ndb.IntegerProperty(required=True)
	session_id = ndb.StringProperty(required=True)
	created = ndb.DateProperty(required=True)
