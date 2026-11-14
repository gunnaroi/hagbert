# AGENTS.md: start here

This file is the entry point for **any** agent or person working on this repo. Read it in full before changing anything.

## What this project is

A public, free, nightly-updated dashboard of the Icelandic economy: growth, prices, jobs, activity, money and banking, markets, public finances and the external sector, plus a release calendar and a status page. It is inspired by econvitals.org (Jason Furman's U.S. dashboard) and credits it on the site, but it is independent.

The site's name, tagline and colours live **only** in `site.config.yaml`. Say "the site" in prose and read the name from config in code.

## Current phase

See `docs/guidebook/00-start-here.md` → "Where we are". Phases: 0 foundations → 1 data spine + home → 2 topic pages → 3 briefings + newsletter → 4 originals and tools → 5 go public.

## Hard rules (never break these)

1. **No hard-coded site name.** Read it from `site.config.yaml`. `make check` enforces this.
2. **Every number shown traces to a series id** in `registry/series/`. No numbers typed by hand into pages.
3. **A failed fetch or validation never overwrites good data.** Mark the series stale in `data/status.json`, fail the run, and open or update a `scraper-broken` issue. Stop.
4. **Raw downloads are never committed.** They go to `data/raw/` (git-ignored).
5. **Use only the data we hold.** Pages and later briefings use our series plus official releases (Hagstofa Íslands, Seðlabanki Íslands, Þjóðskrá, OECD, Eurostat). No outside facts presented as findings.
6. **Respect licences.** Hagstofa PxWeb and OECD/Eurostat data are CC BY 4.0 and can be redistributed with attribution. Each series yaml records its `licence` and `downloadable` flag; `downloadable` must be false for `show-only` or `unverified` licences. Never use paywalled data.
7. **AI writing needs human approval.** When briefings arrive (phase 3), drafts go to a PR; a human merge is the only way to publish.
8. **Never delete data files or history** to "clean up". Ask the maintainer.
9. **Keep the guidebook true.** If you change how something works, update the matching page in `docs/guidebook/` in the same PR.
10. **Respect upstream rate limits.** PxWeb allows 30 calls/s and 150,000 values per call; `pipelines/sources/hagstofa.py` enforces this. Cache downloads (default 6 h) so reruns are free.

## Map of the repo

| Path | What lives there |
|---|---|
| `site.config.yaml` | Identity, brand, conventions, switches |
| `registry/series/*.yaml` | One file per series: the single source of truth for metadata |
| `registry/calendar/*.yaml` | Release calendars (Hagstofa, Seðlabanki) |
| `registry/backlog.yaml` | Indicators planned but not yet built, by phase |
| `pipelines/core.py` | Shared code: cached HTTP, registry loading/validation, publishing, status |
| `pipelines/sources/<provider>.py` | One module per data provider (Hagstofa PxWeb, Seðlabanki NSDP, ...) |
| `pipelines/run.py` | CLI that runs harvesters: one series, one source, or all `fetch: auto` |
| `pipelines/build/site_data.py` | Turns registry + data into the JSON the site reads |
| `data/series/`, `data/meta/`, `data/status.json` | Tidy CSV per series + JSON metadata + health (committed) |
| `data/raw/` | Raw downloads (git-ignored) |
| `measures/` | Measures we build ourselves (pattern from econvitals/replication, CC0): `replicate.py` + `check.json` per folder |
| `site/` | Astro static site |
| `scripts/`, `tools/` | Registry validation, name check, measure checks |
| `tests/` | Offline tests (no network) |
| `docs/guidebook/` | How everything works: conventions, runbook, playbooks |
| `.github/` | Workflows (ci, harvest, check-secrets, deploy), issue + PR templates |

## Commands

```bash
make setup            # uv sync + npm install (site)
make check            # registry validation + name check + pytest
make update SOURCE=cpi_headline   # fetch → validate → publish one series
make update-auto      # all fetch: auto series
make build            # site JSON + Astro build into site/dist
make dev              # local site
```

## Adding things

- New indicator: copy `registry/series/_template.yaml`, implement `fetch(spec)` in the provider module if new, add an offline parser test, fill `verified_against` before the series goes live.
- New source: see `registry/backlog.yaml` and the guidebook; scout first, respect limits, record licence.
- Broken fetch: file a `scraper-broken` issue; the series stays stale until the source recovers.
