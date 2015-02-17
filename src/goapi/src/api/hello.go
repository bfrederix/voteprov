package api

import (
	"goapi/src/github.com/gocraft/web"
    "fmt"
    "net/http"
)

type Context struct {
    HelloCount int
}

func (c *Context) SayHello(rw web.ResponseWriter, req *web.Request) {
    fmt.Fprint(rw,  c)
}

func init() {
	// Create the router
    router := web.New(Context{}).
        Get("/", (*Context).SayHello)               // Main url
	http.Handle("/", router)
}
