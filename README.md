# Can We Swim Today?

A data visualisation telling the story of water quality at Melbourne's beaches —
when, where, and why it's actually safe to swim.

**Live site:** _to be deployed_

**Author:** Jiahui · FIT2179 Data Visualisation 2 · Monash University · 2026

---

## What this is

A single-page data story built with Vega-Lite, exploring six years of EPA Victoria
beach water quality monitoring (2020-2025) combined with Bureau of Meteorology
rainfall data. Eleven interconnected charts walk a general audience through:

1. **Where** the bay's monitoring sites are
2. **How dirty** each beach actually gets
3. **When** during the year and across years bacteria peak
4. **Why** rainfall is the strongest predictor
5. **Where** geographically the bay's cleanest and dirtiest regions are
6. **The verdict** — a simple lookup table for "should I swim today?"

## Stack

- **Vega-Lite 5.21** — every chart is a separate `.vg.json` spec
- **vega-embed 6.26** — runtime renderer
- **Plain HTML/CSS/JS** — no framework, no build step
- **Inter + Playfair Display** (Google Fonts)
- **Python 3 + pandas** for one-time data preprocessing

## Project layout

```
fit2179-dv2/
├── index.html              Single-page entry, 6 chapters
├── main.js                 Embeds all 10 charts via vegaEmbed
├── style.css               Card-based layout, hero + chapter cards + footer
├── data/
│   ├── raw/                Original source CSVs (committed for reproducibility)
│   │   ├── beach.csv
│   │   ├── sites.csv
│   │   └── rainfall.csv
│   ├── master.csv          Joined, cleaned, with derived fields
│   ├── beach_summary.csv   Per-beach aggregates
│   ├── monthly_by_beach.csv
│   ├── rainfall_impact.csv
│   ├── decision_matrix.csv
│   ├── year_month_calendar.csv
│   ├── region_summary.csv
│   └── states.geojson      Map base (Australian state boundaries)
├── charts/
│   ├── 00-bay-locator.vg.json          Port Phillip Bay basemap with 36 monitoring sites
│   ├── 01-beach-locations.vg.json      Radial chord — 36 beaches arranged clockwise
│   ├── 02-avg-quality-map.vg.json      Unfolded skyline ranking (same order as Chart 1)
│   ├── 03-seasonal-heatmap.vg.json     Top-10 worst beach × month heatmap
│   ├── 04-rainfall-scatter.vg.json     Rainfall vs bacteria scatter + regression
│   ├── 05-beach-eras-dumbbell.vg.json  2020-22 vs 2023-25 dumbbell (5 worse + 5 better)
│   ├── 06-rain-bucket-bar.vg.json      Stacked bar of Good/Caution/Poor by rain bucket
│   ├── 07-ranking-bar.vg.json          Top-10 dirtiest beaches ranked
│   ├── 08-risk-calendar.vg.json        Year × month grid with marginal means
│   ├── 09-region-box.vg.json           Region bar + per-beach strip plot
│   └── 10-decision-matrix.vg.json      Regional "Should I swim?" facet lookup
├── scripts/
│   └── preprocess.py       Generates the aggregated CSVs
├── sketch.pdf              Hand-drawn design sketch
└── README.md
```

## Data sources

| Source | What | License |
|--------|------|---------|
| [EPA Victoria Beach Report](https://discover.data.vic.gov.au/dataset/beach-report-enterococci-data) | Enterococci sampling at 36 Port Phillip Bay beaches, 2013-2025 | CC BY 4.0 |
| [Bureau of Meteorology](http://www.bom.gov.au/climate/data/) | Daily rainfall, Melbourne Olympic Park gauge, 2020-2025 | CC BY 3.0 AU |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Port Phillip Bay coastline (`natural=bay` relation 1221199), Melbourne motorways, metropolitan railway — extracted via the Overpass API and Douglas-Peucker simplified | ODbL |
| [rowanhogan / australian-states](https://github.com/rowanhogan/australian-states) | Australian state boundary GeoJSON (legacy reference; no longer rendered) | CC0 |

## Running locally

```bash
# 1. (one-time) regenerate aggregated CSVs from raw data
python3 scripts/preprocess.py

# 2. serve over HTTP (CORS requires non-file:// protocol for CSVs)
python3 -m http.server 8765

# 3. open
open http://localhost:8765/
```

## Methodology notes

- **Detection limit handling**: EPA reports some values as below a stated limit
  (for example `<10`, `<20`, `<38`, or `<130`). Each censored row is recoded to
  half of its own reported limit, the standard convention for censored bacterial data.
- **Site ID merging**: EPA renumbered the Portarlington site in October 2022
  (`99760` → `99761`). The two IDs are merged to a single beach for time-series
  continuity.
- **Region assignment**: Regions are assigned from an explicit EPA `site_id` map,
  rather than inferred from latitude/longitude thresholds.
- **Routine samples**: Headline aggregates (`beach_summary`, `monthly_by_beach`,
  `rainfall_impact`, `decision_matrix`, `year_month_calendar`, and
  `region_summary`) use scheduled Routine samples only. Resamples remain in
  `master.csv` but are excluded from those summaries to avoid double-counting
  follow-up tests triggered by known incidents.
- **Safety thresholds**: EPA Beach Action Values used throughout — Good ≤ 35,
  Caution 35-200, Poor > 200 organisms / 100mL. The 200 cutoff is used here as
  a single-sample threshold; this project does not compute rolling geomeans.
- **Rainfall lag**: Each sample is matched against rainfall from the previous
  day at Melbourne Olympic Park, the closest BOM station to the bay's eastern shore.
  This single-gauge approximation cannot capture local showers at every beach.

## AI acknowledgment

Generative AI (Claude, Anthropic) was used to scaffold code structure,
preprocess data, draft chart specifications, and write narrative prose.
All design decisions, data interpretation, and final review were performed
by the author.

## License

Code: MIT. Data: as per upstream sources (see table above).
