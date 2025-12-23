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
poelis.checkInstallation();
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
- and basic error‑handling output.

