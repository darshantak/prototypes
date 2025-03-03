package handlers

import (
	"net/http"
	"sync"
	"user-service/models"
	"user-service/storage"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

var mu sync.Mutex

func RegisterUser(c *gin.Context) {
	var user models.User
	if err := c.ShouldBindJSON(&user); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	user.ID = uuid.New().String()
	storage.CreateUser(user)

	c.JSON(http.StatusCreated, gin.H{"message": "User registered successfully", "user": user})
}
func GetAllUsers(c *gin.Context) {
	users := storage.GetAllUsers()

	c.JSON(http.StatusOK, gin.H{"users": users})

}
func GetUser(c *gin.Context) {
	id := c.Param("id")
	user, exists := storage.GetUser(id)

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"user": user})
}

func DeleteUser(c *gin.Context) {
	id := c.Param("id")
	storage.DeleteUser(id)
	c.JSON(http.StatusOK, gin.H{"message": "User deleted successfully"})
}
