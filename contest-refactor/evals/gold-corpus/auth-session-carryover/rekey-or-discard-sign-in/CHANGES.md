# rekey-or-discard-sign-in — behavior note

Signing a principal into a session now depends on what the session already
held:

- No prior principal (an anonymous session signing in for the first time):
  the session gets a new token; whatever was already stored in it is
  retained.
- A different prior principal, or the same principal whose credential
  stamp no longer matches the one on file: the session is discarded
  outright -- new token, empty data -- so nothing from the old principal's
  session can be read by the new one.
- The same principal, same credential stamp: the session is left alone.

Data set before sign-in (a session started out anonymous, then
authenticated) is deliberately retained, not cleared -- only a principal
change or a stamp mismatch clears a session's data.
