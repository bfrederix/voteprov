package api


import (
	"goapi/src/github.com/gorilla/mux"
	"strconv"
	"appengine"
    "appengine/datastore"
	"net/http"
	"errors"
	"reflect"
	"log"
)



func GetModelEntity(rw http.ResponseWriter, r *http.Request) interface{} {
	log.Println("GetModelEntity: ", "Started")
	// Get URL path variables
	vars := mux.Vars(r)
    entityTypeString := vars["entityType"]
	entityIdString := vars["entityId"]
	// Entity ID string to int
    entityId, err := strconv.ParseInt(entityIdString, 0, 64)
    if err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
    }
	// Get the struct for the entity
	entityStruct := getEntityType(entityTypeString)
	// Get the string name of the model
	model := reflect.TypeOf(entityStruct).Elem().Name()
    c := appengine.NewContext(r)
	// Get the Entity's key
	entityKey := datastore.NewKey(c, model, "", entityId, nil)
	// Try to load the data into the entity struct model
	if err := datastore.Get(c, entityKey, &entityStruct); err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
    }
	return entityStruct
}

/*
func GetPlayer(rw http.ResponseWriter, r *http.Request) (Player) {
	var player Player
	c, playerKey := GetModelEntity(rw, r, "Player")

	if err := datastore.Get(c, playerKey, &player); err != nil {
        http.Error(rw, err.Error(), http.StatusInternalServerError)
    }
	return player
}
*/

func GetModelEntities(rw http.ResponseWriter, r *http.Request, model string, filterArgs map[string]string) {//(appengine.Context, *datastore.Key) {
	err := errors.New("an error")
	http.Error(rw, err.Error(), http.StatusInternalServerError)
	return
}
