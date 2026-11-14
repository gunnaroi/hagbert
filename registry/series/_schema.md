# Series yaml schema

`scripts/validate_registry.py` enforces this. Required fields:

| Field | Type | Allowed |
|---|---|---|
| id | str | lower_snake, equals the filename, unique |
| title, short_title | str | non-empty |
| area | str | growth, inflation, jobs, activity, money, markets, fiscal, external, housing, population |
| source.agency, source.dataset, source.module | str | module path exists under the repo root |
| source.url | str | landing page of the release/table |
| licence | str | `CC-BY-4.0`, `CC0`, `show-only`, `unverified`, or `other:<text>` |
| downloadable | bool | must be false when licence is `show-only` or `unverified` |
| fetch | str | auto (GitHub Actions nightly) | manual |
| frequency | str | D, W, F, M, Q, A |
| unit | str | non-empty |
| transforms | list | level, mom, yoy, annualized_3m, annualized_6m (computed at site build) |
| release.calendar, release.rule, release.lag_days | str/str/int | calendar names a file in registry/calendar/ or is `none` |
| validation.range | [min, max] | plausible range for the stored values |
| validation.revision_alert | number | % change in a past value that flags a large revision |
| pages | list of {page, section} | page must be a planned page in registry/backlog.yaml |
| original | bool | true if we construct it (method documented in measures/) |
| step | bool | true for values that hold until changed (policy rates): charts draw steps |
| verified_against | list of {url, checked_on, by} | must be non-empty before a series goes live |
| owner, notes | str | |

Provider-specific fetch fields live under `source.` (e.g. `table`, `selection`, `time_dim`,
`item_dim`, `item_code` for Hagstofa PxWeb; `dataflow`, `key` for Seðlabanki SDMX).
