create table run_states (
    run_id varchar(64) primary key,
    workflow_type varchar(64) not null,
    status varchar(64) not null,
    created_at timestamptz not null,
    updated_at timestamptz not null,
    payload text not null
);

create index ix_run_states_created_at on run_states (created_at);
create index ix_run_states_status on run_states (status);
create index ix_run_states_updated_at on run_states (updated_at);
create index ix_run_states_workflow_type on run_states (workflow_type);
