# 500-word Moodle Description (DRAFT)

> Word count: ~440 — fits the 500-word ceiling. Paste into the Moodle form, edit personal voice as needed.

---

**Domain, Why, Who**

Every Australian summer, Port Phillip Bay fills with swimmers — but the water isn't always as clean as it looks. This visualisation tells the story of *when*, *where*, and *why* bacteria levels spike at Melbourne's beaches. The audience is the average Victorian: someone deciding whether to drive 90 minutes to Sorrento or just walk to St Kilda. The "Why?" is practical safety — EPA bulletins exist but are rarely read. By turning six years of monitoring into a scrollable narrative, this work makes that data legible to the public.

**What — Data**

Two real public sources are combined. The **EPA Victoria Beach Report** (CC BY 4.0) provides 5,416 scheduled routine enterococci samples (plus 206 follow-up resamples excluded from headline summaries) taken at 36 Port Phillip Bay beaches between January 2020 and December 2025. The **Bureau of Meteorology** supplies daily rainfall from the Melbourne Olympic Park gauge — the closest reliable station to the bay's eastern shore. A Python preprocessing pipeline merges them on date, joins beaches to geographic regions, recodes "<10" detection-limit values to 5 (the standard convention for censored bacterial data), and unifies a 2022 EPA site renumbering (Portarlington 99760 → 99761). The cleaned master table feeds seven derived aggregates used by individual charts.

**How — Idioms and rationale**

Eleven Vega-Lite charts move the reader through six chapters — *Where, How dirty, When, Why, Region, Verdict* — following Munzer's *What / Why / How* decomposition (what data, why this task for whom, how to encode). Standard idioms locate (point map), rank (horizontal bar), and quantify (stacked bar). Six custom idioms carry the story:

- A **dark-mode locator basemap** opens the story with all 36 EPA sites overlaid on a vector road network, sized by long-term bacteria load and coloured by water-quality band.
- A **radial chord** unfolds the bay's 36 beaches into a clockwise ring around an inner-disk centroid, ray length keyed to mean enterococci.
- A **beach × month heat map** sorted by yearly mean exposes the "summer dirty band" running across the bay's worst sites.
- A **beach-eras dumbbell** pairs each beach's 2020-22 mean with its 2023-25 mean, isolating the five biggest declines and five biggest improvements — the bay is polarising, not homogenising.
- A **marginal year × month risk calendar** collapses six years onto a 12-cell grid with in-cell percentages plus month and year margin means, making outlier months (Nov 2022, Nov 2025, Apr 2024 — all near 30% Poor) instantly visible.
- A final **rain × month decision matrix**, facetted by region, lets a reader look up "today's risk" in two glances — the climax that turns analysis into action.

EPA Beach Action Value thresholds (Good ≤ 35, Poor > 200 orgs/100mL, single-sample basis) are shown as dashed reference lines on every continuous chart. Inline callouts highlight the worst single month, the bay's three most-failed beaches, and the heavy-rain "danger zone".

Typography pairs **Playfair Display** (display) with **Inter** (body) for an editorial feel matching the long-read narrative. Layout is single-column, card-stacked, 880 px wide — so the page reads like a magazine spread without horizontal scrolling on a small laptop. The colour scale (green / amber / red) follows EPA's own rating bands rather than an arbitrary palette.

**AI acknowledgment**

Generative AI (Claude) was used for code scaffolding, data preprocessing, and chart specification drafting. All design decisions, narrative writing, and final review by the author.
