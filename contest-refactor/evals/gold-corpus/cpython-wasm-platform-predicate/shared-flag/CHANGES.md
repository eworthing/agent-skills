# shared-flag — behavior note

`platsupport` gains `is_driftplane(platform)`, true when `platform` is
either sandboxed runtime platform. The three guards whose reason applies
identically to both platforms (`test_shared_temp_writable`,
`test_process_fork`, `test_large_page_alloc`) now use it instead of
spelling out the two-platform check inline.

Every other guard is unchanged: the single-platform guards, and the two
tests carrying one guard per platform, still name `is_gearshift` /
`is_tideline` directly. No test's skip/run outcome changes on any platform.
