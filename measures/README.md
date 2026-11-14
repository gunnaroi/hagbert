# Measures we build ourselves

Some charts on the site are calculated here rather than republished from an agency — the
"house" measures. This folder follows the pattern of
[econvitals/replication](https://github.com/econvitals/replication) (licence CC0, credited
here): one folder per measure with

- `README.md` — what the measure is, where it appears on the site, the exact data it uses,
  and how closely the script matches the published figure;
- `replicate.py` — rebuilds it from the series in `data/series/` (never from the network);
- `check.json` — which outputs must match which published series, over how many recent
  periods, within what tolerance.

`tools/check_all.py` runs every `replicate.py` and checks the outputs; it runs nightly in CI.
A failure never touches `data/` — it just fails.

Planned first measures (from the econvitals methods page, rebuilt on Icelandic data):
underlying-inflation composites (median of 3/6/12-month rates across CPI measures), inflation
dispersion across COICOP items, labor-market tightness z-scores, and the home-page
activity × inflation composites.
