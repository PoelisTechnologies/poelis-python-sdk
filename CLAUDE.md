<!-- AUTO-GENERATED — do not edit manually. Source: .cursor/rules/*.mdc -->
<!-- Regenerate: python3 scripts/sync_claude_rules.py -->

# Claude Code Rules

> Auto-generated from `.cursor/rules/`. Edit the `.mdc` source files — **not this file**.

## Always-Apply Rules

These rules apply to **every** task in this project.

### Sdk Endpoints

_Use when adding or calling a Poelis API from the Python SDK. GraphQL and the web app storage upload are in bounds. The public REST API is not._

# SDK endpoints

The Python SDK authenticates with an SDK API key. Send it as `Authorization: Bearer <key>`. Do not send `X-API-Key` or `X-Poelis-Api-Key`. `PoelisClient.from_env` reads `POELIS_API_KEY`. That value is an SDK key. It is not a public API key.

## Do not call the public REST API

Do not add a client for `/v1/public/*`. Those routes accept only a public API key and reject the SDK key. The SDK does not call them. A new feature does not start there.

## How to add a call

Look at the web app first, then at the GraphQL operations already under `src/poelis_sdk/`.

1. Prefer GraphQL. Add a method on a resource client next to `ItemsClient` and `ProductsClient`. The method builds a document and calls `Transport.graphql`, which POSTs JSON to `/v1/graphql`. Attach the client on `PoelisClient`. Return a Pydantic model from `models.py` when the response has a stable shape. Return a dict only when the neighboring client already does.
2. Call an internal REST route only when the web app already uses that route for the same action and the route accepts an SDK key (`verify_sdk_or_jwt_dependency` in the backend). File bytes are that case. Follow `POST /v1/storage/uploads/signed-put`, PUT the bytes to the signed URL, then `POST /v1/storage/uploads/complete`. Do not POST the file to `/v1/public/files/{target_id}`.
3. Do not send the API key to the storage host. Copy the signed URL required headers and drop `Authorization`.
4. Check the same limits the web app checks before the request. A document upload uses `DOCUMENT_MAX_FILE_SIZE_BYTES`, which is 5 GiB (`5 * 1024 * 1024 * 1024`). Refuse an empty file locally. Leave organization quota and duplicate detection to the server.
5. `Transport._request` sets `Content-Type: application/json` and retries HTTP 429. A call that must not be repeated, including upload, passes `retry=False`. A body that is not JSON needs its own transport method.

## Tests

Drive the new method through `PoelisClient` with an `httpx` mock transport. Assert the path, the body the server receives, and the error the caller sees. Do not assert private helper calls.
