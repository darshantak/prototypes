package main

import (
	"fmt"
	"taskapp/models"
	"taskapp/routes"
	"taskapp/storage"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

func backFillData() {
	tasks := []models.Task{
		{ID: uuid.New().String(), Title: "Complete project report", Status: "Pending"},
		{ID: uuid.New().String(), Title: "Fix API bug", Status: "In Progress"},
		{ID: uuid.New().String(), Title: "Review PRs", Status: "Completed"},
		{ID: uuid.New().String(), Title: "Write unit tests", Status: "Pending"},
		{ID: uuid.New().String(), Title: "Prepare sprint planning", Status: "Completed"},
		{ID: uuid.New().String(), Title: "Optimize database queries", Status: "In Progress"},
		{ID: uuid.New().String(), Title: "Deploy latest release", Status: "Completed"},
		{ID: uuid.New().String(), Title: "Update documentation", Status: "Pending"},
		{ID: uuid.New().String(), Title: "Refactor legacy code", Status: "In Progress"},
		{ID: uuid.New().String(), Title: "Conduct user interviews", Status: "Completed"},
	}

	for _, task := range tasks {
		storage.AddTask(task)
	}

	fmt.Println("✅ Dump data added successfully!")
	
}
func main() {
	r := gin.Default()

	// Register routes
	routes.RegisterTaskRoutes(r)

	// Start server
	r.Run(":7777") // Run on port 8080
}
