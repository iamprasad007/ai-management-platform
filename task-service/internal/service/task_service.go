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

	title, description := normalizeTitleDescription(req.Title, req.Description)

	task := model.Task{
		ID:          uuid.New().String(),
		Title:       title,
		Description: description,
		CreatorID:   req.CreatorID,
		AssigneeID:  req.AssigneeID,
		Status:      StatusTodo,
		Priority:    defaultString(req.Priority, PriorityMedium),
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
	normalizeDueFilter(&filter)
	fmt.Printf("dueStart:", filter.DueStart)
	fmt.Printf("dueEnd:", filter.DueEnd)
	return s.repo.Search(filter)
}


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


func normalizeTitleDescription(title, description string) (string, string) {
	title = strings.TrimSpace(title)
	description = strings.TrimSpace(description)

	// Promote description if title missing
	if title == "" && description != "" {
		title = description
		description = ""
	}

	// Remove punctuation at edges
	title = strings.Trim(title, " ,.-")
	description = strings.Trim(description, " ,.-")

	lower := strings.ToLower(title)

	// Remove known filler prefixes
	prefixes := []string{
		"create a task to",
		"create task to",
		"create a task for",
		"create task for",
		"assign a task to",
		"assign task to",
		"add a task to",
		"add task to",
	}

	for _, p := range prefixes {
		if strings.HasPrefix(lower, p) {
			title = strings.TrimSpace(title[len(p):])
			lower = strings.ToLower(title)
			break
		}
	}

	words := strings.Fields(title)

	if len(words) == 0 {
		return "", description
	}

	// Remove command verbs
	verbs := map[string]bool{
		"assign": true,
		"create": true,
		"add":    true,
		"make":   true,
		"build":  true,
	}

	if verbs[strings.ToLower(words[0])] {
		words = words[1:]
	}

	// Remove leading filler words
	for len(words) > 0 {
		w := strings.ToLower(words[0])
		if w == "a" || w == "an" || w == "the" {
			words = words[1:]
		} else {
			break
		}
	}

	// Remove trailing "task" or "tasks"
	if len(words) > 0 {
		last := strings.ToLower(words[len(words)-1])
		if last == "task" || last == "tasks" {
			words = words[:len(words)-1]
		}
	}

	title = strings.Join(words, " ")

	// // Remove duplicated description
	// if strings.EqualFold(title, description) {
	// 	description = ""
	// }

	// Clean description capitalization
	if len(description) > 0 {
		description = strings.TrimSpace(description)
		description = strings.ToUpper(description[:1]) + description[1:]
	}

	// Limit extremely long titles
	words = strings.Fields(title)
	if len(words) > 10 {
		title = strings.Join(words[:10], " ")
	}

	// Capitalize title
	if len(title) > 0 {
		title = strings.ToUpper(title[:1]) + title[1:]
	}

	return title, description
}

func normalizeDueFilter(filter *model.TaskFilter) {

	if filter.DueDate == "" {
		return
	}

	now := time.Now().UTC()

	resolvers := map[string]func() (time.Time, time.Time){

		"today": func() (time.Time, time.Time) {
			start := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.UTC)
			return start, start.Add(24 * time.Hour)
		},

		"tomorrow": func() (time.Time, time.Time) {
			start := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.UTC).
				Add(24 * time.Hour)
			return start, start.Add(24 * time.Hour)
		},

		"this_week": func() (time.Time, time.Time) {
			weekday := int(now.Weekday())
			start := now.AddDate(0, 0, -weekday)
			start = time.Date(start.Year(), start.Month(), start.Day(), 0, 0, 0, 0, time.UTC)
			return start, start.AddDate(0, 0, 7)
		},

		"next_week": func() (time.Time, time.Time) {
			start := now.AddDate(0,0,7)
			return start, start.AddDate(0,0,7)
		},

		"overdue": func() (time.Time, time.Time) {
			return time.Time{}, now
		},
	}

	if resolver, ok := resolvers[strings.ToLower(filter.DueDate)]; ok {

		start, end := resolver()

		if !start.IsZero() {
			filter.DueStart = start.Format(time.RFC3339)
		}

		if !end.IsZero() {
			filter.DueEnd = end.Format(time.RFC3339)
		}
	}
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


func defaultString(val, fallback string) string {
    if val == "" {
        return fallback
    }
    return val
}