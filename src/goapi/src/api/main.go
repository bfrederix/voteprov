package api

import (
	"goapi/src/github.com/gorilla/mux"
    //"fmt"
    "net/http"
	"log"
	"encoding/json"
)

func PlayerAPIGet(rw http.ResponseWriter, r *http.Request) {
	// Get the player entity
	player := GetPlayer(rw, r)
	log.Println("Logging: ", "Hello!")
	// Encode the player into JSON output
	json.NewEncoder(rw).Encode(player)
    //fmt.Fprint(rw, "Welcome! ", player.Name)
}

func PlayersAPIGet(rw http.ResponseWriter, r *http.Request) {
	// Get the player entity
	players := GetPlayers(rw, r)
	log.Println("Logging: ", "Hello!")
	// Encode the player into JSON output
	json.NewEncoder(rw).Encode(players)
    //fmt.Fprint(rw, "Welcome! ", player.Name)
}

func ShowsAPIGet(rw http.ResponseWriter, r *http.Request) {
	shows := GetShows(rw, r)
	json.NewEncoder(rw).Encode(shows)
}

func CreateHandler() *mux.Router {
	r := mux.NewRouter()
	s := r.PathPrefix("/v1").Subrouter()
	s.HandleFunc("/player/{entityId}/", PlayerAPIGet)
	s.HandleFunc("/players/", PlayersAPIGet)
	s.HandleFunc("/shows/", ShowsAPIGet)

	return r
}


func init() {
	http.Handle("/", CreateHandler())
}
