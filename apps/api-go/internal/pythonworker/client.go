package pythonworker

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/waqasraza123/agent-runway/apps/api-go/internal/contracts"
)

type Client struct {
	baseURL    string
	token      string
	httpClient *http.Client
}

func NewClient(baseURL string, token string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		token:   token,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (client *Client) Health(ctx context.Context) error {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, client.baseURL+"/health", nil)
	if err != nil {
		return err
	}
	response, err := client.httpClient.Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		return fmt.Errorf("agent worker health returned status %d", response.StatusCode)
	}
	return nil
}

func (client *Client) ExecuteTurn(
	ctx context.Context,
	turnRequest contracts.LLMWorkerTurnRequest,
) (contracts.LLMExecutionOutcome, error) {
	var outcome contracts.LLMExecutionOutcome
	body, err := json.Marshal(turnRequest)
	if err != nil {
		return outcome, err
	}

	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		client.baseURL+"/internal/agent/turn",
		bytes.NewReader(body),
	)
	if err != nil {
		return outcome, err
	}
	request.Header.Set("Content-Type", "application/json")
	if client.token != "" {
		request.Header.Set("Authorization", "Bearer "+client.token)
	}

	response, err := client.httpClient.Do(request)
	if err != nil {
		return outcome, err
	}
	defer response.Body.Close()

	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		return outcome, fmt.Errorf("agent worker returned status %d", response.StatusCode)
	}
	if err := json.NewDecoder(response.Body).Decode(&outcome); err != nil {
		return outcome, err
	}
	return outcome, nil
}
