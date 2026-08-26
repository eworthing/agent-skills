"""Legacy marker vocabulary, kept for record specs written against this
package's older annotation style. A field author may still import `Derived`
from here instead of from `markers_native` -- a record scanner needs to
recognize either spelling the same way.
"""

from __future__ import annotations

from markers_native import _MarkerForm

Derived = _MarkerForm("Derived")
