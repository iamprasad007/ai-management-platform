package repository

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"time"
	"task-service/internal/model"

	elasticsearch "github.com/elastic/go-elasticsearch/v8"
)

type TaskRepository struct {
	es *elasticsearch.Client
}

func NewTaskRepository(es *elasticsearch.Client) *TaskRepository {
	return &TaskRepository{es: es}
}

func (r *TaskRepository) Create(task model.Task) error {
	fmt.Println("Creating task in ES")

	data, _ := json.Marshal(task)

	_, err := r.es.Index(
		"tasks",
		bytes.NewReader(data),
		r.es.Index.WithDocumentID(task.ID),
		r.es.Index.WithContext(context.Background()),
	)

	return err
}

func (r *TaskRepository) GetByID(id string) (*model.Task, error) {

	res, err := r.es.Get("tasks", id)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()

	if res.IsError() {
		return nil, fmt.Errorf("task not found")
	}

	var result map[string]interface{}
	if err := json.NewDecoder(res.Body).Decode(&result); err != nil {
		return nil, err
	}

	source := result["_source"]
	data, _ := json.Marshal(source)

	var task model.Task
	json.Unmarshal(data, &task)

	return &task, nil
}

func (r *TaskRepository) Search(filter model.TaskFilter) ([]model.Task, error) {

	must := []map[string]interface{}{}

	if filter.AssigneeID != "" {
		must = append(must, map[string]interface{}{
			"term": map[string]interface{}{
				"assigneeId.keyword": filter.AssigneeID,
			},
		})
	}

	if filter.Status != "" {
		must = append(must, map[string]interface{}{
			"term": map[string]interface{}{
				"status.keyword": filter.Status,
			},
		})
	}

	if filter.Priority != "" {
		must = append(must, map[string]interface{}{
			"term": map[string]interface{}{
				"priority.keyword": filter.Priority,
			},
		})
	}

	if filter.DueDate != "" {

		t, err := time.Parse(time.RFC3339, filter.DueDate)
		if err == nil {

			start := time.Date(t.Year(), t.Month(), t.Day(), 0, 0, 0, 0, time.UTC)
			end := start.Add(24 * time.Hour)

			must = append(must, map[string]interface{}{
				"range": map[string]interface{}{
					"dueDate": map[string]interface{}{
						"gte": start.Format(time.RFC3339),
						"lt":  end.Format(time.RFC3339),
					},
				},
			})
		}
	}

	if filter.DueStart != "" || filter.DueEnd != "" {

		rangeQuery := map[string]interface{}{
			"range": map[string]interface{}{
				"dueDate": map[string]interface{}{},
			},
		}

		if filter.DueStart != "" {
			rangeQuery["range"].(map[string]interface{})["dueDate"].(map[string]interface{})["gte"] = filter.DueStart
		}

		if filter.DueEnd != "" {
			rangeQuery["range"].(map[string]interface{})["dueDate"].(map[string]interface{})["lt"] = filter.DueEnd
		}

		must = append(must, rangeQuery)
	}

	if filter.Title != "" {
		must = append(must, map[string]interface{}{
			"multi_match": map[string]interface{}{
				"query":     filter.Title,
				"fields":    []string{"title^3", "description"},
				"fuzziness": "AUTO",
			},
		})
	}

	var query map[string]interface{}

	if len(must) == 0 {
		query = map[string]interface{}{
			"query": map[string]interface{}{
				"match_all": map[string]interface{}{},
			},
		}
	} else {
		query = map[string]interface{}{
			"query": map[string]interface{}{
				"bool": map[string]interface{}{
					"must": must,
				},
			},
		}
	}

	var buf bytes.Buffer
	json.NewEncoder(&buf).Encode(query)

	res, err := r.es.Search(
		r.es.Search.WithIndex("tasks"),
		r.es.Search.WithBody(&buf),
		r.es.Search.WithSize(100),
		r.es.Search.WithSort("createdAt:desc"),
	)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()

	var envelope struct {
		Hits struct {
			Hits []struct {
				Source model.Task `json:"_source"`
			} `json:"hits"`
		} `json:"hits"`
	}

	json.NewDecoder(res.Body).Decode(&envelope)

	var tasks []model.Task
	for _, hit := range envelope.Hits.Hits {
		tasks = append(tasks, hit.Source)
	}

	return tasks, nil
}

func (r *TaskRepository) GenericUpdate(id string, fields map[string]interface{}) error {

	body := map[string]interface{}{
		"doc": fields,
	}

	data, _ := json.Marshal(body)

	_, err := r.es.Update(
		"tasks",
		id,
		bytes.NewReader(data),
	)

	return err
}