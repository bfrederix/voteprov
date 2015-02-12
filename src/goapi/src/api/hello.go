package api

import (
	"goapi/src/github.com/gocraft/web"
    "fmt"
    "net/http"
	"strings"
)

type Context struct {
    HelloCount int
}

func (c *Context) SetHelloCount(rw web.ResponseWriter, req *web.Request, next web.NextMiddlewareFunc) {
    c.HelloCount = 5
    next(rw, req)
}

func (c *Context) SayHello(rw web.ResponseWriter, req *web.Request) {
    fmt.Fprint(rw, strings.Repeat("Hello ", c.HelloCount), "World!")
}

func init() {
    router := web.New(Context{}).                   // Create your router
        Middleware(web.LoggerMiddleware).           // Use some included middleware
        Middleware(web.ShowErrorsMiddleware).       // ...
        Middleware((*Context).SetHelloCount).       // Your own middleware!
        Get("/", (*Context).SayHello)
	http.Handle("/", router)
}
