package api

import (
	"goapi/src/github.com/gorilla/mux"
    "fmt"
    "net/http"
)

func Index(rw http.ResponseWriter, r *http.Request) {
	GetPlayer(rw, r)
    fmt.Fprint(rw, "Welcome!")
}


func CreateHandler() *mux.Router {
	r := mux.NewRouter()
	s := r.PathPrefix("/v1").Subrouter()
	s.HandleFunc("/player/{playerId}", Index)

	return r
}


func init() {
	http.Handle("/", CreateHandler())
}
