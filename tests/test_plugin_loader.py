import sys
import types

import pytest

from adpaper.filtering import load_plugin
from adpaper.models import RelevanceResult, TagAssignment


def test_plugin_loader_requires_discovery_categories(monkeypatch):
    module = types.ModuleType("tests.incomplete_plugin")

    class IncompletePlugin:
        slug = "incomplete"
        display_name = "Incomplete"
        tags = ("Topic",)

        def evaluate(self, paper):
            return RelevanceResult(include=True, score=100)

        def assign_tags(self, paper):
            return TagAssignment("Topic")

    module.plugin = IncompletePlugin()
    monkeypatch.setitem(sys.modules, module.__name__, module)

    with pytest.raises(TypeError, match="does not implement DomainPlugin"):
        load_plugin(f"{module.__name__}:plugin")
