from __future__ import annotations

import importlib
from typing import Protocol, runtime_checkable

from adpaper.models import Paper, RelevanceResult, TagAssignment


@runtime_checkable
class DomainPlugin(Protocol):
    slug: str
    display_name: str
    tags: tuple[str, ...]
    arxiv_categories: tuple[str, ...]

    def evaluate(self, paper: Paper) -> RelevanceResult: ...

    def assign_tags(self, paper: Paper) -> TagAssignment: ...


def load_plugin(reference: str) -> DomainPlugin:
    module_name, separator, attribute = reference.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("Plugin reference must use 'module:attribute' syntax")
    module = importlib.import_module(module_name)
    plugin = getattr(module, attribute)
    if not isinstance(plugin, DomainPlugin):
        raise TypeError(f"{reference} does not implement DomainPlugin")
    return plugin
