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

// func (h *TaskHandler) CreateTask(w http.ResponseWriter, r *http.Request) {

// 	var req model.Task
// 	err := json.NewDecoder(r.Body).Decode(&req)
// 	if err != nil {
// 		http.Error(w, err.Error(), http.StatusBadRequest)
// 		return
// 	}

// 	task, err := h.service.CreateTask(req)
// 	if err != nil {
//     	http.Error(w, err.Error(), http.StatusBadRequest)
//     	return
// 	}

// 	w.Header().Set("Content-Type", "application/json")
// 	w.WriteHeader(http.StatusCreated)
// 	json.NewEncoder(w).Encode(task)
// }

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
			"code":    "BUSINESS_RULE_VIOLATION",
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
	tasks, err := h.service.ListTasks()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(tasks)
}


func (h *TaskHandler) ListTasksByAssignee(w http.ResponseWriter, r *http.Request) {
    // 1. Extract from Path instead of Query
    vars := mux.Vars(r)
    assigneeID := vars["assigneeId"]

    // 2. Validation
    if assigneeID == "" {
        http.Error(w, "assigneeId is required in path", http.StatusBadRequest)
        return
    }

    // 3. Call Service 
    tasks, err := h.service.ListByAssignee(assigneeID)
    if err != nil {
        http.Error(w, "Internal Server Error", http.StatusInternalServerError)
        return
    }

    // 4. Response
    w.Header().Set("Content-Type", "application/json")
    if err := json.NewEncoder(w).Encode(tasks); err != nil {
        http.Error(w, "Encoding Error", http.StatusInternalServerError)
    }
}


func (h *TaskHandler) UpdateStatus(w http.ResponseWriter, r *http.Request) {

	id := mux.Vars(r)["id"]

	var body struct {
		Status string `json:"status"`
	}

	json.NewDecoder(r.Body).Decode(&body)

	err := h.service.UpdateStatus(id, body.Status)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func (h *TaskHandler) ReassignTask(w http.ResponseWriter, r *http.Request) {

	id := mux.Vars(r)["id"]

	var body struct {
		NewAssigneeID string `json:"newAssigneeId"`
		CreatorID     string `json:"creatorId"`
	}

	json.NewDecoder(r.Body).Decode(&body)

	err := h.service.ReassignTask(id, body.NewAssigneeID, body.CreatorID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusForbidden)
		return
	}

	w.WriteHeader(http.StatusOK)
}

