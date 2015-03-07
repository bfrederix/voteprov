package api


import (
	"fmt"
    "time"
	"appengine/datastore"
)

type Player struct {
	Name          string    `datastore:"name" json:"name"`
	PhotoFilename string    `datastore:"photo_filename,noindex" json:"photo_filename"`
	Star          bool      `datastore:"star" json:"star"`
	DateAdded     time.Time `datastore:"date_added" json:"date_added"`
	IMGPath       string    `json:"img_path"`
}


func (p *Player) SetProperties() {
    p.IMGPath = fmt.Sprintf("/static/img/players/%s", p.PhotoFilename)
}


type SuggestionPool struct {
	Name          string    `datastore:"name" json:"name"`
	DisplayName   string    `datastore:"display_name" json:"display_name"`
	Description   string    `datastore:"description" json:"description"`
	Created       time.Time `datastore:"created" json:"created"`
}


type VoteType struct {
	// Defined at creation
	Name                string         `datastore:"name" json:"name"`
	DisplayName         string         `datastore:"display_name" json:"display_name"`
	SuggestionPool      *datastore.Key `datastore:"suggestion_pool" json:"suggestion_pool"`
	PreshowVoted        bool           `datastore:"preshow_voted" json:"preshow_voted"`
	HasIntervals        bool           `datastore:"has_intervals" json:"has_intervals"`
	IntervalUsesPlayers bool           `datastore:"interval_uses_players" json:"interval_uses_players"`
	Intervals           []int64        `datastore:"intervals" json:"intervals"`
	Style               string         `datastore:"style" json:"style"`
	Occurs              string         `datastore:"occurs" json:"occurs"`
	Ordering            int64          `datastore:"ordering" json:"ordering"`
	Options             int64          `datastore:"options" json:"options"`
	RandomizeAmount     int64          `datastore:"randomize_amount" json:"randomize_amount"`
	ButtonColor         string         `datastore:"button_color" json:"button_color"`

	// Dynamic
	CurrentInterval     int64          `datastore:"current_interval" json:"current_interval"`
	CurrentInit         time.Time      `datastore:"current_init" json:"current_init"`
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


type Suggestion struct {
	Show           *datastore.Key `datastore:"show" json:"show"`
	SuggestionPool *datastore.Key `datastore:"suggestion_pool" json:"suggestion_pool"`
	Used           bool           `datastore:"used" json:"used"`
	VotedOn        bool           `datastore:"voted_on" json:"voted_on"`
	AmountVotedOn  int64          `datastore:"amount_voted_on" json:"amount_voted_on"`
	Value          string         `datastore:"value" json:"value"`
	PreshowValue   int64          `datastore:"preshow_value" json:"preshow_value"`
	SessionID      string         `datastore:"session_id" json:"session_id"`
	UserID         string         `datastore:"user_id" json:"user_id"`
	Created        time.Time      `datastore:"created" json:"created"`
}


type PreshowVote struct {
	Show           *datastore.Key `datastore:"show" json:"show"`
	Suggestion     *datastore.Key `datastore:"suggestion" json:"suggestion"`
	SessionID      string         `datastore:"session_id" json:"session_id"`
}


type LiveVote struct {
	Show       *datastore.Key `datastore:"show" json:"show"`
	VoteType   *datastore.Key `datastore:"vote_type" json:"vote_type"`
	Player     *datastore.Key `datastore:"player" json:"player"`
	Suggestion *datastore.Key `datastore:"suggestion" json:"suggestion"`
	Interval   int64          `datastore:"interval" json:"interval"`
	SessionID  string         `datastore:"session_id" json:"session_id"`
	UserID     string         `datastore:"user_id" json:"user_id"`
}


type ShowInterval struct {
	Show       *datastore.Key `datastore:"show" json:"show"`
	VoteType   *datastore.Key `datastore:"vote_type" json:"vote_type"`
	Interval   int64          `datastore:"interval" json:"interval"`
	Player     *datastore.Key `datastore:"player" json:"player"`
}


type VoteOptions struct {
	Show       *datastore.Key   `datastore:"show" json:"show"`
	VoteType   *datastore.Key   `datastore:"vote_type" json:"vote_type"`
	Interval   int64            `datastore:"interval" json:"interval"`
	OptionList []*datastore.Key `datastore:"option_list" json:"option_list"`
}


type VotedItem struct {
	VoteType   *datastore.Key `datastore:"vote_type" json:"vote_type"`
	Show       *datastore.Key `datastore:"show" json:"show"`
	Suggestion *datastore.Key `datastore:"suggestion" json:"suggestion"`
	Player     *datastore.Key `datastore:"player" json:"player"`
	Interval   int64          `datastore:"interval" json:"interval"`
}


type Medal struct {
	Name          string `datastore:"name" json:"name"`
	DisplayName   string `datastore:"display_name" json:"display_name"`
	Description   string `datastore:"description" json:"description"`
	ImageFilename string `datastore:"image_filename" json:"image_filename"`
	IconFilename  string `datastore:"icon_filename" json:"icon_filename"`
}


type LeaderboardEntry struct {
	Show        *datastore.Key   `datastore:"show" json:"show"`
	ShowDate    time.Time        `datastore:"show_date" json:"show_date"`
	UserID      string           `datastore:"user_id" json:"user_id"`
	Points      int64            `datastore:"points" json:"points"`
	Wins        int64            `datastore:"wins" json:"wins"`
	Medals      []*datastore.Key `datastore:"medals" json:"medals"`
	Username    string           `json:"username"`
	Suggestions int              `json:"suggestions"`
}


//func (le *LeaderboardEntry) SetProperties() {
//    le.Username = fmt.Sprintf("/static/img/players/%s", p.PhotoFilename)
//}


type UserProfile struct {
	UserID         string    `datastore:"user_id" json:"user_id"`
	Username       string    `datastore:"username" json:"username"`
	StripUsername  string    `datastore:"strip_username" json:"strip_username"`
	Email          string    `datastore:"email" json:"email"`
	LoginType      string    `datastore:"login_type" json:"login_type"`
	CurrentSession string    `datastore:"current_session" json:"current_session"`
	FBAcessToken   string    `datastore:"fb_access_token" json:"fb_access_token"`
	Created        time.Time `datastore:"created" json:"created"`
}


type EmailOptOut struct {
	Email string `datastore:"email" json:"email"`
}


type LeaderboardSpan struct {
	Name      string    `datastore:"name" json:"name"`
	StartDate time.Time `datastore:"start_date" json:"start_date"`
	EndDate   time.Time `datastore:"end_date" json:"end_date"`
}
