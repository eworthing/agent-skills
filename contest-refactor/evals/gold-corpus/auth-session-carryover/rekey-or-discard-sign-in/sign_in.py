"""Attaching a signed-in principal to a session.

What happens to the session depends on what it already held: a session
with no prior principal gets a new token but keeps its data -- data set
during anonymous browsing is retained when a principal signs in. A session
whose prior principal differs, or whose stored credential stamp no longer
matches the incoming principal's, is discarded outright so nothing from
before survives into the new principal's session. A session already signed
in as the same principal with a matching stamp is left alone.
"""

from __future__ import annotations

import hmac

from principal import Principal
from session import Session


def sign_in(session: Session, principal: Principal) -> None:
    stamp = principal.credential_stamp
    if session.principal_id is not None:
        if session.principal_id != principal.id or (
            stamp and not hmac.compare_digest(session.credential_stamp or "", stamp)
        ):
            session.discard()
    else:
        session.rotate_token()
    session.principal_id = principal.id
    session.credential_stamp = stamp
