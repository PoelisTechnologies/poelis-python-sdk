# Poelis MATLAB Toolbox

## Install or Update the Toolbox

Download the latest `.mltbx` release artifact, then install it in MATLAB:

- Double-click the `.mltbx` file in the Current Folder browser, or
- Run:

```matlab
matlab.addons.toolbox.installToolbox('PoelisToolbox-1.0.8.mltbx');
```

If you are updating from an older toolbox version, install the new `.mltbx` first and then restart MATLAB if the Add-On manager prompts you to do so.

## Install or Update the Python SDK

The MATLAB toolbox is a wrapper around the Python SDK. Users must also install the latest published `poelis-sdk` in the Python environment that MATLAB uses.

In a terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -U poelis-sdk
```

To upgrade an existing environment:

```bash
pip install -U poelis-sdk
```

## Point MATLAB to the Python Environment

In MATLAB:

```matlab
pyenv('Version', '/full/path/to/.venv/bin/python');
pyenv
```

If MATLAB was already using a different Python interpreter, restart the Python session first:

```matlab
terminate(pyenv)
pyenv('Version', '/full/path/to/.venv/bin/python');
```

## Verify the Installation

In MATLAB:

```matlab
poelis_sdk.checkInstallation();
mod = py.importlib.import_module('poelis_sdk');
char(py.builtins.getattr(mod, '__version__'))
char(py.builtins.getattr(mod, '__file__'))
```

The version should match the latest PyPI release you expect, and the file path should point to the Python environment you configured with `pyenv(...)`.

## Run the Example Script

Open `try_poelis_matlab.m`, set your real API key, replace the demo paths with real Poelis paths, and run the script.

The toolbox supports:

- Listing workspaces, products, and child nodes
- Reading values and property metadata
- Updating draft properties
- MATLAB-native type conversion for common Python return values

## Important Usage Notes

- Property paths must include an explicit item before the final property name.
- Read examples:
  - `workspace.product.item.property`
  - `workspace.product.baseline.item.property`
- Write examples:
  - `workspace.product.draft.item.property`
  - `workspace.product.item.property` also works and is routed through draft
- Versioned properties (`.v1`, `.v2`, `.baseline`) are read-only.
- Write operations require `EDITOR` role access.

## Maintainer Release Workflow

Use a manual `.mltbx` release process and keep the toolbox version aligned with the Python SDK version in `pyproject.toml`.

Before release:

1. Merge the MATLAB wrapper changes.
2. Bump `project.version` in `pyproject.toml`.
3. Set the toolbox version in `toolbox.prj` to the same version number.
4. Run the full Python test suite:

```bash
./.venv/bin/python -m pytest -q
```

In MATLAB R2025b, package the toolbox:

```matlab
addpath("scripts");
outputFile = package_matlab_toolbox()
```

Then:

1. Upload the generated `.mltbx` to the GitHub release or your internal distribution channel.
2. Let the existing GitHub Actions workflow publish the Python SDK to PyPI when `pyproject.toml` changes.
3. Tell users to:
   - install/update the new `.mltbx`
   - run `pip install -U poelis-sdk`
   - restart MATLAB Python with `terminate(pyenv)` if needed
   - verify with `poelis_sdk.checkInstallation()`

`package_matlab_toolbox` reads the metadata from `src/poelis_matlab/toolbox.prj`, checks that the toolbox version matches `pyproject.toml`, and writes `dist/PoelisToolbox-<version>.mltbx`.
