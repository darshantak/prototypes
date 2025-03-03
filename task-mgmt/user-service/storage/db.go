package storage

import (
	"sync"
	"user-service/models"
)

var (
	users = make(map[string]models.User)
	mu    sync.Mutex
)

func GetAllUsers() []models.User {
	mu.Lock()
	defer mu.Unlock()

	var userList []models.User
	for _, user := range users {
		userList = append(userList, user)
	}
	return userList
}

func GetUser(id string) (models.User, bool) {
	mu.Lock()
	defer mu.Unlock()
	user, exists := users[id]
	return user, exists
}

func CreateUser(user models.User) {
	mu.Lock()
	defer mu.Unlock()
	users[user.ID] = user
}

func DeleteUser(id string) {
	mu.Lock()
	defer mu.Unlock()
	delete(users, id)
}
