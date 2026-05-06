package storage

import (
	"context"
	"encoding/json"

	"github.com/waqasraza123/agent-runway/apps/api-go/internal/domain"
)

func (store *Store) SavePlanAndRunState(
	ctx context.Context,
	plan domain.RunPlanReport,
	runState domain.RunStateSnapshot,
	events []domain.RunEventRecord,
	providerUsage *domain.ProviderUsageRecord,
) (domain.RunPlanReport, error) {
	payload, err := json.Marshal(plan)
	if err != nil {
		return domain.RunPlanReport{}, err
	}

	tx, err := store.pool.Begin(ctx)
	if err != nil {
		return domain.RunPlanReport{}, err
	}
	defer func() {
		_ = tx.Rollback(ctx)
	}()

	_, err = tx.Exec(
		ctx,
		`insert into run_plans (
			plan_id,
			run_id,
			created_at,
			payload
		) values ($1, $2, $3, $4)`,
		plan.PlanID,
		plan.RunID,
		plan.CreatedAt,
		string(payload),
	)
	if err != nil {
		return domain.RunPlanReport{}, err
	}

	if err := updateRunStateInTx(ctx, tx, runState); err != nil {
		return domain.RunPlanReport{}, err
	}
	for _, eventRecord := range events {
		if err := appendEventInTx(ctx, tx, eventRecord); err != nil {
			return domain.RunPlanReport{}, err
		}
	}
	if providerUsage != nil {
		if err := insertProviderUsageInTx(ctx, tx, *providerUsage); err != nil {
			return domain.RunPlanReport{}, err
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return domain.RunPlanReport{}, err
	}
	return plan, nil
}

func (store *Store) GetLatestRunPlan(
	ctx context.Context,
	runID string,
) (domain.RunPlanReport, error) {
	var payload string
	err := store.pool.QueryRow(
		ctx,
		`select payload
		from run_plans
		where run_id = $1
		order by created_at desc, plan_id desc
		limit 1`,
		runID,
	).Scan(&payload)
	if err != nil {
		return domain.RunPlanReport{}, err
	}

	var plan domain.RunPlanReport
	if err := json.Unmarshal([]byte(payload), &plan); err != nil {
		return domain.RunPlanReport{}, err
	}
	return plan, nil
}

func (store *Store) SaveTurnAdvance(
	ctx context.Context,
	runState domain.RunStateSnapshot,
	turn domain.RunTurnRecord,
	toolCalls []domain.RunToolCallRecord,
	llmCalls []domain.LLMCallRecord,
	providerUsage []domain.ProviderUsageRecord,
	events []domain.RunEventRecord,
) (domain.RunTurnRecord, domain.RunStateSnapshot, error) {
	tx, err := store.pool.Begin(ctx)
	if err != nil {
		return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
	}
	defer func() {
		_ = tx.Rollback(ctx)
	}()

	if err := updateRunStateInTx(ctx, tx, runState); err != nil {
		return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
	}

	for _, toolCall := range toolCalls {
		payload, err := json.Marshal(toolCall)
		if err != nil {
			return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
		}
		_, err = tx.Exec(
			ctx,
			`insert into run_tool_calls (
				tool_call_id,
				run_id,
				turn_id,
				task_id,
				created_at,
				payload
			) values ($1, $2, $3, $4, $5, $6)`,
			toolCall.ToolCallID,
			toolCall.RunID,
			toolCall.TurnID,
			toolCall.TaskID,
			toolCall.CreatedAt,
			string(payload),
		)
		if err != nil {
			return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
		}
	}

	for _, llmCall := range llmCalls {
		payload, err := json.Marshal(llmCall)
		if err != nil {
			return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
		}
		_, err = tx.Exec(
			ctx,
			`insert into run_llm_calls (
				llm_call_id,
				run_id,
				turn_id,
				task_id,
				provider_name,
				created_at,
				payload
			) values ($1, $2, $3, $4, $5, $6, $7)`,
			llmCall.LLMCallID,
			llmCall.RunID,
			llmCall.TurnID,
			llmCall.TaskID,
			llmCall.ProviderName,
			llmCall.CreatedAt,
			string(payload),
		)
		if err != nil {
			return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
		}
	}

	turnPayload, err := json.Marshal(turn)
	if err != nil {
		return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
	}
	_, err = tx.Exec(
		ctx,
		`insert into run_turns (
			turn_id,
			run_id,
			task_id,
			created_at,
			payload
		) values ($1, $2, $3, $4, $5)`,
		turn.TurnID,
		turn.RunID,
		turn.TaskID,
		turn.CreatedAt,
		string(turnPayload),
	)
	if err != nil {
		return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
	}

	for _, eventRecord := range events {
		if err := appendEventInTx(ctx, tx, eventRecord); err != nil {
			return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
		}
	}
	for _, usage := range providerUsage {
		if err := insertProviderUsageInTx(ctx, tx, usage); err != nil {
			return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return domain.RunTurnRecord{}, domain.RunStateSnapshot{}, err
	}
	return turn, runState, nil
}
