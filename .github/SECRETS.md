# GitHub Secrets for Publishing

Add these repository secrets in GitHub → Settings → Secrets and variables → Actions:

- TEST_PYPI_API_TOKEN: API token for TestPyPI (`__token__` user)
- PYPI_API_TOKEN: API token for PyPI (`__token__` user)

Optional:
- CODECOV_TOKEN: If your repository is private and you use Codecov

Tagging strategy:
- Release candidates: `v0.1.1-rc1` (publishes to TestPyPI)
- Final releases: `v0.1.1` (publishes to PyPI)

