# Local Hybrid Runtime

Run the first Go + Python hybrid slice:

```bash
make hybrid-up
```

Services:

- Go control plane: `http://127.0.0.1:8080`
- Python agent worker: `http://127.0.0.1:8090`
- Postgres: `127.0.0.1:5432`

The Go service currently exposes `/health` and `/ready`. The Python worker exposes `/health` and the private `POST /internal/agent/turn` endpoint.
