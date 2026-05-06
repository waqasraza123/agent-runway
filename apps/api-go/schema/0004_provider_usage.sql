create table provider_usage_records (
    usage_id varchar(64) primary key,
    tenant_id varchar(64) not null references tenants (tenant_id),
    run_id varchar(64) not null references run_states (run_id),
    operation varchar(32) not null,
    provider_name varchar(64) not null,
    model_name varchar(128) not null,
    input_tokens integer not null default 0,
    output_tokens integer not null default 0,
    total_tokens integer not null default 0,
    estimated_cost_usd numeric(18, 8),
    created_at timestamptz not null,
    payload text not null
);

create index ix_provider_usage_tenant_created_at
    on provider_usage_records (tenant_id, created_at);
create index ix_provider_usage_run_id on provider_usage_records (run_id);
create index ix_provider_usage_tenant_run_id
    on provider_usage_records (tenant_id, run_id);
create index ix_provider_usage_operation on provider_usage_records (operation);
create index ix_provider_usage_provider_model
    on provider_usage_records (provider_name, model_name);
