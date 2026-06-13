# Scam Guardian — Flutter mobile app (placeholder)

No app code yet. The cross-platform (iOS + Android) app is built with Flutter/Dart and its
API client is **generated** from the backend's OpenAPI contract.

## Generate the client

1. Start the backend (`cd ../backend && python -m app`).
2. Generate the Dart client into `lib/api`:
   ```bash
   npx @openapitools/openapi-generator-cli generate -g dart-dio \
     -i http://localhost:8000/openapi.json -o lib/api
   ```
   (or run `../backend/scripts/gen_clients.sh`)

Generated `*.g.dart` / `*.freezed.dart` files are gitignored; run build_runner after codegen.
