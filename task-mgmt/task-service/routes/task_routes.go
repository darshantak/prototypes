package routes

import (
	"task-service/handlers"

	"github.com/gin-gonic/gin"
)

func RegisterTaskRoutes(r *gin.Engine) {
	taskRoutes := r.Group("/tasks")
	{
		taskRoutes.GET("/", handlers.GetTasks)
		taskRoutes.POST("/", handlers.CreateTask)
		taskRoutes.GET("/:id", handlers.GetTask)
		taskRoutes.DELETE("/:id", handlers.DeleteTask)
	}
}
