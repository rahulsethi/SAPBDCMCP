# Contributing

Thanks for your interest in `sap-bdc-mcp`. Contributions are welcome.

## Licensing

By contributing a pull request to this repository, you agree that your contribution will be licensed under the project's current license — the **Business Source License 1.1 (BSL 1.1)** (see [`LICENSE`](LICENSE)). The maintainer retains the right to use, modify, and (where applicable) relicense the codebase including your contributions.

If you cannot agree to those terms, please open an issue first to discuss.

## Dev setup

```bash
git clone https://github.com/rahulsethi/SAPBDCMCP.git
cd SAPBDCMCP
python -m venv .venv
source .venv/bin/activate          # or .venv\Scripts\Activate.ps1 on Windows
pip install -e ".[dev]"
```

## Conventions

- Use `ruff` for formatting + linting.
- Use `mypy` for type checks.
- Every new tool must declare full `ToolMetadata` (`mutability`, `risk`, `api_surface`, `api_evidence`, `bulk_data_behavior`). See `docs_public/SAP_API_POLICY.md` for the rationale.
- Add tests for every new tool. Keep tool outputs small and stable (LLM-friendly).
- Each source file carries a `Version: vN` header in its module docstring. Bump it on substantive edits.

## Pre-commit checks

```bash
pytest -q
ruff format --check .
ruff check .
mypy src/sap_bdc_mcp
```

All four must pass before merging.

## Filing issues

- Bugs / questions / feature requests: <https://github.com/rahulsethi/SAPBDCMCP/issues>.
- Commercial licensing inquiries: see [`docs_public/COMMERCIAL_LICENSING.md`](docs_public/COMMERCIAL_LICENSING.md).
- Security advisories: please report privately via GitHub Security Advisories on the repo.
