package routes

import (
	"user-service/handlers"
	"user-service/utils"

	"github.com/gin-gonic/gin"
)

func RegisterUserRoutes(r *gin.Engine) {
	userGroup := r.Group("/users")
	{
		userGroup.POST("/register", handlers.RegisterUser)
		userGroup.GET("/", handlers.GetAllUsers)
		userGroup.GET("/:id", utils.AuthenticateToken(), handlers.GetUser)
	}
}
