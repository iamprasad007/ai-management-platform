package repository

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
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

func (r *TaskRepository) GetAll() ([]*model.Task, error) {
    // 1. Execute the search request
    // Passing nil as the body retrieves all documents (match_all)
    res, err := r.es.Search(
        r.es.Search.WithIndex("tasks"),
        r.es.Search.WithContext(context.Background()),
    )
    if err != nil {
        return nil, err
    }
    defer res.Body.Close()

    if res.IsError() {
        return nil, fmt.Errorf("error fetching tasks: %s", res.Status())
    }

    // 2. Define a structure to map the ES response
    var envelope struct {
        Hits struct {
            Hits []struct {
                Source json.RawMessage `json:"_source"`
            } `json:"hits"`
        } `json:"hits"`
    }

    // 3. Decode the response body
    if err := json.NewDecoder(res.Body).Decode(&envelope); err != nil {
        return nil, err
    }

    // 4. Parse the individual hits into your model
    var tasks []*model.Task
    for _, hit := range envelope.Hits.Hits {
        var task model.Task
        if err := json.Unmarshal(hit.Source, &task); err != nil {
            return nil, err
        }
        tasks = append(tasks, &task)
    }

    return tasks, nil
}

func (r *TaskRepository) FindByAssignee(assigneeID string) ([]model.Task, error) {
    // 1. Build the query safely
    query := map[string]interface{}{
        "query": map[string]interface{}{
            "term": map[string]interface{}{
                "assigneeId.keyword": assigneeID,
            },
        },
    }

    var buf bytes.Buffer
    if err := json.NewEncoder(&buf).Encode(query); err != nil {
        return nil, err
    }

    // 2. Execute Search
    res, err := r.es.Search(
        r.es.Search.WithIndex("tasks"),
        r.es.Search.WithBody(&buf),
        r.es.Search.WithTrackTotalHits(true),
        r.es.Search.WithContext(context.Background()),
    )
    if err != nil {
        return nil, err
    }
    defer res.Body.Close()

    if res.IsError() {
        return nil, fmt.Errorf("search error: %s", res.Status())
    }

    // 3. Optimized Decoding (Direct to Struct)
    var envelope struct {
        Hits struct {
            Hits []struct {
                Source model.Task `json:"_source"`
            } `json:"hits"`
        } `json:"hits"`
    }

    if err := json.NewDecoder(res.Body).Decode(&envelope); err != nil {
        return nil, fmt.Errorf("error parsing response: %w", err)
    }

    // 4. Extract results
    tasks := make([]model.Task, 0, len(envelope.Hits.Hits))
    for _, hit := range envelope.Hits.Hits {
        tasks = append(tasks, hit.Source)
    }

    return tasks, nil
}

func (r *TaskRepository) UpdateStatus(id string, status string) error {

	updateBody := fmt.Sprintf(`{
		"doc": {
			"status": "%s",
			"updatedAt": "%s"
		}
	}`, status, time.Now().Format(time.RFC3339))

	_, err := r.es.Update(
		"tasks",
		id,
		strings.NewReader(updateBody),
	)

	return err
}

func (r *TaskRepository) UpdateAssignee(id string, assigneeID string) error {

	updateBody := fmt.Sprintf(`{
		"doc": {
			"assigneeId": "%s",
			"updatedAt": "%s"
		}
	}`, assigneeID, time.Now().Format(time.RFC3339))

	_, err := r.es.Update(
		"tasks",
		id,
		strings.NewReader(updateBody),
	)

	return err
}


