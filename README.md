# Poelis Python SDK

Python SDK for Poelis - explore your data with simple dot notation.

## Installation

```bash
pip install -U poelis-sdk
```

Requires Python 3.11+.

## Quick Start

```python
from poelis_sdk import PoelisClient

# Create client
poelis = PoelisClient(
    api_key="poelis_live_A1B2C3...",    # Get from Organization Settings → API Keys
    org_id="tenant_uci_001",            # Same section
)

# Use the browser for easy exploration
poelis = poelis.browser  # Now you can use dot notation!

# Explore your data
poelis.workspace_name.product_name.item_name
```

## Getting Your Credentials

1. Go to **Organization Settings → API Keys**
2. Click **"Create API key"** (read-only recommended)
3. Copy the key (shown only once) and your `org_id`
4. Store securely as environment variables:

```bash
export POELIS_API_KEY=poelis_live_A1B2C3...
export POELIS_ORG_ID=tenant_uci_001
```

## Browser Usage

The browser lets you navigate your Poelis data with simple dot notation:

```python
# Navigate through your data
poelis = poelis.browser

# List workspaces
poelis.names()  # ['workspace1', 'workspace2', ...]

# Access workspace
ws = poelis.workspace1

# List products in workspace  
ws.names()  # ['product1', 'product2', ...]

# Access product
product = ws.product1

# List items in product
product.names()  # ['item1', 'item2', ...]

# Access item and its properties
item = product.item1
item_value = item.some_property.value  # Access property values directly
item_category = item.some_property.category  # Access property categories directly

```

## IDE Compatibility & Autocomplete

The Poelis SDK works in all Python environments, but autocomplete behavior varies by IDE:

### ✅ VS Code (Recommended for Notebooks)
- **Autocomplete**: Works perfectly with dynamic attributes
- **Setup**: No configuration needed
- **Experience**: Full autocomplete at all levels

### ⚠️ PyCharm (Jupyter Notebooks)
- **Autocomplete**: Limited - PyCharm uses static analysis and doesn't see dynamic attributes
- **Code execution**: Works perfectly (attributes are real and functional)
- **Workaround**: Call `names()` at each level to prime autocomplete

## Examples

See `notebooks/try_poelis_sdk.ipynb` for complete examples including authentication, data exploration, and search queries.

## Requirements

- Python >= 3.11
- API base URL reachable from your environment

## License

MIT
