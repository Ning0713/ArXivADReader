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

Changes to a domain filter should include positive examples, near-match negative
examples, tag assertions, and appropriate `arxiv_categories`. A new domain must
also update its site branding and document how existing archive data is kept
separate. Changes to templates should be checked at desktop and mobile widths.
