"""The knowledge-space visualizer: a self-contained interactive graph, no CDN, no build step.

`python -m mangrove_kb.viz > graph.html` writes one HTML file that opens in any browser.
"""
from .render import main

__all__ = ["main"]
