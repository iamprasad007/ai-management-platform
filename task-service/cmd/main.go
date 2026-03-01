package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
	elasticsearch "github.com/elastic/go-elasticsearch/v8"

	"task-service/internal/client"
	"task-service/internal/handler"
	"task-service/internal/repository"
	"task-service/internal/service"
	"task-service/internal/middleware"
)

func main() {

	es, err := elasticsearch.NewClient(elasticsearch.Config{
		Addresses: []string{
			os.Getenv("ELASTICSEARCH_URL"),
		},
	})

	if err != nil {
		log.Fatalf("Error creating ES client: %s", err)
	}

	repo := repository.NewTaskRepository(es)
	userClient := client.NewUserClient()
	service := service.NewTaskService(repo, userClient)
	handler := handler.NewTaskHandler(service)

	r := mux.NewRouter()
	r.HandleFunc("/tasks", handler.CreateTask).Methods("POST")
	r.HandleFunc("/tasks", handler.ListTasks).Methods("GET")
	r.HandleFunc("/tasks/{id}", handler.GetTask).Methods("GET")
	r.HandleFunc("/tasks/{id}", handler.UpdateTask).Methods("PATCH")

	r.Use(middleware.LoggingMiddleware)

	log.Println("Task Service running on :8081")
	log.Fatal(http.ListenAndServe(":8081", r))
}
