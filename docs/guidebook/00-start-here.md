# Guidebook: start here

## What this is

The site (name lives only in `site.config.yaml`) is a free, nightly-updated dashboard of the
Icelandic economy built from official open data, inspired by econvitals.org. The repo layout,
hard rules and commands are in `AGENTS.md`; read it first.

## Where we are

Phases: 0 foundations → 1 data spine + home → 2 topic pages → 3 briefings + newsletter →
4 originals and tools → 5 go public.

- **Phase 0 is done**: repo layout, registry schema, three seed series (headline CPI, CPI less
  housing, policy rate), PxWeb + NSDP clients, nightly harvest workflow, CI, Pages deploy.
- **Phase 1 (current)**: pin exact PxWeb leaf tables/codes and NSDP keys, add the remaining
  core series (national accounts, labour force survey, wages, retail, housing, FX, yields,
  fiscal, external), fill the release calendars. Tracked in `registry/backlog.yaml`.

## Conventions

- Series CSVs are tidy: `date, period, value` (period is the raw publisher code, e.g.
  `2026M10`; date is the period start in ISO).
- `data/status.json` is the health page: ok / stale per series, never deleted.
- Iceland is UTC year-round; the nightly harvest runs 05:17 UTC, after the morning releases.
- UI language is Icelandic first (`site.language: is`), English secondary; titles in series
  yaml carry both.
- Inflation reference line on charts: the Seðlabanki target from `site.config.yaml`
  (`conventions.inflation_target`, 2.5% CPI yoy).

## Runbook

- Nightly: `harvest.yml` → `python -m pipelines.run --fetch auto` → commit `data/` → `deploy.yml`.
- Manually: `make update SOURCE=<id>`; `make check` before any PR.
- Broken source: the run marks the series stale; file a `scraper-broken` issue; never edit
  `data/series/` by hand to "fix" it.
- New series: `registry/series/_template.yaml` + provider `fetch(spec)` + offline test +
  `verified_against` before it goes live.
