# Loop 2 Review

Transition-legality fixture: transition-illegal-post-cap-continue. Loop 1 emits HALT_LOOP_CAP (terminal per canon/states.toml transitions.HALT_LOOP_CAP.edges == []) and loop 2 resumes with CONTINUE anyway -- a run continuing past a terminal halt without --reset. The report-only transition check must print one [transition-violation ...] line for this pair; nothing else in the suite blocks it on exit code (the check is report-only).
