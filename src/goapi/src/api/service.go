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


func GetEntityKeyByIDs(c appengine.Context, modelType string, entityIdString string) (*datastore.Key) {
	// Entity ID string to int
	entityId, err := strconv.ParseInt(entityIdString, 0, 64)
	log.Println("GetModelEntity: ", entityId)
	if err != nil {
		// Couldn't find the entity by ID
		// Decode the key
    	entityKey, keyErr := datastore.DecodeKey(entityIdString)
    	if keyErr != nil {
    		// Couldn't decode the key
        	log.Fatal(keyErr)
    	}
    	return entityKey
    }
	// Get the key based on the entity ID
	entityKey := datastore.NewKey(c, modelType, "", entityId, nil)

	return entityKey
}


func GetEntityKeyByURLIDs(rw http.ResponseWriter, r *http.Request, modelType string) (appengine.Context, *datastore.Key) {
	// Get URL path variables
	vars := mux.Vars(r)
	entityIdString := vars["entityId"]
	c := appengine.NewContext(r)
	entityKey := GetEntityKeyByIDs(c, modelType, entityIdString)

	return c, entityKey
}


func GetModelEntities(rw http.ResponseWriter, r *http.Request, modelType string, limit int) (appengine.Context, *datastore.Query) {
	c := appengine.NewContext(r)
	q := datastore.NewQuery(modelType)
	queryParams := r.URL.Query()
	log.Println("Query Params: ", queryParams)
	// If empty query parameters, return the full query results
	if queryParams == nil {
		return c, q
	}
	// If a name was specified
	if name, ok := queryParams["name"]; ok {
		log.Println("Query Name!")
		q = q.Filter("name =", name[0])
	}
	// If a show id/key was specified
	if showID, ok := queryParams["show"]; ok {
		showKey := GetEntityKeyByIDs(c, "Show", showID[0])
		q = q.Filter("show =", showKey)
	}
	// If archived was specified
	if queryParams["archived"] != nil {
		archived, err := strconv.ParseBool(queryParams["archived"][0])
		if err != nil {
			http.Error(rw, err.Error(), http.StatusInternalServerError)
		}
		q = q.Filter("archived =", archived)
	}
	// If ordering on created date was specified
	if queryParams["order_by_created"] != nil {
		orderByCreated, err := strconv.ParseBool(queryParams["order_by_created"][0])
		if err != nil {
			http.Error(rw, err.Error(), http.StatusInternalServerError)
		}
		if orderByCreated == true {
			q = q.Order("created")
		}
	}
	// If we want to return only one item
	if limit != 0 {
		q = q.Limit(limit)
	}

	return c, q
}


// Need to add a new function that can create the query
// With just context and queryParams so that we can use it for setting properties

///////////////////////// Single Item Get /////////////////////////////////


func GetPlayer(rw http.ResponseWriter, r *http.Request, hasID bool) (Player) {
	if hasID == true {
		var player Player
		c, playerKey := GetEntityKeyByURLIDs(rw, r, "Player")

		// Try to load the data into the Player struct model
		if err := datastore.Get(c, playerKey, &player); err != nil {
			http.Error(rw, err.Error(), http.StatusInternalServerError)
		}
		// Make sure the image path is set
		player.SetProperties()
		return player
	} else {
		var players []Player
		c, q := GetModelEntities(rw, r, "Player", 1)
		if _, err := q.GetAll(c, &players); err != nil {
			http.Error(rw, err.Error(), http.StatusInternalServerError)
		}
		// Set the non-model fields
		players[0].SetProperties()
		return players[0]
	}
}


func GetUserProfile(rw http.ResponseWriter, r *http.Request, hasID bool) (UserProfile) {
	if hasID == true {
		var userProfile UserProfile
		c, userProfileKey := GetEntityKeyByURLIDs(rw, r, "UserProfile")

		// Try to load the data into the UserProfile struct model
		if err := datastore.Get(c, userProfileKey, &userProfile); err != nil {
			http.Error(rw, err.Error(), http.StatusInternalServerError)
		}
		// Make sure the image path is set
		//userProfile.SetProperties()
		return userProfile
	} else {
		var userProfiles []UserProfile
		c, q := GetModelEntities(rw, r, "UserProfile", 1)
		if _, err := q.GetAll(c, &userProfiles); err != nil {
			http.Error(rw, err.Error(), http.StatusInternalServerError)
		}
		// Set the non-model fields
		//userProfiles[0].SetProperties()
		return userProfiles[0]
	}
}


///////////////////////// Multiple Item Queries ////////////////////////////


func GetPlayers(rw http.ResponseWriter, r *http.Request) ([]Player) {
	c, q := GetModelEntities(rw, r, "Player", 0)
	var players []Player
	if _, err := q.GetAll(c, &players); err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
    }
	// Set the non-model fields
	for i := range players {
	    player := &players[i]
        player.SetProperties()
    }
	return players
}


func GetShows(rw http.ResponseWriter, r *http.Request) ([]Show) {
	c, q := GetModelEntities(rw, r, "Show", 0)
	var shows []Show
	if _, err := q.GetAll(c, &shows); err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
    }

	return shows
}


func GetLeaderboardEntries(rw http.ResponseWriter, r *http.Request) ([]LeaderboardEntry) {
	c, q := GetModelEntities(rw, r, "LeaderboardEntry", 0)
	var leaderboardEntries []LeaderboardEntry
	if _, err := q.GetAll(c, &leaderboardEntries); err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
    }

	return leaderboardEntries
}
