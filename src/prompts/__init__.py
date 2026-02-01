"""Shared prompt loading utilities."""

from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parent


def load(name: str, *, encoding: str = "utf-8") -> str:
    """Load a prompt file by path relative to prompts dir. E.g. 'parser.txt', 'jury/vote_template.txt'."""
    path = _root() / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding=encoding)


def load_jury_template(name: str, *, encoding: str = "utf-8") -> str:
    """Load a jury prompt. E.g. 'vote_template', 'debate_template'."""
    return load(f"jury/{name}.txt", encoding=encoding)


def load_role_instruction(agent_name: str, *, encoding: str = "utf-8") -> str:
    """Load role instruction for a jury agent. E.g. 'literal', 'context'."""
    return load(f"jury/{agent_name}.txt", encoding=encoding)
