package main

import (
	"user-service/routes"

	"github.com/gin-gonic/gin"
)

func main() {
	r := gin.Default()

	// Register user routes
	routes.RegisterUserRoutes(r)

	r.Run(":8082") // Running User Service on port 8082
}
