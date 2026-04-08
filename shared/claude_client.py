"""
Shared Claude API client factory.
Import this wherever you need an Anthropic client instance.
"""

import anthropic


def get_client() -> anthropic.Anthropic:
    """Return a configured Anthropic client using ANTHROPIC_API_KEY from env."""
    return anthropic.Anthropic()
