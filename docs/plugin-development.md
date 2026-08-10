# Domain Plugins

Implement a module-level `plugin` object with:

```python
class Plugin:
    slug: str
    version: str  # optional; written to daily manifests
    display_name: str
    tags: tuple[str, ...]

    def evaluate(self, paper) -> RelevanceResult: ...
    def assign_tags(self, paper) -> TagAssignment: ...
```

`evaluate()` must be deterministic and must not perform network requests.
Return a high-recall decision, a numeric score, matched terms, and short
reasons. `assign_tags()` should return one primary tag and at most two
secondary tags. Put provider-specific model calls in the optional enrichment
layer, not in the plugin itself.
