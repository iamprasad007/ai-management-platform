package handler

import (
	"encoding/json"
	"net/http"
	"github.com/gorilla/mux"
	"task-service/internal/model"
	"task-service/internal/service"
)

type TaskHandler struct {
	service *service.TaskService
}

func NewTaskHandler(s *service.TaskService) *TaskHandler {
	return &TaskHandler{service: s}
}


func (h *TaskHandler) CreateTask(w http.ResponseWriter, r *http.Request) {

	var req model.Task
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(model.ErrorResponse{
			Code:    "INVALID_REQUEST",
			Message: "Invalid JSON body",
		})
		return
	}

	task, err := h.service.CreateTask(req)
	if err != nil {

    	w.Header().Set("Content-Type", "application/json")

    	w.WriteHeader(http.StatusBadRequest)

		json.NewEncoder(w).Encode(map[string]string{
			"code":    "UNAUTHORIZED_ACTION",
			"message": err.Error(),
		})

    	return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(task)
}


func (h *TaskHandler) GetTask(w http.ResponseWriter, r *http.Request) {

	id := mux.Vars(r)["id"]

	task, err := h.service.GetTask(id)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	json.NewEncoder(w).Encode(task)
}

func (h *TaskHandler) ListTasks(w http.ResponseWriter, r *http.Request) {

	query := r.URL.Query()

	filter := model.TaskFilter{
		AssigneeID: query.Get("assigneeId"),
		Status:     query.Get("status"),
		Priority:   query.Get("priority"),
		Title:      query.Get("title"),
		DueStart:   query.Get("dueStart"),
		DueEnd:     query.Get("dueEnd"),
	}

	tasks, err := h.service.ListTasksWithFilter(filter)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(tasks)
}


func (h *TaskHandler) UpdateTask(w http.ResponseWriter, r *http.Request) {

	id := mux.Vars(r)["id"]

	var body struct {
		Status     *string `json:"status"`
		Priority   *string `json:"priority"`
		DueDate    *string `json:"dueDate"`
		AssigneeID *string `json:"assigneeId"`
	}

	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{
			"code":    "INVALID_REQUEST",
			"message": "Invalid JSON body",
		})
		return
	}

	updatedTask, err := h.service.UpdateTask(id, body.Status, body.Priority, body.DueDate, body.AssigneeID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{
			"code": "VALIDATION_ERROR",
			"message": err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(updatedTask)
}




