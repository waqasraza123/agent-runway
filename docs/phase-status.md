# Phase status

## Current platform state

The core execution spine is implemented and release-gated.

Completed areas:

- foundation and toolchain
- API surface
- run state contracts
- planning
- deterministic turn execution
- provider-backed LLM turn execution
- retry and deterministic fallback
- deterministic tool execution
- evidence recording
- approvals
- verification
- final output synthesis
- in-memory storage
- SQL-backed durable persistence
- Alembic schema migrations
- PostgreSQL-ready database URL support
- persisted LLM call artifacts and usage tracking
- fake provider support
- OpenAI-compatible provider support
- hybrid Go control-plane scaffold
- Go-owned run create/list/read endpoints
- Go-owned deterministic and worker-backed LLM planning
- Go-owned deterministic turn advancement
- Go-owned worker-backed LLM turn advancement
- Go-owned artifact list endpoints for events, turns, tool calls, and LLM calls
- Go-owned verification and finalization endpoints
- Go-owned finalization gate for passing verification and pending approvals
- Go-owned approval request, listing, and decision endpoints
- Go-owned opt-in auth/RBAC for workflow endpoints
- Go-owned durable user, tenant, membership, and run ownership records
- Go-owned tenant-scoped run list, read, and mutation checks
- Go-owned structured request logs and Python worker trace propagation
- Go-owned durable request metadata on run events
- Go-owned OTLP/HTTP server span export
- Go-owned tenant-specific provider routing and model policy
- Go-owned provider usage ledger and budget guards
- private Python agent-worker scaffold
- shared worker-boundary contracts
- unit and integration tests for the implemented platform spine
- documentation and release-readiness smoke flows

## Current recommended usage

- use memory mode for fast development
- use SQL mode for durable local validation
- use fake LLM mode for repeatable smoke testing
- use the OpenAI-compatible provider for manual provider-backed validation
- use hybrid mode for early Go control-plane and Python worker development

## Project readiness

This repository is in a strong backend MVP state for:

- demos
- portfolio presentation
- client discussions
- architecture walkthroughs
- further production hardening

## Next practical upgrades

- worker-side spans for provider calls and execution turns
- signed JWT validation for external identity providers
- frontend operator console
