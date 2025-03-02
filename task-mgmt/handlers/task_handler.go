package handlers

import (
	"net/http"
	"sync"
	"taskapp/models"
	"taskapp/storage"
	"taskapp/utils"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

var mu sync.Mutex

func GetTasks(c *gin.Context) {
	status := c.Query("status") // Filtering by status
	tasks := storage.GetAllTasks()

	// Apply filtering
	filteredTasks := []models.Task{}
	for _, task := range tasks {
		if status == "" || task.Status == status {
			filteredTasks = append(filteredTasks, task)
		}
	}

	// Apply pagination
	paginatedTasks := utils.Paginate(filteredTasks, c)

	c.JSON(http.StatusOK, gin.H{"tasks": paginatedTasks})
}

func CreateTask(c *gin.Context) {
	var task models.Task
	if err := c.ShouldBindJSON(&task); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	task.ID = uuid.New().String()
	storage.AddTask(task)

	c.JSON(http.StatusCreated, gin.H{"message": "Task created", "task": task})
}

func GetTask(c *gin.Context) {
	id := c.Param("id")
	task, exists := storage.GetTaskByID(id)

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "Task not found"})
		return
	}

	c.JSON(http.StatusOK, task)
}

func DeleteTask(c *gin.Context) {
	id := c.Param("id")
	storage.DeleteTask(id)
	c.JSON(http.StatusOK, gin.H{"message": "Task deleted"})
}
