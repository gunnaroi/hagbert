## What
<!-- one or two lines -->

## Verified
<!-- which numbers you checked against which official source (URL + page/table) -->

## Checklist (AGENTS.md → hard rules)
- [ ] `make check` passes (registry validation, name check, tests)
- [ ] New/changed series have a yaml, an offline test, and `verified_against` filled before going live
- [ ] No raw downloads committed (`data/raw/` stays git-ignored)
- [ ] A failed fetch still leaves good data untouched (stale marker only)
- [ ] Guidebook updated if behaviour changed
- [ ] Briefing PRs (phase 3): human merge is the only way to publish
