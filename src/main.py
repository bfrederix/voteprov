#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#import sys
#for p in ['gaepytz-2011h.zip']:
#    sys.path.insert(0, p)

import os
import webapp2

from views_base import RobotsTXT, LoaderIO
from user_views import (MainPage, LiveVote, AddSuggestions,
						LiveVoteWorker, ShowLeaderboard,
						UserLeaderboard, AllTimeLeaderboard)
from admin_views import (ShowPage, CreateShow, DeleteTools,
						 SuggestionPools, VoteTypes,
					     JSTestPage, AddPlayers, IntervalTimer)
from json_views import (ShowJSON, IntervalTimerJSON, UpvoteJSON)


config = {'webapp2_extras.sessions': {
    	     'secret_key': '8djs1qjs3jsm'
    	     }
    	}


app = webapp2.WSGIApplication([
	# Robots.txt
	(r'/robots.txt', RobotsTXT),
	(r'/loaderio-9b6fa50492da1609dc61b9198b767688.txt', LoaderIO),
	# User pages
    (r'/', MainPage),
    (r'/leaderboard/show/(\d+)/', ShowLeaderboard),
    (r'/leaderboard/user/(\d+)/', UserLeaderboard),
    (r'/leaderboards/(\d{4})/([1-12]*)/', AllTimeLeaderboard),
    (r'/leaderboards/(\d{4})/', AllTimeLeaderboard),
    (r'/leaderboards/', AllTimeLeaderboard),
    (r'/live_vote/', LiveVote),
    (r'/suggestions/([a-zA-Z\-]+)/', AddSuggestions),
    (r'/suggestions/', AddSuggestions),
    # Admin URLS
    (r'/show/(\d+)/', ShowPage),
    (r'/create_show/', CreateShow),
    (r'/vote_types/', VoteTypes),
    (r'/suggestion_pools/', SuggestionPools),
    (r'/add_players/', AddPlayers),
    (r'/delete_tools/', DeleteTools),
    (r'/interval_timer/', IntervalTimer),
    (r'/js_test/', JSTestPage),
    # JSON ENDPOINT
    (r'/show_json/(\d+)/', ShowJSON),
    (r'/interval_timer_json/(\d+)/', IntervalTimerJSON),
    (r'/upvote_json/([a-zA-Z\-]+)/',UpvoteJSON),
    # Task Queues
    (r'/live_vote_worker/', LiveVoteWorker),
],
  config=config,
  debug=True)


app.registry['templates'] = os.path.join(os.path.dirname(__file__),
										 'templates/')
app.registry['images'] = os.path.join(os.path.dirname(__file__),
										 '/static/img/')
app.registry['player_images'] = os.path.join(os.path.dirname(__file__),
										 '/static/img/players/')
app.registry['css'] = os.path.join(os.path.dirname(__file__),
										 '/static/css/')
app.registry['js'] = os.path.join(os.path.dirname(__file__),
										 '/static/js/')
app.registry['audio'] = os.path.join(os.path.dirname(__file__),
										 '/static/audio/')

