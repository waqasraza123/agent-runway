package httpapi

import (
	"context"
	"encoding/json"
	"net/http"
	"time"
)

type Handler struct {
	dependencies Dependencies
}

func (handler Handler) Health(response http.ResponseWriter, request *http.Request) {
	writeJSON(response, http.StatusOK, map[string]string{"status": "ok"})
}

func (handler Handler) Ready(response http.ResponseWriter, request *http.Request) {
	ctx, cancel := context.WithTimeout(request.Context(), 2*time.Second)
	defer cancel()

	if handler.dependencies.Store != nil {
		if err := handler.dependencies.Store.Ping(ctx); err != nil {
			writeJSON(response, http.StatusServiceUnavailable, map[string]string{
				"status": "database_unavailable",
			})
			return
		}
	}

	if handler.dependencies.WorkerClient != nil {
		if err := handler.dependencies.WorkerClient.Health(ctx); err != nil {
			writeJSON(response, http.StatusServiceUnavailable, map[string]string{
				"status": "worker_unavailable",
			})
			return
		}
	}

	writeJSON(response, http.StatusOK, map[string]string{"status": "ready"})
}

func writeJSON(response http.ResponseWriter, statusCode int, payload any) {
	response.Header().Set("Content-Type", "application/json")
	response.WriteHeader(statusCode)
	_ = json.NewEncoder(response).Encode(payload)
}
