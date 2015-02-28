package api


import (
    "time"
)

func getEntityType(entityType string) interface{} {
	switch entityType {
	case "player":
		var p Player
		return &p
	case "suggestion_pool":
		var p SuggestionPool
		return &p
	}
	return nil
}

type Player struct {
	Name          string    `datastore:"name"`
	PhotoFilename string    `datastore:"photo_filename,noindex"`
	Star          bool      `datastore:"star"`
	DateAdded     time.Time `datastore:"date_added"`
}


type SuggestionPool struct {
	Name          string    `datastore:"name"`
	DisplayName   string    `datastore:"display_name"`
	Description   string    `datastore:"description"`
	Created       time.Time `datastore:"created"`
}
