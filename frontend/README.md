# Scam Guardian — Web frontend (placeholder)

No app code yet. The web app (React/TS) will be **generated** from the backend's OpenAPI
contract, so it stays in sync with the single source of truth.

## Generate the client

1. Start the backend so the contract is live:
   ```bash
   cd ../backend && python -m app      # serves http://localhost:8000/openapi.json
   ```
2. Generate the typed client into `src/client`:
   ```bash
   npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o src/client
   ```
   (or run `../backend/scripts/gen_clients.sh`)

The core call is `POST /api/v1/check` → returns a `Verdict`. The trends dashboard reads
`GET /api/v1/intelligence/trends`.
