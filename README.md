# Poelis Python SDK

GraphQL-first Python SDK for Poelis with a focus on great developer experience.

## Quickstart (API key + org ID)

```python
from poelis_sdk import PoelisClient

client = PoelisClient(
    api_key="poelis_live_A1B2C3...",    # Organization Settings → API Keys
    org_id="tenant_uci_001",            # same section
    # base_url defaults to https://api.poelis.ai
)

# Workspaces → Products (GraphQL)
workspaces = client.workspaces.list(limit=10, offset=0)
ws_id = workspaces[0]["id"]

page = client.products.list_by_workspace(workspace_id=ws_id, limit=10, offset=0)
print([p.name for p in page.data])

# Items for a product (GraphQL)
pid = page.data[0].id
items = client.items.list_by_product(product_id=pid, limit=10, offset=0)
print([i.get("name") for i in items])

# Property search (GraphQL)
props = client.search.properties(q="*", workspace_id=ws_id, limit=10, offset=0)
print(props["total"], len(props["hits"]))
```

## Configuration

### Base URL

The SDK defaults to the production API (`https://api.poelis.ai`). You can override this for different environments:

- Local development: `base_url="http://localhost:8000"`
- Staging (example): `base_url="https://api.staging.poelis.ai"`
- Production (default): No need to specify, uses `https://api.poelis.ai`

Confirm the exact URLs for your environments.

Note: Multi-tenancy uses `org_id` for scoping. When using API keys, the SDK sets `X-Poelis-Org` automatically from `org_id`.

### Getting your API key and org ID

1. Navigate to Organization Settings → API Keys.
2. Click “Create API key”, choose a name and scopes (read-only by default recommended).
3. Copy the full key when shown (it will be visible only once). Keep it secret.
4. The `org_id` for your organization is displayed in the same section.
5. You can rotate or revoke keys anytime. Prefer storing as env vars:

```bash
export POELIS_API_KEY=poelis_live_A1B2C3...
export POELIS_ORG_ID=tenant_uci_001
# POELIS_BASE_URL is optional - defaults to https://api.poelis.ai
```


## Dot-path browser (Notebook UX)

The SDK exposes a dot-path browser for easy exploration:

```python
client.browser  # then use TAB to explore
# client.browser.<workspace>.<product>.<item>.<child>.properties
```

- Lazy-loaded via GraphQL on-demand.
- Autocomplete-friendly in Jupyter/VSCode.

## Requirements

- Python >= 3.11
- API base URL reachable from your environment

## License

Apache-2.0
