# Changes

Following the dedicated-path refactor, Panel (multi-column) groups no
longer received a label -- they never went through the side-effect
pinning `apply_plot` was written to avoid, and nothing replaced it for
them. This silently emptied scatter-plot legends for Panel groups.

Fix: `apply_plot` now forwards `(group, key=group.key)` uniformly for
every group shape. `scatter` already accepted an optional `key`, so both
call paths keep working. Added a regression test covering Panel legend
labels.
