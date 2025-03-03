package utils

import (
	"strconv"

	"github.com/gin-gonic/gin"
)

func Paginate[T any](items []T, c *gin.Context) []T {
	pageSize, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))

	start := (page - 1) * pageSize
	if start > len(items) {
		return []T{}
	}

	end := start + pageSize
	if end > len(items) {
		end = len(items)
	}

	return items[start:end]
}
