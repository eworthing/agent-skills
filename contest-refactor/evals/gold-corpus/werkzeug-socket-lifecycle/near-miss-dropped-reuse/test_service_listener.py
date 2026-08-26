#!/usr/bin/env python3
"""service_listener's own bundled test suite (this variant).

Run directly: python3 test_service_listener.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from service_listener import provision_listener, start_service, start_with_handoff


def test_listener_starts_open_and_closes_cleanly() -> None:
    listener = provision_listener(("basics", 9001))
    assert listener.descriptor_id >= 0
    listener.close()
    assert listener.descriptor_id == -1
    listener.close()  # idempotent, must not raise
    assert listener.descriptor_id == -1


def test_plain_service_lifecycle_leaves_nothing_open() -> None:
    service = start_service(("plain", 9002))
    assert service.listener.descriptor_id >= 0
    service.close()
    assert service.listener.descriptor_id == -1


def test_start_with_handoff_returns_an_int() -> None:
    descriptor_id = start_with_handoff(("handoff", 9003))
    assert isinstance(descriptor_id, int)


def test_adopting_a_listener_keeps_it_usable() -> None:
    endpoint = ("adopt", 9004)
    prepared = provision_listener(endpoint)
    service = start_service(endpoint, adopt=prepared)
    assert service.listener is prepared
    assert service.listener.descriptor_id >= 0
    service.close()


def test_provisioned_listener_is_inheritable() -> None:
    listener = provision_listener(("inherit", 9005))
    assert listener.inheritable is True
    listener.close()


def main() -> int:
    test_listener_starts_open_and_closes_cleanly()
    test_plain_service_lifecycle_leaves_nothing_open()
    test_start_with_handoff_returns_an_int()
    test_adopting_a_listener_keeps_it_usable()
    test_provisioned_listener_is_inheritable()
    print("OK: test_service_listener.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
