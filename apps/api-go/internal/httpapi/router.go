package httpapi

import (
	"log/slog"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/pythonworker"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/storage"
)

type Dependencies struct {
	Logger       *slog.Logger
	Store        *storage.Store
	WorkerClient *pythonworker.Client
}

func NewRouter(dependencies Dependencies) http.Handler {
	router := chi.NewRouter()
	handler := Handler{dependencies: dependencies}

	router.Get("/health", handler.Health)
	router.Get("/ready", handler.Ready)

	return router
}
