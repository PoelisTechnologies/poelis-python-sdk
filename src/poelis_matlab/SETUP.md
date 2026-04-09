# Using Poelis from MATLAB

If you already use MATLAB for calculations or simulation, you can call the Poelis Python SDK from MATLAB by pointing MATLAB to a Python environment where `poelis-sdk` is installed and then using the Poelis MATLAB Toolbox helpers.

This setup lets you:

- read values and metadata from Poelis in MATLAB
- run calculations locally in MATLAB
- keep Poelis as the source of truth while doing analysis in your own environment

## How It Works

MATLAB talks to Python through `pyenv`. The Poelis MATLAB Toolbox is a thin MATLAB wrapper around the Python SDK. The toolbox gives you MATLAB-friendly helpers such as `poelis_sdk.checkInstallation()` and `poelis_sdk.PoelisClient(...)`, while the actual API calls are handled by the Python package installed in your virtual environment.

## First-Time Setup

### 1. Install the Poelis MATLAB Toolbox

Download the latest `PoelisToolbox-<version>.mltbx` release artifact and install it in MATLAB.

You can either:

- double-click the `.mltbx` file in MATLAB, or
- run:

```matlab
matlab.addons.toolbox.installToolbox('PoelisToolbox-1.0.8.mltbx');
```

### 2. Create a Python Environment and Install `poelis-sdk`

In a terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -U poelis-sdk
which python                # on Windows: where python
```

Keep the full path printed by `which python` or `where python`. You will need it in MATLAB.

### 3. Point MATLAB to That Python Environment

In MATLAB:

```matlab
pyenv('Version', '/full/path/to/.venv/bin/python');   % on Windows: full path to .venv\Scripts\python.exe
pyenv
```

If MATLAB is already using another Python interpreter, restart the Python session first:

```matlab
terminate(pyenv)
pyenv('Version', '/full/path/to/.venv/bin/python');
```

### 4. Verify the Setup

In MATLAB:

```matlab
poelis_sdk.checkInstallation();
mod = py.importlib.import_module('poelis_sdk');
char(py.builtins.getattr(mod, '__version__'))
char(py.builtins.getattr(mod, '__file__'))
```

You should see:

- the installed `poelis-sdk` version
- the Python file path inside the environment you configured

### 5. Start Using the SDK

Open `try_poelis_matlab.m`, replace the API key and demo paths with your real ones, and run it.

## Updating an Existing MATLAB Setup

When a new SDK or toolbox version is released, users usually need to update both parts:

### 1. Install the New MATLAB Toolbox

Install the new `PoelisToolbox-<version>.mltbx` file in MATLAB.

```matlab
matlab.addons.toolbox.installToolbox('PoelisToolbox-1.0.8.mltbx');
```

If MATLAB asks you to restart after the toolbox update, do that first.

### 2. Upgrade the Python SDK

Activate the same Python environment that MATLAB uses, then run:

```bash
pip install -U poelis-sdk
```

### 3. Restart MATLAB's Python Session

In MATLAB:

```matlab
terminate(pyenv)
```

If the Python path did not change, MATLAB will usually pick up the same interpreter again on the next Python call. If the Python environment changed, run `pyenv('Version', ...)` again.

### 4. Verify After the Update

In MATLAB:

```matlab
poelis_sdk.checkInstallation();
mod = py.importlib.import_module('poelis_sdk');
char(py.builtins.getattr(mod, '__version__'))
```

## Troubleshooting

- If MATLAB loads the wrong Python package, check `char(py.builtins.getattr(mod, '__file__'))`.
- If you change Python environments, run `terminate(pyenv)` before calling `pyenv('Version', ...)` again.
- If the toolbox is updated but Python is not, MATLAB may still load an older `poelis-sdk`.
- If Python is updated but the toolbox is not, users may miss MATLAB wrapper fixes or examples from the newer release.
