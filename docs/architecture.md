# Architecture

The repository is a static-site pipeline:

```text
Axi daily HTML -> parser -> domain plugin -> optional LLM enrichment
                                  |                 |
                             arXiv metadata --------+
                                  |
                   data/papers + data/daily + indexes
                                  |
                         Jinja2 static site
                                  |
                         GitHub Pages / CNAME
```

The Axi page is the default candidate authority. arXiv metadata fills missing
authors, dates, categories, and canonical links. A failed arXiv enrichment does
not discard Axi content. A failed Axi fetch leaves the last published date
untouched unless an operator explicitly enables arXiv discovery fallback.

Favorites are browser-local. No visitor, account, or traffic database is
required.

