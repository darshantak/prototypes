package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"

	"github.com/gin-gonic/gin"
)

func proxyRequest(target string, c *gin.Context) {
	remote, err := url.Parse(target)
	if err != nil {
		log.Printf("Error parsing target URL: %v\n", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal Server Error"})
		return
	}

	proxy := httputil.NewSingleHostReverseProxy(remote)
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		log.Printf("Proxy error: %v\n", err)
		http.Error(w, "Proxy Error", http.StatusBadGateway)
	}

	log.Printf("Forwarding request: %s %s -> %s%s", c.Request.Method, c.Request.URL.Path, target, c.Request.URL.Path)

	c.Request.URL.Host = remote.Host
	c.Request.URL.Scheme = remote.Scheme
	c.Request.Header.Set("X-Forwarded-Host", c.Request.Host)
	c.Request.Host = remote.Host

	proxy.ServeHTTP(c.Writer, c.Request)
}

func main() {
	r := gin.Default()

	// API Gateway Routes
	r.Any("/tasks/*proxyPath", func(c *gin.Context) {
		proxyRequest("http://localhost:8081", c)
	})

	r.Any("/users/*proxyPath", func(c *gin.Context) {
		proxyRequest("http://localhost:8082", c)
	})

	log.Println("API Gateway running on port 8080")
	r.Run(":8080")
}
