# Contributing

Bug reports and pull requests are welcome. Please keep changes reproducible
without private API keys and do not commit raw personal AutoClaw workspaces,
chat history, tokens, PDFs, or generated caches.

Before opening a pull request:

```powershell
python -m pip install -e ".[dev]"
ruff check .
pytest -q
python -m adpaper validate
python -m adpaper build
```

Changes to a domain filter should include fixtures for both positive and
negative examples. Changes to templates should be checked at desktop and
mobile widths.

