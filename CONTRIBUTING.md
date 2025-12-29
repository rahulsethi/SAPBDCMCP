# Contributing (scaffold)

- Use `ruff` for formatting/linting.
- Add tests for new tools.
- Keep tool outputs small and stable (LLM-friendly).

## Dev commands

```bash
pip install -e ".[dev]"
pytest
ruff check .
```
