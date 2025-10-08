# Poelis Python SDK

Python SDK for Poelis.

## Installation

```bash
pip install -U poelis-sdk
```

Requires Python 3.11+.

## Quickstart (API key + org ID)

```python
from poelis_sdk import PoelisClient

client = PoelisClient(
    api_key="poelis_live_A1B2C3...",    # Organization Settings → API Keys
    org_id="tenant_uci_001",            # same section
)

# Workspaces → Products
workspaces = client.workspaces.list(limit=10, offset=0)
ws_id = workspaces[0]["id"]

page = client.products.list_by_workspace(workspace_id=ws_id, limit=10, offset=0)
print([p.name for p in page.data])

# Items for a product
pid = page.data[0].id
items = client.items.list_by_product(product_id=pid, limit=10, offset=0)
print([i.get("name") for i in items])

# Property search
props = client.search.properties(q="*", workspace_id=ws_id, limit=10, offset=0)
print(props["total"], len(props["hits"]))
```

## Configuration

### Getting your API key and org ID

1. Navigate to Organization Settings → API Keys.
2. Click “Create API key”, choose a name and scopes (read-only by default recommended).
3. Copy the full key when shown (it will be visible only once). Keep it secret.
4. The `org_id` for your organization is displayed in the same section.
5. You can rotate or revoke keys anytime. Prefer storing as env vars:

```bash
export POELIS_API_KEY=poelis_live_A1B2C3...
export POELIS_ORG_ID=tenant_id_001
# POELIS_BASE_URL is optional - defaults to the managed GCP endpoint
```


## Dot-path browser (Notebook UX)

The SDK exposes a dot-path browser for easy exploration:

```python
client.browser  # then use TAB to explore
# client.browser.<workspace>.<product>.<item>.<child>.properties
```

See the example notebook in `notebooks/try_poelis_sdk.ipynb` for an end-to-end walkthrough (authentication, listing workspaces/products/items, and simple search queries).

## Requirements

- Python >= 3.11
- API base URL reachable from your environment

## License

MIT
