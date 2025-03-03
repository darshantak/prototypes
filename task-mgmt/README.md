# 📝 Task Management System (Microservice)

A simple **Task Management System** built with Go and Gin. This microservice provides CRUD operations for tasks,users along with **pagination** and **filtering**.

---

## 🚀 Features
- Create, Read, Update, Delete tasks/users.
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

1. To start the basic Task CRUD application, navigate to the task-service directory and run the server using go run main.go.

2. Since we are adopting a microservices architecture, I have set up an API Gateway that acts as a reverse proxy. This allows us to run services independently while routing requests through the gateway.

3. For example, I have also included a User Service. We can host user-service separately, and the reverse proxy will handle directing user-related requests accordingly.

### **Cloning and running**
```sh

git clone https://github.com/darshantak/prototypes.git
git checkout design/taskapp
cd task-mgmt```

**Start the Task Service** : 
cd task-service
go run main.go

**Start the User Service** :
cd ../user-service
go run main.go

**Start the API Gateway (Reverse Proxy)**:
cd ../api-gateway
go run main.go

