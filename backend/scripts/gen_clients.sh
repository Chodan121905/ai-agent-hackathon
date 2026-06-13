#!/usr/bin/env bash
# Generate the web (TS) and Flutter (Dart) clients from the live OpenAPI contract.
# Run the backend first:  python -m app   (so http://localhost:8000/openapi.json is up)
set -euo pipefail

OPENAPI_URL="${OPENAPI_URL:-http://localhost:8000/openapi.json}"

echo "→ Web (React/TS) client via Hey API"
npx --yes @hey-api/openapi-ts -i "$OPENAPI_URL" -o ../frontend/src/client

echo "→ Flutter (Dart) client via openapi-generator (dart-dio)"
npx --yes @openapitools/openapi-generator-cli generate -g dart-dio -i "$OPENAPI_URL" -o ../mobile/lib/api

echo "✓ Clients generated."
