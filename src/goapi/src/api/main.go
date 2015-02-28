package api

import (
	"goapi/src/github.com/gorilla/mux"
    "fmt"
    "net/http"
	"log"
)

func Entity(rw http.ResponseWriter, r *http.Request) {
	entity := GetModelEntity(rw, r)
	log.Println("Logging: ", "Hello!")
    fmt.Fprint(rw, "Welcome! ", entity.Name)
}


func CreateHandler() *mux.Router {
	r := mux.NewRouter()
	s := r.PathPrefix("/v1").Subrouter()
	s.HandleFunc("/{entityType}/{entityId}", Entity)

	return r
}


func init() {
	http.Handle("/", CreateHandler())
}
