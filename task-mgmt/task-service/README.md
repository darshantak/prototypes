# 📝 Task Management System (Microservice)

A simple **Task Management System** built with Go and Gin. This microservice provides CRUD operations for tasks, along with **pagination** and **filtering**.

---

## 🚀 Features
- Create, Read, Update, Delete tasks.
- Pagination support for `GET /tasks`.
- Filtering tasks by status.
- RESTful API using **Gin**.
- In-memory database (**for now**).
- Easily extendable for future microservices (e.g., **User Service**).

---

## 🏗️ Tech Stack
- **Golang** (with Gin framework)
- **In-memory storage** (for simplicity)
- **REST-based microservices**

---

## 🔧 Installation & Running

### **1️⃣ Clone and Run**
```sh
git clone https://github.com/darshantak/prototypes.git
git checkout design/taskapp
cd task-mgmt
cd task-service
go run main.go

This will run the Task CRUD Service
