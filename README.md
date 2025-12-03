# Poelis Python SDK

Python SDK for Poelis - explore your data with simple dot notation.

## IDE Compatibility & Autocomplete

The Poelis SDK works in all Python environments, but autocomplete behavior varies by IDE:

### ✅ VS Code (Recommended for Notebooks)
- **Autocomplete**: Works perfectly with dynamic attributes
- **Setup**: No configuration needed
- **Experience**: Full autocomplete at all levels

### ⚠️ PyCharm (Jupyter Notebooks)
- **Autocomplete**: Limited - PyCharm uses static analysis and doesn't see dynamic attributes
- **Code execution**: Works perfectly (attributes are real and functional)
- **Workaround**: Call the relevant `list_*().names` at each level to prime autocomplete

## Examples

See `notebooks/try_poelis_sdk.ipynb` for complete examples including authentication, data exploration, and search queries.

## Installation

- Python >= 3.11
- API base URL reachable from your environment

```bash
pip install -U poelis-sdk
```

## Quick Start

1. Go to **Organization Settings → API Keys**
2. Click **\"Create API key\"**
3. Copy the key (shown only once) and store it securely, for example as an environment variable:

```python
from poelis_sdk import PoelisClient

# Create client
poelis_client = PoelisClient(
    api_key="poelis_live_A1B2C3...",    # Get from Organization Settings → API Keys
)
```

## Browser Usage

The browser lets you navigate your Poelis data with simple dot notation:

```python
# Navigate through your data
poelis = poelis_client.browser

# List workspaces
poelis.list_workspaces().names  # ['workspace1', 'workspace2', ...]

# Access workspace
ws = poelis.workspace1

# List products in workspace  
ws.list_products().names  # ['product1', 'product2', ...]

# Access product
product = ws.product1

# List items in product
product.list_items().names  # ['item1', 'item2', ...]

# Access item and its properties
item = product.item1

# List children by type for more control
item.list_items().names       # ['child_item1', 'child_item2'] - only child items
item.list_properties().names  # ['Color', 'Weight', ...] - only properties

# Access property values directly
item_value = item.some_property.value  # Access property values directly
item_category = item.some_property.category  # Access property categories directly
item_unit = item.some_property.unit  # Access property units directly
```

## Property Change Detection

The SDK can automatically warn you when property values change between script/notebook runs. This is useful when you're using property values for calculations and want to be notified if a colleague changes them in the webapp.


## License

MIT
