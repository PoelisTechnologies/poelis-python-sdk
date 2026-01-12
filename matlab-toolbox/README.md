# Poelis MATLAB Toolbox

## 1. Install the Poelis MATLAB Toolbox

### Download the `.mltbx` file

Then, either:

- **Double‑click** the `PoelisToolbox.mltbx` file in the Current Folder browser, **or**
- Run this command in MatLab:

```matlab
matlab.addons.install('PoelisToolbox.mltbx');
```

---

## 2. Create a Python virtualenv and install `poelis-sdk`

In a terminal:

```bash
cd /path/to/poelis-python-sdk
python3 -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -U poelis-sdk
```

Note the full path of the Python inside the venv, e.g.:
- macOS/Linux: `/path/to/.venv/bin/python`
- Windows: `C:\path\to\.venv\Scripts\python.exe`

---

## 3. Point MATLAB to this Python environment

In MATLAB:

```matlab
pyenv('Version', '/full/path/to/.venv/bin/python');  % adjust path
pyenv   % optional: check it looks correct
```

You can quickly check everything with:

```matlab
poelis_sdk.checkInstallation();
```

---

## 4. Run the example code

In MATLAB:

Open the example script "try_poelis_matlab.m"

Then in the script:
1. Set your real API key:

```matlab
api_key = 'your-api-key';
```

2. Adjust any demo paths like:

```matlab
path = 'demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass';
```

3. Run the script.

You should see:
- list of workspaces,
- example property values,
- property updates,
- and basic error‑handling output.

---

## 5. Example: Updating Property Values

The toolbox supports updating property values for draft properties:

```matlab
% Update a numeric property
poelis.change_property('workspace.product.draft.item.property', 123.45);

% Update with title and description
poelis.change_property('workspace.product.draft.item.property', 123.45, 'Title of change (optional)', 'Description of change (optional)');

% Update a text property
poelis.change_property('workspace.product.draft.item.description', 'New text');
```

**Important Notes:**
- Only **draft properties** can be updated (use `.draft` in the path)
- Versioned properties (`.v1`, `.v2`, `.baseline`) are read-only
- **Requires EDITOR role**: Write operations require EDITOR role for the workspace or product
  - Users with VIEWER role can only read data and will receive a permission error
- Numeric values can be numbers or matrixes
- Text values must be strings
- Date values must be in ISO 8601 format (YYYY-MM-DD)

