package storage

import (
	"context"
	"encoding/json"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/domain"
)

func (store *Store) SumProviderUsage(
	ctx context.Context,
	tenantID string,
	runID *string,
	since time.Time,
) (float64, error) {
	var total float64
	err := store.pool.QueryRow(
		ctx,
		`select coalesce(sum(estimated_cost_usd), 0)::float8
		from provider_usage_records
		where tenant_id = $1
			and ($2::text is null or run_id = $2)
			and ($3::timestamptz is null or created_at >= $3)`,
		tenantID,
		runID,
		nullableTime(since),
	).Scan(&total)
	return total, err
}

func insertProviderUsageInTx(
	ctx context.Context,
	tx pgx.Tx,
	usage domain.ProviderUsageRecord,
) error {
	payload, err := json.Marshal(usage)
	if err != nil {
		return err
	}
	_, err = tx.Exec(
		ctx,
		`insert into provider_usage_records (
			usage_id,
			tenant_id,
			run_id,
			operation,
			provider_name,
			model_name,
			input_tokens,
			output_tokens,
			total_tokens,
			estimated_cost_usd,
			created_at,
			payload
		) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
		usage.UsageID,
		usage.TenantID,
		usage.RunID,
		string(usage.Operation),
		usage.ProviderName,
		usage.ModelName,
		usage.InputTokens,
		usage.OutputTokens,
		usage.TotalTokens,
		usage.EstimatedCostUSD,
		usage.CreatedAt,
		string(payload),
	)
	return err
}

func nullableTime(value time.Time) *time.Time {
	if value.IsZero() {
		return nil
	}
	return &value
}
