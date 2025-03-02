package storage

import (
	"sync"
	"taskapp/models"
)

var (
	TaskDB = make(map[string]models.Task)
	mu     sync.Mutex
)

func AddTask(task models.Task) {
	mu.Lock()
	defer mu.Unlock()
	TaskDB[task.ID] = task
}

func GetAllTasks() []models.Task {
	mu.Lock()
	defer mu.Unlock()

	tasks := make([]models.Task, 0, len(TaskDB))
	for _, task := range TaskDB {
		tasks = append(tasks, task)
	}
	return tasks
}

func GetTaskByID(id string) (models.Task, bool) {
	mu.Lock()
	defer mu.Unlock()
	task, exists := TaskDB[id]
	return task, exists
}

func DeleteTask(id string) {
	mu.Lock()
	defer mu.Unlock()
	delete(TaskDB, id)
}

