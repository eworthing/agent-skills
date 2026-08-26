# consolidated-service-ownership — behavior note

`open_listener()` is gone. Every responsibility it had moves onto `Service`
itself:

| open_listener did                            | Service now does                                    |
|-----------------------------------------------|------------------------------------------------------|
| `clear_stale(endpoint)`                       | in `__init__`, before configuring                     |
| `Listener()` + `set_reuse(True)`              | `Listener()` + `set_reuse(self.reuse_by_default)`     |
| `set_inheritable(True)`                       | same, in `__init__`                                   |
| `bind(endpoint)`, friendly message on conflict | same, in `__init__`'s `try`/`except`                  |
| `activate(backlog)`                           | `activate(self.backlog)`                              |

`reuse_by_default` and `backlog` are now class attributes instead of
literals buried in the old helper, so a subclass can override either
without copying the whole provisioning sequence.

One more fix along the way: construction used to leave an unused listener
open whenever `bind=False` -- the case where a caller supplies its own
already-active one through `start_service`'s `adopt` argument. `__init__`
now releases that placeholder immediately in the `bind=False` branch
instead of leaving it for something else to replace.

No caller-visible behavior changes: every endpoint that used to bind still
binds the same way, with the same reuse and inheritance settings, through
the same public entry points.
