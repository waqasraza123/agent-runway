package storage

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/waqasraza123/agent-runway/apps/api-go/internal/domain"
)

type ArtifactListQuery struct {
	Limit  int
	Offset int
}

func (store *Store) ListRunEvents(
	ctx context.Context,
	runID string,
	query ArtifactListQuery,
) ([]domain.RunEventRecord, domain.PageInfo, error) {
	totalCount, err := store.countByRunID(ctx, "run_events", runID)
	if err != nil {
		return nil, domain.PageInfo{}, err
	}

	rows, err := store.pool.Query(
		ctx,
		`select payload
		from run_events
		where run_id = $1
		order by occurred_at desc, event_id desc
		limit $2 offset $3`,
		runID,
		query.Limit,
		query.Offset,
	)
	if err != nil {
		return nil, domain.PageInfo{}, err
	}
	defer rows.Close()

	items := make([]domain.RunEventRecord, 0)
	for rows.Next() {
		var payload string
		if err := rows.Scan(&payload); err != nil {
			return nil, domain.PageInfo{}, err
		}
		var item domain.RunEventRecord
		if err := json.Unmarshal([]byte(payload), &item); err != nil {
			return nil, domain.PageInfo{}, err
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, domain.PageInfo{}, err
	}

	return items, buildPageInfo(query, totalCount), nil
}

func (store *Store) ListRunTurns(
	ctx context.Context,
	runID string,
	query ArtifactListQuery,
) ([]domain.RunTurnRecord, domain.PageInfo, error) {
	totalCount, err := store.countByRunID(ctx, "run_turns", runID)
	if err != nil {
		return nil, domain.PageInfo{}, err
	}

	rows, err := store.pool.Query(
		ctx,
		`select payload
		from run_turns
		where run_id = $1
		order by created_at desc, turn_id desc
		limit $2 offset $3`,
		runID,
		query.Limit,
		query.Offset,
	)
	if err != nil {
		return nil, domain.PageInfo{}, err
	}
	defer rows.Close()

	items := make([]domain.RunTurnRecord, 0)
	for rows.Next() {
		var payload string
		if err := rows.Scan(&payload); err != nil {
			return nil, domain.PageInfo{}, err
		}
		var item domain.RunTurnRecord
		if err := json.Unmarshal([]byte(payload), &item); err != nil {
			return nil, domain.PageInfo{}, err
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, domain.PageInfo{}, err
	}

	return items, buildPageInfo(query, totalCount), nil
}

func (store *Store) ListRunToolCalls(
	ctx context.Context,
	runID string,
	query ArtifactListQuery,
) ([]domain.RunToolCallRecord, domain.PageInfo, error) {
	totalCount, err := store.countByRunID(ctx, "run_tool_calls", runID)
	if err != nil {
		return nil, domain.PageInfo{}, err
	}

	rows, err := store.pool.Query(
		ctx,
		`select payload
		from run_tool_calls
		where run_id = $1
		order by created_at desc, tool_call_id desc
		limit $2 offset $3`,
		runID,
		query.Limit,
		query.Offset,
	)
	if err != nil {
		return nil, domain.PageInfo{}, err
	}
	defer rows.Close()

	items := make([]domain.RunToolCallRecord, 0)
	for rows.Next() {
		var payload string
		if err := rows.Scan(&payload); err != nil {
			return nil, domain.PageInfo{}, err
		}
		var item domain.RunToolCallRecord
		if err := json.Unmarshal([]byte(payload), &item); err != nil {
			return nil, domain.PageInfo{}, err
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, domain.PageInfo{}, err
	}

	return items, buildPageInfo(query, totalCount), nil
}

func (store *Store) ListRunLLMCalls(
	ctx context.Context,
	runID string,
	query ArtifactListQuery,
) ([]domain.LLMCallRecord, domain.PageInfo, error) {
	totalCount, err := store.countByRunID(ctx, "run_llm_calls", runID)
	if err != nil {
		return nil, domain.PageInfo{}, err
	}

	rows, err := store.pool.Query(
		ctx,
		`select payload
		from run_llm_calls
		where run_id = $1
		order by created_at desc, llm_call_id desc
		limit $2 offset $3`,
		runID,
		query.Limit,
		query.Offset,
	)
	if err != nil {
		return nil, domain.PageInfo{}, err
	}
	defer rows.Close()

	items := make([]domain.LLMCallRecord, 0)
	for rows.Next() {
		var payload string
		if err := rows.Scan(&payload); err != nil {
			return nil, domain.PageInfo{}, err
		}
		var item domain.LLMCallRecord
		if err := json.Unmarshal([]byte(payload), &item); err != nil {
			return nil, domain.PageInfo{}, err
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, domain.PageInfo{}, err
	}

	return items, buildPageInfo(query, totalCount), nil
}

func (store *Store) countByRunID(ctx context.Context, tableName string, runID string) (int, error) {
	if !allowedArtifactTable(tableName) {
		return 0, errors.New("artifact table is not allowed")
	}
	var totalCount int
	query := fmt.Sprintf("select count(*) from %s where run_id = $1", tableName)
	if err := store.pool.QueryRow(ctx, query, runID).Scan(&totalCount); err != nil {
		return 0, err
	}
	return totalCount, nil
}

func allowedArtifactTable(tableName string) bool {
	switch tableName {
	case "run_events", "run_turns", "run_tool_calls", "run_llm_calls":
		return true
	default:
		return false
	}
}

func buildPageInfo(query ArtifactListQuery, totalCount int) domain.PageInfo {
	return domain.PageInfo{
		Limit:      query.Limit,
		Offset:     query.Offset,
		TotalCount: totalCount,
		HasMore:    query.Offset+query.Limit < totalCount,
	}
}
