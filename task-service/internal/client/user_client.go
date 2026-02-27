package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"task-service/internal/model"
)

type UserClient struct {
	baseURL string
}

func NewUserClient() *UserClient {
	return &UserClient{
		baseURL: os.Getenv("USER_SERVICE_URL"), // http://user-service:8080
	}
}

func (c *UserClient) GetUserByID(userID string) (*model.User, error) {

	url := fmt.Sprintf("%s/users/%s", c.baseURL, userID)

	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("user not found")
	}

	var user model.User
	if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
		return nil, err
	}

	return &user, nil
}
