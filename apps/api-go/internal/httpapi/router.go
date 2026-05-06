package httpapi

import (
	"log/slog"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/config"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/pythonworker"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/storage"
)

type Dependencies struct {
	Logger       *slog.Logger
	Store        *storage.Store
	WorkerClient *pythonworker.Client
	Settings     config.Settings
}

func NewRouter(dependencies Dependencies) http.Handler {
	router := chi.NewRouter()
	handler := Handler{dependencies: dependencies}

	router.Get("/health", handler.Health)
	router.Get("/ready", handler.Ready)
	router.Post("/runs", handler.CreateRun)
	router.Get("/runs", handler.ListRuns)
	router.Get("/runs/{run_id}", handler.GetRun)
	router.Get("/runs/{run_id}/state", handler.GetRunState)
	router.Post("/runs/{run_id}/plan", handler.GeneratePlan)
	router.Get("/runs/{run_id}/plans/latest", handler.GetLatestPlan)
	router.Post("/runs/{run_id}/turns/advance", handler.AdvanceTurn)
	router.Get("/runs/{run_id}/events", handler.ListRunEvents)
	router.Get("/runs/{run_id}/turns", handler.ListRunTurns)
	router.Get("/runs/{run_id}/tool-calls", handler.ListRunToolCalls)
	router.Get("/runs/{run_id}/llm-calls", handler.ListRunLLMCalls)

	return router
}
