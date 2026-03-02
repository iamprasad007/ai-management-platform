package service

import (
	"fmt"
	"time"
	"strings"

	"github.com/google/uuid"

	"task-service/internal/client"
	"task-service/internal/model"
	"task-service/internal/repository"
)

const (
	StatusTodo       = "TODO"
	StatusInProgress = "IN_PROGRESS"
	StatusCompleted  = "COMPLETED"
)

const (
	PriorityLow    = "LOW"
	PriorityMedium = "MEDIUM"
	PriorityHigh   = "HIGH"
)

type TaskService struct {
	repo       *repository.TaskRepository
	userClient *client.UserClient
}

func NewTaskService(repo *repository.TaskRepository, uc *client.UserClient) *TaskService {
	return &TaskService{
		repo:       repo,
		userClient: uc,
	}
}

func (s *TaskService) CreateTask(req model.Task) (model.Task, error) {

	creator, err := s.userClient.GetUserByID(req.CreatorID)
	if err != nil {
		return model.Task{}, fmt.Errorf("invalid creator")
	}

	assignee, err := s.userClient.GetUserByID(req.AssigneeID)
	if err != nil {
		return model.Task{}, fmt.Errorf("invalid assignee")
	}

	// Role Validation
	switch creator.Role {

	case "ADMIN":
		// can assign to anyone

	case "OWNER":
		if assignee.Role != "MEMBER" {
			return model.Task{}, fmt.Errorf("owner can assign only to member")
		}

	case "MEMBER":
		return model.Task{}, fmt.Errorf("member cannot assign tasks")

	default:
		return model.Task{}, fmt.Errorf("invalid role")
	}

	task := model.Task{
		ID:          uuid.New().String(),
		Title:       req.Title,
		Description: req.Description,
		CreatorID:   req.CreatorID,
		AssigneeID:  req.AssigneeID,
		Status:      "TODO",
		Priority:    req.Priority,
		DueDate:     req.DueDate,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	err = s.repo.Create(task)
	return task, err
}

func (s *TaskService) GetTask(id string) (*model.Task, error) {
	return s.repo.GetByID(id)
}


func (s *TaskService) ListTasksWithFilter(filter model.TaskFilter) ([]model.Task, error) {
	return s.repo.Search(filter)
}

// func (s *TaskService) UpdateTask(
// 	id string,
// 	status *string,
// 	priority *string,
// 	dueDate *string,
// 	assigneeID *string,
// ) (*model.Task, error) {

// 	currentTask, err := s.repo.GetByID(id)
// 	if err != nil {
// 		return nil, err
// 	}

// 	update := make(map[string]interface{})

// 	if status != nil {
// 		normalized, err := normalizeStatus(*status)
// 		if err != nil {
// 			return nil, err
// 		}

// 		if err := validateTransition(currentTask.Status, normalized); err != nil {
// 			return nil, err
// 		}

// 		update["status"] = normalized
// 	}

// 	if priority != nil {
// 		normalized, err := normalizePriority(*priority)
// 		if err != nil {
// 			return nil, err
// 		}
// 		update["priority"] = normalized
// 	}

// 	if dueDate != nil {
// 		parsed, err := time.Parse(time.RFC3339, *dueDate)
// 		if err != nil {
// 			return nil, fmt.Errorf("invalid dueDate format")
// 		}

// 		if parsed.Before(time.Now()) {
// 			return nil, fmt.Errorf("due date cannot be in the past")
// 		}

// 		if currentTask.Status == StatusCompleted {
// 			return nil, fmt.Errorf("cannot modify completed task")
// 		}

// 		update["dueDate"] = parsed
// 	}


// 	if assigneeID != nil {
// 		update["assigneeId"] = *assigneeID
// 	}

// 	if len(update) == 0 {
// 		return nil, fmt.Errorf("no fields to update")
// 	}

// 	update["updatedAt"] = time.Now()

// 	// perform update
// 	currentTask, err := s.repo.GenericUpdate(id, update)
// 	if err != nil {
// 		return nil, err
// 	}

// 	// fetch updated task
// 	updatedTask, err := s.repo.GetByID(id)
// 	if err != nil {
// 		return nil, err
// 	}

// 	return updatedTask, nil
// }

func (s *TaskService) UpdateTask(
	id string,
	status *string,
	priority *string,
	dueDate *string,
	assigneeID *string,
) (*model.Task, error) {

	currentTask, err := s.repo.GetByID(id)
	if err != nil {
		return nil, err
	}

	// Lock completed tasks completely
	if currentTask.Status == StatusCompleted &&
		(status != nil || dueDate != nil || priority != nil || assigneeID != nil) {
		return nil, fmt.Errorf("cannot modify completed task")
	}

	update := make(map[string]interface{})

	if status != nil {
		normalized, err := normalizeStatus(*status)
		if err != nil {
			return nil, err
		}

		if err := validateTransition(currentTask.Status, normalized); err != nil {
			return nil, err
		}

		update["status"] = normalized
	}

	if priority != nil {
		normalized, err := normalizePriority(*priority)
		if err != nil {
			return nil, err
		}
		update["priority"] = normalized
	}

	if dueDate != nil {
		parsed, err := time.Parse(time.RFC3339, *dueDate)
		if err != nil {
			return nil, fmt.Errorf("invalid dueDate format")
		}

		if parsed.Before(time.Now()) {
			return nil, fmt.Errorf("due date cannot be in the past")
		}

		update["dueDate"] = parsed
	}

	if assigneeID != nil {
		update["assigneeId"] = *assigneeID
	}

	if len(update) == 0 {
		return nil, fmt.Errorf("no fields to update")
	}

	update["updatedAt"] = time.Now()

	err = s.repo.GenericUpdate(id, update)
	if err != nil {
		return nil, err
	}

	return s.repo.GetByID(id)
}

func normalizePriority(input string) (string, error) {
	s := strings.ToUpper(strings.TrimSpace(input))

	switch s {
	case PriorityLow, PriorityMedium, PriorityHigh:
		return s, nil
	}

	return "", fmt.Errorf("invalid priority value")
}


func normalizeStatus(input string) (string, error) {
	s := strings.ToLower(strings.TrimSpace(input))

	switch s {
	case "todo", "to do", "pending":
		return StatusTodo, nil
	case "in progress", "inprogress", "working", "started", "in_progress":
		return StatusInProgress, nil
	case "done", "completed", "complete", "finished", "fixed":
		return StatusCompleted, nil
	}

	return "", fmt.Errorf("invalid status value")
}


func validateDueDate(dateStr string, currentStatus string) (time.Time, error) {
	parsed, err := time.Parse(time.RFC3339, dateStr)
	if err != nil {
		return time.Time{}, fmt.Errorf("invalid dueDate format")
	}

	if parsed.Before(time.Now()) {
		return time.Time{}, fmt.Errorf("due date cannot be in the past")
	}

	if currentStatus == StatusCompleted {
		return time.Time{}, fmt.Errorf("cannot modify due date of completed task")
	}

	return parsed, nil
}

func validateTransition(current, next string) error {

	if current == StatusCompleted {
		return fmt.Errorf("cannot change status of completed task")
	}

	if current == StatusTodo && next == StatusInProgress {
		return nil
	}

	if current == StatusTodo && next == StatusCompleted {
		return nil
	}

	if current == StatusInProgress && next == StatusCompleted {
		return nil
	}

	if current == next {
		return nil
	}

	return fmt.Errorf("invalid status transition from %s to %s", current, next)
}


