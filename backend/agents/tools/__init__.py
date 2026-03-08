"""Scoped tools per agent (zero-trust)."""
from agents.tools.searcher_tools import get_searcher_tools
from agents.tools.analyzer_tools import get_analyzer_tools
from agents.tools.pentester_tools import get_pentester_tools

__all__ = ["get_searcher_tools", "get_analyzer_tools", "get_pentester_tools"]
