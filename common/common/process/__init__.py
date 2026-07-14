"""Process lifecycle helpers (process-group kill, bounded drain, popen kwargs)."""

from .tree import _kill_tree, _popen_session_kwargs, drain_process

__all__ = ["_kill_tree", "_popen_session_kwargs", "drain_process"]
