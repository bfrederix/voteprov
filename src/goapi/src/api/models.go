package api


import (
    "time"
)


type Player struct {
	name          string
	photo_filename string
	star          bool
	date_added     time.Time
}


type SuggestionPool struct {
	Name          string
	DisplayName   string
	Description   string
	Created       time.Time
}
