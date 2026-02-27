package service

import (
	"fmt"
	"time"

	"github.com/google/uuid"

	"task-service/internal/client"
	"task-service/internal/model"
	"task-service/internal/repository"
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

func (s *TaskService) ListTasks() ([]model.Task, error) {
	tasks, err := s.repo.GetAll()
	if err != nil {
		return nil, err
	}

	var result []model.Task
	for _, task := range tasks {
		result = append(result, *task)
	}
	return result, nil
}

func (s *TaskService) ListByAssignee(assigneeID string) ([]model.Task, error) {
	return s.repo.FindByAssignee(assigneeID)
}

func (s *TaskService) UpdateStatus(id string, status string) error {

	valid := map[string]bool{
		"TODO":        true,
		"IN_PROGRESS": true,
		"DONE":        true,
	}

	if !valid[status] {
		return fmt.Errorf("invalid status")
	}

	return s.repo.UpdateStatus(id, status)
}

func (s *TaskService) ReassignTask(taskID, newAssigneeID, creatorID string) error {

	// Validate roles via user service
	creator, err := s.userClient.GetUserByID(creatorID)
	if err != nil {
		return err
	}

	assignee, err := s.userClient.GetUserByID(newAssigneeID)
	if err != nil {
		return err
	}

	// Role rules:
	// ADMIN → anyone
	// OWNER → can assign only to MEMBER
	// MEMBER → cannot reassign

	if creator.Role == "MEMBER" {
		return fmt.Errorf("members cannot reassign tasks")
	}

	if creator.Role == "OWNER" && assignee.Role != "MEMBER" {
		return fmt.Errorf("owner can only assign to member")
	}

	return s.repo.UpdateAssignee(taskID, newAssigneeID)
}

