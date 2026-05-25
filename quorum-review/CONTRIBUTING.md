# Contributing to quorum-review

## When editing `scripts/quorum/parsing.py` or `scripts/quorum/prompts.py`

If you add a function, confirm it fits one of the section headers documented in the module's top-level docstring. If not, propose a new section (and add a header comment) rather than appending to an existing one. The 600-LoC soft cap + 800-LoC hard cap (`common/scripts/check_module_size.py`) keep these modules from becoming new monoliths.
