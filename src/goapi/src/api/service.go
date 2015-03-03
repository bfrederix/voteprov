package api


import (
	"goapi/src/github.com/gorilla/mux"
	"strconv"
	"appengine"
    "appengine/datastore"
	"net/http"
	//"errors"
	"log"
)


func GetModelEntity(rw http.ResponseWriter, r *http.Request, modelName string) (appengine.Context, *datastore.Key) {
	log.Println("GetModelEntity: ", "Started")
	// Get URL path variables
	vars := mux.Vars(r)
	entityIdString := vars["entityId"]
	c := appengine.NewContext(r)
	// Entity ID string to int
	entityId, err := strconv.ParseInt(entityIdString, 0, 64)
	log.Println("GetModelEntity: ", entityId)
	if err != nil {
		// Couldn't find the entity by ID
		// Decode the key
    	entityKey, keyErr := datastore.DecodeKey(entityIdString)
    	if keyErr != nil {
    		// Couldn't decode the key
        	http.Error(rw, keyErr.Error(), http.StatusInternalServerError)
    	}
    	return c, entityKey
    }
	// Get the key based on the entity ID
	entityKey := datastore.NewKey(c, modelName, "", entityId, nil)

	return c, entityKey
}


func GetPlayer(rw http.ResponseWriter, r *http.Request) (Player) {
	var player Player
	c, playerKey := GetModelEntity(rw, r, "Player")

	// Try to load the data into the Player struct model
	if err := datastore.Get(c, playerKey, &player); err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
    }
	return player
}

/*
func GetModelEntities(rw http.ResponseWriter, r *http.Request) {//(appengine.Context, *datastore.Key) {
	c := appengine.NewContext(r)
	_, err := q.GetAll(c, &players) // _ is keys
	if err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
    }
	err := errors.New("an error")
	//http.Error(rw, err.Error(), http.StatusInternalServerError)
	return
}
*/

func GetPlayers(rw http.ResponseWriter, r *http.Request) ([]Player) {
	q := datastore.NewQuery("Player")
	var players []Player
	c := appengine.NewContext(r)
	_, err := q.GetAll(c, &players) // _ is keys
	if err != nil {
        c.Errorf("Fetching Players: %v", err)
        return nil
    }
	return players
}


func GetShows(rw http.ResponseWriter, r *http.Request) ([]Show) {
	c := appengine.NewContext(r)
	q := datastore.NewQuery("Show")
	var filteredQ = q
	queryParams := r.URL.Query()
	switch {
	case queryParams["archived"] != nil:
		archived, err := strconv.ParseBool(queryParams["archived"][0])
		log.Println("GetShows: ", archived)
		if err != nil {
			c.Errorf("Fetching Shows: %v", err)
			return nil
		}
		filteredQ = q.Filter("archived =", archived)
	}
	var shows []Show
	_, err := filteredQ.GetAll(c, &shows) // _ is keys
	if err != nil {
        c.Errorf("Fetching Shows: %v", err)
        return nil
    }

	return shows
}
