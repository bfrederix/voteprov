package api


import (
	"goapi/src/github.com/gorilla/mux"
	"strconv"
	"appengine"
    "appengine/datastore"
	"net/http"
)


func GetPlayer(rw http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
    playerIdString := vars["playerId"]
	// string to int
    playerId, err := strconv.ParseInt(playerIdString, 0, 64)
    if err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
    }
    c := appengine.NewContext(r)
	playerKey := datastore.NewKey(c, "Player", "", playerId, nil)
	var player Player
	if err := datastore.Get(c, playerKey, &player); err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
        return
    }

}
