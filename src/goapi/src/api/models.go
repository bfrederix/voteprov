package api


import (
    "time"
	"appengine/datastore"
)

type Player struct {
	Name          string    `datastore:"name" json:"name"`
	PhotoFilename string    `datastore:"photo_filename,noindex" json:"photo_filename"`
	Star          bool      `datastore:"star" json:"star"`
	DateAdded     time.Time `datastore:"date_added" json:"date_added"`
}


type SuggestionPool struct {
	Name          string    `datastore:"name"`
	DisplayName   string    `datastore:"display_name"`
	Description   string    `datastore:"description"`
	Created       time.Time `datastore:"created"`
}


type Show struct {
	VoteLength      int64            `datastore:"vote_length" json:"vote_length"`
	ResultLength    int64            `datastore:"result_length" json:"result_length"`
	VoteOptions     int64            `datastore:"vote_options" json:"vote_options"`
	Timezone        string           `datastore:"timezone" json:"timezone"`
	VoteTypes       []*datastore.Key `datastore:"vote_types" json:"vote_types"`
	Players         []*datastore.Key `datastore:"players" json:"players"`
	PlayerPool      []*datastore.Key `datastore:"player_pool" json:"player_pool"`
	Created         time.Time        `datastore:"created" json:"created"`
	Archived        bool             `datastore:"archived" json:"archived"`
	CurrentVoteType *datastore.Key   `datastore:"current_vote_type" json:"current_vote_type"`
	CurrentVoteInit time.Time        `datastore:"current_vote_init" json:"current_vote_init"`
	RecapType       *datastore.Key   `datastore:"recap_type" json:"recap_type"`
	RecapInit       time.Time        `datastore:"recap_init" json:"recap_init"`
	Locked          bool             `datastore:"locked" json:"locked"`
}


type LeaderboardEntry struct {
	Show     *datastore.Key   `datastore:"show" json:"show"`
	ShowDate time.Time        `datastore:"show_date" json:"show_date"`
	UserID   string           `datastore:"user_id" json:"user_id"`
	Points   int64            `datastore:"points" json:"points"`
	Wins     int64            `datastore:"wins" json:"wins"`
	Medals   []*datastore.Key `datastore:"medals" json:"medals"`
}

