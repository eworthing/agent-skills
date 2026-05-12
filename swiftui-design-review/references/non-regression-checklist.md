# Non-Regression Checklist

Use this checklist for UI/UX-heavy PRs, refactors, and "cleanup" changes.

## Contract (What Must Not Change)

- Layout stability:
  - [ ] Existing views render correctly at default Dynamic Type size
  - [ ] No clipped or overlapping content at large Dynamic Type sizes (AX1+)
  - [ ] iPhone and iPad layouts both work correctly
- Button styles:
  - [ ] Modal content uses `.bordered`/`.borderedProminent` button styles
  - [ ] No hardcoded colors or spacing values introduced
- Accessibility + testability:
  - [ ] Accessibility identifiers remain stable (or have a migration plan)
  - [ ] Identifiers are applied to leaf elements only (no `.contain` container IDs)
  - [ ] VoiceOver reading order is logical

## Evidence (Required for High-Risk Changes)

- [ ] iPhone: screenshots at standard and large Dynamic Type
- [ ] iPad: screenshots in portrait and landscape
- [ ] Dark mode: screenshots confirming readability

## Manual QA Script

- iPhone:
  - [ ] Navigation flows work (push/pop, present/dismiss)
  - [ ] Dynamic Type at large sizes: no clipped labels or buttons
  - [ ] Orientation change: layout adapts without breakage
- iPad:
  - [ ] Split view and slide over: layout adapts correctly
  - [ ] Popovers and sheets display as expected
  - [ ] Landscape orientation: no hidden or clipped content
- Both:
  - [ ] Dark mode: all text readable
  - [ ] VoiceOver: interactive elements reachable, reading order correct

## Automated Validation

- [ ] `xcodebuild build` succeeds for iPhone and iPad destinations
- [ ] `xcodebuild test` UI tests pass
- [ ] `swiftformat . --lint` passes
- [ ] `swiftlint lint --quiet` passes
