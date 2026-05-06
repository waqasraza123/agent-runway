package httpapi

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/domain"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/storage"
)

func (handler Handler) ListRunEvents(response http.ResponseWriter, request *http.Request) {
	runID, query, ok := handler.parseArtifactListRequest(response, request)
	if !ok {
		return
	}

	items, page, err := handler.dependencies.Store.ListRunEvents(request.Context(), runID, query)
	if err != nil {
		handler.logError("list run events failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to list run events")
		return
	}

	writeJSON(response, http.StatusOK, domain.RunEventListResponse{Items: items, Page: page})
}

func (handler Handler) ListRunTurns(response http.ResponseWriter, request *http.Request) {
	runID, query, ok := handler.parseArtifactListRequest(response, request)
	if !ok {
		return
	}

	items, page, err := handler.dependencies.Store.ListRunTurns(request.Context(), runID, query)
	if err != nil {
		handler.logError("list run turns failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to list run turns")
		return
	}

	writeJSON(response, http.StatusOK, domain.RunTurnListResponse{Items: items, Page: page})
}

func (handler Handler) ListRunToolCalls(response http.ResponseWriter, request *http.Request) {
	runID, query, ok := handler.parseArtifactListRequest(response, request)
	if !ok {
		return
	}

	items, page, err := handler.dependencies.Store.ListRunToolCalls(request.Context(), runID, query)
	if err != nil {
		handler.logError("list run tool calls failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to list run tool calls")
		return
	}

	writeJSON(response, http.StatusOK, domain.RunToolCallListResponse{Items: items, Page: page})
}

func (handler Handler) ListRunLLMCalls(response http.ResponseWriter, request *http.Request) {
	runID, query, ok := handler.parseArtifactListRequest(response, request)
	if !ok {
		return
	}

	items, page, err := handler.dependencies.Store.ListRunLLMCalls(request.Context(), runID, query)
	if err != nil {
		handler.logError("list run LLM calls failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to list run LLM calls")
		return
	}

	writeJSON(response, http.StatusOK, domain.LLMCallListResponse{Items: items, Page: page})
}

func (handler Handler) parseArtifactListRequest(
	response http.ResponseWriter,
	request *http.Request,
) (string, storage.ArtifactListQuery, bool) {
	if _, ok := handler.getRunState(response, request); !ok {
		return "", storage.ArtifactListQuery{}, false
	}

	values := request.URL.Query()
	limit, ok := parseBoundedIntQuery(response, values.Get("limit"), 20, 1, 100, "limit")
	if !ok {
		return "", storage.ArtifactListQuery{}, false
	}
	offset, ok := parseBoundedIntQuery(response, values.Get("offset"), 0, 0, 0, "offset")
	if !ok {
		return "", storage.ArtifactListQuery{}, false
	}

	return chi.URLParam(request, "run_id"), storage.ArtifactListQuery{
		Limit:  limit,
		Offset: offset,
	}, true
}

