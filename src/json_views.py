import json
import datetime

from google.appengine.ext import ndb

from views_base import ViewBase
from service import (get_show, get_suggestion_pool, get_suggestion,
                     get_suggestion_pool_page_suggestions,
                     create_preshow_vote)
from timezone import get_mountain_time, back_to_tz


class ShowJSON(ViewBase):
    def get(self, show_id):
        show = get_show(key_id=show_id)
        vote_options = show.current_vote_options()
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.out.write(json.dumps(vote_options))


class IntervalTimerJSON(ViewBase):
    def get(self, show_id):
        time_json = {}
        show = get_show(key_id=show_id)
        interval_gap = show.get_interval_gap(show.current_interval)
        if interval_gap:
            # Set the end of this gap
            gap_end = back_to_tz(show.interval_vote_init) + datetime.timedelta(minutes=interval_gap)
        else:
            gap_end = back_to_tz(get_mountain_time())
        time_json.update({'hour': gap_end.hour,
                          'minute': gap_end.minute,
                          'second': gap_end.second})
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.out.write(json.dumps(time_json))


class UpvoteJSON(ViewBase):
    def get(self, suggestion_pool_name):
    	response_dict = {}
    	current_suggestion_pool = get_suggestion_pool(name=suggestion_pool_name)
    	response_dict['item_count'] = len(get_suggestion_pool_page_suggestions(
                                              getattr(current_suggestion_pool, 'key', None)))
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.out.write(json.dumps(response_dict))
    
    def post(self, suggestion_pool_name):
    	# Get the posted data
    	posted_id = self.request.get('id', '')
    	session_id = self.request.get('session_id')
    	# Splits the id into type and item id
    	item_type, item_id = posted_id.split('-')
    	suggestion = get_suggestion(key_id=item_id)
        # See if the user already voted for this suggestion
        if not session_id in suggestion.get_voted_sessions:
        	# If not, create the pre-show vote
            create_preshow_vote({'show': getattr(self.current_show, 'key', None),
                                 'suggestion': suggestion.key,
                                 'session_id': session_id})
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.out.write(json.dumps({}))