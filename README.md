# Hagbert

**A free, daily-updated read on the Icelandic economy, straight from the official data.**

Hagbert brings together what Statistics Iceland (Hagstofa Íslands), the Central Bank of Iceland (Seðlabanki Íslands) and the international databases publish: growth, prices, jobs, activity, money and banking, markets, public finances and the external sector. It updates as new numbers come out. Every chart names its source, and every series has its own page with its history, method and a download where the licence allows.

It is an independent project, not affiliated with Hagstofa Íslands, Seðlabanki Íslands or any data provider. It is inspired by [Econvitals](https://econvitals.org), Jason Furman's dashboard of the U.S. economy, and is not affiliated with it either; methods ported from the [econvitals/replication](https://github.com/econvitals/replication) repository (CC0) are credited in `measures/`.

## What's on it (planned)

| Page | Highlights |
|---|---|
| **Home** | Key indicators grid: activity vs. inflation composites, each scaled by its own history (the econvitals 2×2 idea, rebuilt on Icelandic data) |
| **Growth** | Quarterly GDP and components from the national accounts; Seðlabanki's forecasts against outturns |
| **Inflation** | CPI by COICOP group, CPI less housing (the official Icelandic core measure), HICP, dispersion across items |
| **Jobs** | Labour force survey: unemployment, participation, hours; registered unemployment; wage index |
| **Activity** | Retail turnover, building permits and starts, tourism, external trade |
| **Money & markets** | Policy rate and Seðlabanki's rate decisions, official ISK exchange rate, government bond yields, OMX Iceland index, credit |
| **Fiscal & external** | Treasury accounts, general government deficit and debt, balance of payments, reserves |
| **Calendar, methods, status** | Hagstofa/Seðlabanki release calendar, how each measure is built, freshness of every series |

## How the data stays current

- A **nightly harvest** (`.github/workflows/harvest.yml`, 05:17 UTC — Iceland is UTC year-round) runs every `fetch: auto` series: fetch → validate → publish as tidy CSV under `data/series/`, with metadata in `data/meta/` and health in `data/status.json`. It commits only when something changed; the site redeploys after every commit.
- **A failed fetch never overwrites good data.** The series is marked stale in `data/status.json` and the run fails loudly; nothing in `data/series/` is touched.
- **Sources are keyless and public**: Hagstofa's PxWeb API (JSON-stat2, CC BY 4.0, 30 calls/s), Seðlabanki's NSDP SDMX feed, OECD and Eurostat. `check-secrets.yml` (gitleaks) guards against accidental key commits later.
- **Licences are respected per series**: each `registry/series/*.yaml` records `licence` and whether the series may be offered for download.

## Repository layout

```
site.config.yaml    the site's name, tagline, brand, conventions (the name lives only here)
registry/           one YAML per series (source, licence, checks, pages) + release calendars + backlog
pipelines/          Python: core plumbing, one source module per provider, site-data build
  sources/hagstofa.py       Statistics Iceland PxWeb API client
  sources/sedlabanki.py     Central Bank of Iceland NSDP/SDMX client
data/               published series (CSV), metadata, status (committed); raw downloads (git-ignored)
measures/           measures we build ourselves (pattern ported from econvitals/replication, CC0)
site/               Astro static site; reads the JSON that pipelines/build writes to site/public/data
scripts/, tools/    registry validation, name check, measure checks
tests/              offline tests (registry, parsers, publishing)
docs/guidebook/     how everything works
```

## Running it locally

You need Python 3.12+ with [uv](https://docs.astral.sh/uv/), and Node 20+ for the site.

```bash
uv sync                                # Python dependencies
make check                             # registry validation + name check + tests
make update SOURCE=cpi_headline        # run one series end to end (needs network)
make update-auto                       # all fetch:auto series
make build                             # build site JSON + the Astro site into site/dist
make dev                               # local site with live reload
```

## Data sources and licences

| Provider | API | Licence |
|---|---|---|
| Hagstofa Íslands (Statistics Iceland) | PxWeb API, `https://px.hagstofa.is/pxen/api/v1/en/` (no key, 30 calls/s, 150k values/call) | CC BY 4.0 |
| Seðlabanki Íslands (Central Bank) | NSDP SDMX, `https://data.sedlabanki.is/`; databank.is | public statistics |
| OECD | SDMX, country `ISL` | CC BY 4.0 |
| Eurostat | JSON-stat, geo `IS` | CC BY 4.0 |

Code in this repository is MIT-licensed; data files carry the licence recorded per series in the registry.
