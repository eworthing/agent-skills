"""Provisioning and lifecycle for the listener a Service accepts connections
on.

A Service needs one bound, listening resource for its whole life. Getting
one ready takes several steps -- clear out any stale registration for the
address, allocate the resource, turn on address reuse and descriptor
inheritance, bind, then start accepting a backlog. `open_listener` does all
of that in one call; `Service` wraps the result for whatever runs the
request loop.
"""

from __future__ import annotations

import sys
from itertools import count

DEFAULT_BACKLOG = 8

_id_seq = count(1)
_OPEN_DESCRIPTORS: set[int] = set()
_BOUND_ENDPOINTS: set[tuple[str, int]] = set()


class EndpointInUseError(Exception):
    """Raised when an endpoint is already bound by another listener."""


class Listener:
    """A single bound, listening resource.

    Tracks its own open/closed state in the module-level descriptor ledger
    so a leaked instance is observable from outside.
    """

    def __init__(self) -> None:
        self._id = next(_id_seq)
        self._closed = False
        self.reuse_enabled = False
        self.inheritable = False
        self._endpoint: tuple[str, int] | None = None
        _OPEN_DESCRIPTORS.add(self._id)

    @property
    def descriptor_id(self) -> int:
        """The id a successor would use to adopt this resource.

        -1 once closed, the same way a closed low-level descriptor reports
        itself -- reading it never raises.
        """
        return -1 if self._closed else self._id

    def set_reuse(self, enabled: bool) -> None:
        self.reuse_enabled = enabled

    def set_inheritable(self, enabled: bool) -> None:
        self.inheritable = enabled

    def bind(self, endpoint: tuple[str, int]) -> None:
        if endpoint in _BOUND_ENDPOINTS:
            raise EndpointInUseError(endpoint)
        _BOUND_ENDPOINTS.add(endpoint)
        self._endpoint = endpoint

    def activate(self, backlog: int) -> None:
        self.backlog = backlog

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        _OPEN_DESCRIPTORS.discard(self._id)
        if self._endpoint is not None:
            _BOUND_ENDPOINTS.discard(self._endpoint)
            self._endpoint = None


def clear_stale(endpoint: tuple[str, int]) -> None:
    """Drop any leftover binding registration for `endpoint` before reuse."""
    _BOUND_ENDPOINTS.discard(endpoint)


def open_listener(endpoint: tuple[str, int]) -> Listener:
    """Build, configure, bind, and activate a listener in one call.

    Semi-public: `start_with_handoff` uses this to get a resource ready
    before handing its descriptor to a successor, but any other caller that
    wants provisioning control separate from `Service` can call it directly
    too.
    """
    clear_stale(endpoint)
    listener = Listener()
    listener.set_reuse(True)
    listener.set_inheritable(True)
    try:
        listener.bind(endpoint)
    except EndpointInUseError:
        print(f"endpoint already in use: {endpoint}", file=sys.stderr)
        raise
    listener.activate(DEFAULT_BACKLOG)
    return listener


class Service:
    """Owns one endpoint's request-accepting resource for as long as the
    service runs.

    Always provisions its own listener on construction. A caller that plans
    to supply an already-provisioned one instead (see `start_service`'s
    `adopt` argument) passes `bind=False` to skip binding it -- the
    placeholder listener still gets created either way.
    """

    def __init__(self, endpoint: tuple[str, int], *, bind: bool = True) -> None:
        self.listener = Listener()
        if bind:
            self.listener.set_reuse(True)
            self.listener.set_inheritable(True)
            self.listener.bind(endpoint)
            self.listener.activate(DEFAULT_BACKLOG)

    def close(self) -> None:
        self.listener.close()


def start_service(endpoint: tuple[str, int], *, adopt: Listener | None = None) -> Service:
    """Build a Service for `endpoint`.

    If `adopt` is given -- a listener `open_listener` already bound and
    activated elsewhere -- the service takes that one over instead of
    binding its own.
    """
    if adopt is not None:
        service = Service(endpoint, bind=False)
        service.listener = adopt
        return service
    return Service(endpoint, bind=True)


def provision_listener(endpoint: tuple[str, int]) -> Listener:
    """A ready-to-use listener for `endpoint`, provisioned the same way
    `start_service` would provision one of its own."""
    return open_listener(endpoint)


def start_with_handoff(endpoint: tuple[str, int]) -> int:
    """Provision a listener for `endpoint`, then hand its descriptor to a
    successor and release this process's own reference to it.

    This is the shape a warm restart uses: the successor picks the same
    resource back up from the descriptor id instead of rebinding.
    """
    listener = provision_listener(endpoint)
    descriptor_id = listener.descriptor_id
    listener.close()
    return descriptor_id
