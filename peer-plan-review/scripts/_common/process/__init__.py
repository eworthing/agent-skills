"""Process lifecycle helpers (process-group kill, popen kwargs)."""

from .tree import _kill_tree, _popen_session_kwargs

__all__ = ["_kill_tree", "_popen_session_kwargs"]
