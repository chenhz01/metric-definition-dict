# Changelog — metric-definition-dict

All releases are local drafts; no remote operations are performed.

## v0.1.1 — 2026-10-13

Fixed:
- bench now guards division by zero when a timer returns 0 (degenerate clocks).
- window `0d` is accepted by the grammar but documented as degenerate rather than silently meaning "never".

Changed:
- self_test expanded to 65 cases across functional / exception / extreme-edge
  categories (scaffold v2 four defenses: SystemExit capture, Unicode-safe
  matching, Windows newline-safe fixtures, SUMMARY last line); added UTF-8 BOM
  tolerance in `_load` (utf-8-sig) so Windows-authored files pass.
- README: Performance section numbers re-measured with the shipped `bench`
  subcommand and reproducible command column added.

## v0.1.0 — 2026-10-13

Added:
- Initial local draft: metric definition dictionary schema (id/kind/window/numerator/denominator),
  structural validation rules R1–R9, cross-entry conflict detection C1–C3,
  argparse CLI (`validate` / `check` / `bench`) and scaffold-v2 self_test.
