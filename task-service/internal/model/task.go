package model

import "time"

type Task struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	Description string    `json:"description"`

	CreatorID   string    `json:"creatorId"`
	AssigneeID  string    `json:"assigneeId"`

	Status      string    `json:"status"`   // TODO | IN_PROGRESS | DONE
	Priority    string    `json:"priority"` // LOW | MEDIUM | HIGH

	DueDate     time.Time `json:"dueDate"`
	CreatedAt   time.Time `json:"createdAt"`
	UpdatedAt   time.Time `json:"updatedAt"`
}
