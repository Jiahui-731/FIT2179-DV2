"""
FIT2179 DV2 — Data preprocessing
Read 3 raw CSVs and write per-chart CSVs.
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"


def load():
    beach = pd.read_csv(RAW / "beach.csv")
    sites = pd.read_csv(RAW / "sites.csv")
    rain = pd.read_csv(RAW / "rainfall.csv")
    return beach, sites, rain


SITE_ID_ALIAS = {
    99760: 99761,
}

SITE_REGION = {
    **dict.fromkeys([99290, 99520, 99280, 99530, 99550, 99240, 99993, 99994, 99992],
                    "Mornington Peninsula"),
    **dict.fromkeys([99500, 99510, 99730, 99761, 99770, 99998],
                    "Western Shore"),
    **dict.fromkeys([99020, 99660, 99700, 99690, 99710, 99650, 99997, 99991, 99060],
                    "Inner North"),
}


def normalize(beach, sites, rain):
    beach = beach.rename(columns={
        "Site ID": "site_id",
        "Site Name": "site_name_raw",
        "Sample datetime": "date",
        "Enterococci value (orgs/100 mL)": "enterococci_raw",
        "Enterococci qualifier": "qualifier",
        "Sample type": "sample_type",
    })
    sites = sites.rename(columns={"site_ID": "site_id"})

    beach["site_id"] = beach["site_id"].replace(SITE_ID_ALIAS)

    beach["enterococci"] = beach.apply(
        lambda r: r["enterococci_raw"] / 2 if r["qualifier"] == "<" else r["enterococci_raw"], axis=1
    )

    beach["date"] = pd.to_datetime(beach["date"]).dt.strftime("%Y-%m-%d")
    rain["date"] = pd.to_datetime(rain["date"]).dt.strftime("%Y-%m-%d")
    return beach, sites, rain


def safety_label(v):
    """EPA Beach Action Values: 35 and 200 on a single-sample basis."""
    if v <= 35:
        return "Good"
    if v <= 200:
        return "Caution"
    return "Poor"


def assign_region(site_id):
    """4 geographical clusters around Port Phillip Bay, keyed by EPA site ID."""
    if pd.isna(site_id):
        return None
    return SITE_REGION.get(int(site_id), "Eastern Bayside")


def build_master(beach, sites, rain):
    rain_lag1 = rain.assign(
        date=(pd.to_datetime(rain["date"]) + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    ).rename(columns={"rainfall": "rainfall_yesterday"})

    rain_lag2 = rain.assign(
        date=(pd.to_datetime(rain["date"]) + pd.Timedelta(days=2)).dt.strftime("%Y-%m-%d")
    ).rename(columns={"rainfall": "rainfall_2days_ago"})

    master = (
        beach
        .merge(sites[["site_id", "site_name", "water_body", "latitude", "longitude"]],
               on="site_id", how="left")
        .merge(rain[["date", "rainfall"]], on="date", how="left")
        .merge(rain_lag1, on="date", how="left")
        .merge(rain_lag2, on="date", how="left")
    )

    master["safety"] = master["enterococci"].apply(safety_label)
    master["year"] = pd.to_datetime(master["date"]).dt.year
    master["month"] = pd.to_datetime(master["date"]).dt.month
    master["month_name"] = pd.to_datetime(master["date"]).dt.strftime("%b")
    master["dayofyear"] = pd.to_datetime(master["date"]).dt.dayofyear
    master["weekofyear"] = pd.to_datetime(master["date"]).dt.isocalendar().week.astype(int)
    master["region"] = master["site_id"].apply(assign_region)

    def rain_bucket(r):
        if pd.isna(r):
            return "Unknown"
        if r == 0:
            return "Dry (0mm)"
        if r < 5:
            return "Light (<5mm)"
        if r < 20:
            return "Moderate (5-20mm)"
        return "Heavy (20mm+)"
    master["rain_yesterday_bucket"] = master["rainfall_yesterday"].apply(rain_bucket)

    master = master[[
        "site_id", "site_name", "water_body", "region",
        "latitude", "longitude",
        "date", "year", "month", "month_name", "dayofyear", "weekofyear",
        "enterococci", "qualifier", "safety",
        "rainfall", "rainfall_yesterday", "rainfall_2days_ago", "rain_yesterday_bucket",
        "sample_type",
    ]]
    return master


def routine_samples(master):
    """Headline charts use scheduled Routine samples; resamples stay in master.csv only."""
    return master[master["sample_type"] == "Routine"].copy()


def build_summary(master):
    """Per-beach aggregate, used by the locator map and ranking chart."""
    routine = routine_samples(master)
    summary = (
        routine.dropna(subset=["site_name"])
        .groupby(["site_id", "site_name", "region", "water_body", "latitude", "longitude"])
        .agg(
            avg_enterococci=("enterococci", "mean"),
            median_enterococci=("enterococci", "median"),
            max_enterococci=("enterococci", "max"),
            samples=("enterococci", "count"),
            poor_pct=("safety", lambda x: (x == "Poor").mean() * 100),
            good_pct=("safety", lambda x: (x == "Good").mean() * 100),
        )
        .round(2)
        .reset_index()
    )
    return summary


def build_monthly(master):
    """Per-beach × month aggregate for the seasonal heatmap."""
    routine = routine_samples(master)
    monthly = (
        routine.dropna(subset=["site_name"])
        .groupby(["site_name", "month", "month_name"])
        .agg(
            avg_enterococci=("enterococci", "mean"),
            samples=("enterococci", "count"),
            poor_pct=("safety", lambda x: (x == "Poor").mean() * 100),
        )
        .round(2)
        .reset_index()
    )
    return monthly


def build_beach_radial(summary):
    """Radial chord layout — beaches sorted clockwise around bay perimeter.
    Ray length = sqrt(avg) for visual balance."""
    import math
    bay_center_lon = 144.85
    bay_center_lat = -38.10
    cx, cy = 360.0, 380.0
    r_inner = 195.0
    LEN_K = 6.5

    name_short_map = {
        "Frankston Surf Life Saving Club": "Frankston SLC",
        "Carrum Surf Life Saving Club": "Carrum SLC",
        "Mornington Life Saving Club": "Mornington LSC",
        "Aspendale Life Saving Club": "Aspendale LSC",
        "Brighton Life Saving Club": "Brighton LSC",
        "Black Rock Life Saving Club": "Black Rock LSC",
        "Mt Martha Life Saving Club": "Mt Martha LSC",
        "South Melbourne Life Saving Club": "South Melbourne LSC",
        "Rosebud Life Saving Club": "Rosebud LSC",
        "Seaford Life Saving Club": "Seaford LSC",
        "Frankston Coast Guard": "Frankston Coast Guard",
        "Portarlington Beach (new site)": "Portarlington",
    }

    rows = []
    for _, b in summary.iterrows():
        dy = b.latitude - bay_center_lat
        dx = b.longitude - bay_center_lon
        atan_rad = math.atan2(dy, dx)
        cw_north_deg = (90.0 - math.degrees(atan_rad)) % 360.0
        math_deg_norm = (90.0 - cw_north_deg) % 360.0
        math_rad = math.radians(math_deg_norm)

        ray_len = math.sqrt(b.avg_enterococci) * LEN_K
        r_outer = r_inner + ray_len
        r_dot = r_outer
        r_label = r_outer + 11

        inner_x = cx + r_inner * math.cos(math_rad)
        inner_y = cy - r_inner * math.sin(math_rad)
        dot_x = cx + r_dot * math.cos(math_rad)
        dot_y = cy - r_dot * math.sin(math_rad)
        label_x = cx + r_label * math.cos(math_rad)
        label_y = cy - r_label * math.sin(math_rad)

        # Radial label rotation: text reads outward along ray
        # Right half (math_deg -90 to 90): rotation = -math_deg, anchor left
        # Left half: rotation = -math_deg + 180, anchor right
        if 90 < math_deg_norm < 270:
            label_angle = (-math_deg_norm + 180) % 360
            align = "right"
        else:
            label_angle = (-math_deg_norm) % 360
            align = "left"

        rows.append({
            "site_name": b.site_name,
            "name_short": name_short_map.get(b.site_name, b.site_name),
            "region": b.region,
            "avg_enterococci": b.avg_enterococci,
            "poor_pct": b.poor_pct,
            "samples": b.samples,
            "cw_north_deg": round(cw_north_deg, 2),
            "inner_x": round(inner_x, 2), "inner_y": round(inner_y, 2),
            "dot_x": round(dot_x, 2), "dot_y": round(dot_y, 2),
            "label_x": round(label_x, 2), "label_y": round(label_y, 2),
            "label_align": align,
            "label_angle": round(label_angle, 2)
        })
    df = pd.DataFrame(rows).sort_values("cw_north_deg").reset_index(drop=True)
    df["order"] = df.index
    return df


def build_beach_map(summary):
    """Geographic spike map data — actual lat/lon + spike end coords.
    Spike length = sqrt(avg) * SPIKE_FACTOR (degrees).
    Spike direction = outward radial from bay center (so spike points 'into the land',
    visually echoing the stormwater origin of contamination)."""
    import math
    bay_center_lon = 144.85
    bay_center_lat = -38.10
    SPIKE_FACTOR = 0.0048

    name_short_map = {
        "Frankston Surf Life Saving Club": "Frankston SLC",
        "Carrum Surf Life Saving Club": "Carrum SLC",
        "Mornington Life Saving Club": "Mornington LSC",
        "Aspendale Life Saving Club": "Aspendale LSC",
        "Brighton Life Saving Club": "Brighton LSC",
        "Black Rock Life Saving Club": "Black Rock LSC",
        "Mt Martha Life Saving Club": "Mt Martha LSC",
        "South Melbourne Life Saving Club": "South Melbourne LSC",
        "Rosebud Life Saving Club": "Rosebud LSC",
        "Seaford Life Saving Club": "Seaford LSC",
        "Portarlington Beach (new site)": "Portarlington",
    }
    callout_specs = {
        "Frankston Coast Guard": {"label": "Frankston CG", "lon_offset": 0.0, "lat_offset": 0.0},
        "Carrum Surf Life Saving Club": {"label": "Carrum SLC", "lon_offset": 0.0, "lat_offset": 0.0},
        "Port Melbourne": {"label": "Port Melbourne", "lon_offset": -0.058, "lat_offset": -0.108},
    }

    sorted_summary = summary.sort_values("avg_enterococci", ascending=False).reset_index(drop=True)
    top_worst = set(sorted_summary.head(3)["site_name"].tolist())

    rows = []
    for _, b in summary.iterrows():
        dx = b.longitude - bay_center_lon
        dy = b.latitude - bay_center_lat
        norm = math.sqrt(dx * dx + dy * dy)
        if norm == 0:
            ux, uy = 0.0, 1.0
        else:
            ux, uy = dx / norm, dy / norm
        length_deg = math.sqrt(b.avg_enterococci) * SPIKE_FACTOR
        spike_end_lon = b.longitude + ux * length_deg
        spike_end_lat = b.latitude + uy * length_deg

        spec = callout_specs.get(b.site_name, {"label": "", "lon_offset": 0.0, "lat_offset": 0.0})
        callout_lon = spike_end_lon + spec["lon_offset"]
        callout_lat = spike_end_lat + spec["lat_offset"]
        rows.append({
            "site_id": b.site_id,
            "site_name": b.site_name,
            "name_short": name_short_map.get(b.site_name, b.site_name),
            "callout_label": spec["label"],
            "callout_lon": round(callout_lon, 6),
            "callout_lat": round(callout_lat, 6),
            "region": b.region,
            "lat": round(b.latitude, 6),
            "lon": round(b.longitude, 6),
            "spike_end_lat": round(spike_end_lat, 6),
            "spike_end_lon": round(spike_end_lon, 6),
            "avg_enterococci": round(b.avg_enterococci, 1),
            "samples": int(b.samples),
            "is_top3_worst": 1 if b.site_name in top_worst else 0,
        })
    return pd.DataFrame(rows)


def build_beach_bivariate(master):
    """Per-beach baseline (dry-day avg) + rain sensitivity (wet - dry).
    Each site is classified into a 3x3 bivariate cell.
    Used by chart 0 (the bivariate risk map)."""
    routine = routine_samples(master).dropna(subset=["site_name", "rainfall_yesterday", "enterococci"])

    BASELINE_LOW, BASELINE_HIGH = 80, 180
    SENS_LOW, SENS_HIGH = 0, 100

    name_short_map = {
        "Frankston Surf Life Saving Club": "Frankston SLC",
        "Carrum Surf Life Saving Club": "Carrum SLC",
        "Mornington Life Saving Club": "Mornington LSC",
        "South Melbourne Life Saving Club": "South Melb LSC",
        "Brighton Life Saving Club": "Brighton LSC",
        "Aspendale Life Saving Club": "Aspendale LSC",
        "Black Rock Life Saving Club": "Black Rock LSC",
        "Mt Martha Life Saving Club": "Mt Martha LSC",
        "Rosebud Life Saving Club": "Rosebud LSC",
        "Seaford Life Saving Club": "Seaford LSC",
        "Portarlington Beach (new site)": "Portarlington",
    }

    callout_specs = {
        "Port Melbourne": {"label": "Port Melbourne", "lon_offset": -0.058, "lat_offset": -0.06, "subtitle": "Dirty AND rain-sensitive"},
        "Sandridge": {"label": "Sandridge", "lon_offset": 0.0, "lat_offset": 0.0, "subtitle": "Sens +532 after rain"},
        "Werribee Sth": {"label": "Werribee Sth", "lon_offset": 0.0, "lat_offset": 0.0, "subtitle": "Sens +379"},
        "Frankston Coast Guard": {"label": "Frankston CG", "lon_offset": 0.0, "lat_offset": 0.0, "subtitle": "Always dirty (rain doesn't matter)"},
        "Mornington Life Saving Club": {"label": "Mornington LSC", "lon_offset": 0.0, "lat_offset": 0.0, "subtitle": "Same"},
    }

    rows = []
    for site, g in routine.groupby("site_id"):
        dry = g[g["rainfall_yesterday"] <= 5]
        wet = g[g["rainfall_yesterday"] > 5]
        if len(dry) < 5 or len(wet) < 5:
            continue
        baseline = dry["enterococci"].mean()
        wet_avg = wet["enterococci"].mean()
        sens = wet_avg - baseline

        b_class = "low" if baseline <= BASELINE_LOW else ("mid" if baseline <= BASELINE_HIGH else "high")
        s_class = "low" if sens <= SENS_LOW else ("mid" if sens <= SENS_HIGH else "high")
        cell = f"{b_class}_{s_class}"

        site_name = g["site_name"].iloc[0]
        spec = callout_specs.get(site_name, {"label": "", "lon_offset": 0.0, "lat_offset": 0.0})
        lon = float(g["longitude"].iloc[0])
        lat = float(g["latitude"].iloc[0])
        rows.append({
            "site_id": site,
            "site_name": site_name,
            "name_short": name_short_map.get(site_name, site_name),
            "callout_label": spec["label"],
            "callout_lon": round(lon + spec["lon_offset"], 6),
            "callout_lat": round(lat + spec["lat_offset"], 6),
            "region": g["region"].iloc[0],
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "baseline": round(baseline, 1),
            "wet_avg": round(wet_avg, 1),
            "sensitivity": round(sens, 1),
            "baseline_class": b_class,
            "sens_class": s_class,
            "bivariate_cell": cell,
            "n_dry": int(len(dry)),
            "n_wet": int(len(wet)),
        })
    return pd.DataFrame(rows)


def build_rainfall_breakdown(master):
    """Per rain bucket × safety category share (% of routine samples)."""
    routine = routine_samples(master).dropna(subset=["site_name", "rain_yesterday_bucket"])
    routine = routine[routine["rain_yesterday_bucket"] != "Unknown"]
    df = (routine.groupby(["rain_yesterday_bucket", "safety"])
                 .agg(n=("enterococci", "size"))
                 .reset_index())
    total = df.groupby("rain_yesterday_bucket")["n"].transform("sum")
    df["pct"] = (df["n"] / total * 100).round(2)
    bucket_order = ["Dry (0mm)", "Light (<5mm)", "Moderate (5-20mm)", "Heavy (20mm+)"]
    safety_order = {"Good": 0, "Caution": 1, "Poor": 2}
    df["bucket_idx"] = df["rain_yesterday_bucket"].apply(lambda b: bucket_order.index(b) if b in bucket_order else 99)
    df["safety_idx"] = df["safety"].map(safety_order)
    df = df.sort_values(["bucket_idx", "safety_idx"]).drop(columns=["bucket_idx"])
    return df


def build_beach_eras(master, era_a=(2020, 2022), era_b=(2023, 2025)):
    """Per-beach mean enterococci in two 3-year eras, for the dumbbell trend chart."""
    routine = routine_samples(master).dropna(subset=["site_name", "region"])
    routine = routine.assign(era=routine["year"].apply(
        lambda y: "a" if era_a[0] <= y <= era_a[1] else ("b" if era_b[0] <= y <= era_b[1] else None)
    ))
    routine = routine[routine["era"].notna()]

    g = (routine.groupby(["site_id", "site_name", "region", "era"])
                .agg(mean_ent=("enterococci", "mean"),
                     n=("enterococci", "size"),
                     poor_pct=("safety", lambda x: (x == "Poor").mean() * 100))
                .round(2).reset_index())

    wide = g.pivot_table(index=["site_id", "site_name", "region"],
                         columns="era", values=["mean_ent", "n", "poor_pct"]).reset_index()
    wide.columns = ['_'.join(str(c) for c in col if c).strip('_') for col in wide.columns]
    wide["delta"] = (wide["mean_ent_b"] - wide["mean_ent_a"]).round(2)
    wide["pct_change"] = (wide["delta"] / wide["mean_ent_a"] * 100).round(1)
    wide = wide.sort_values("delta", ascending=False).reset_index(drop=True)
    wide["rank"] = wide.index + 1

    long = wide.melt(
        id_vars=["site_id", "site_name", "region", "delta", "pct_change", "rank"],
        value_vars=["mean_ent_a", "mean_ent_b"],
        var_name="era_col", value_name="mean_ent",
    )
    long["era"] = long["era_col"].map({"mean_ent_a": "2020-2022", "mean_ent_b": "2023-2025"})
    long = long.drop(columns=["era_col"])
    long["era_a_mean"] = long["site_id"].map(wide.set_index("site_id")["mean_ent_a"])
    long["era_b_mean"] = long["site_id"].map(wide.set_index("site_id")["mean_ent_b"])
    return wide, long


def build_rainfall_impact(master):
    """Rain-impact aggregate grouped by rain bucket."""
    routine = routine_samples(master)
    impact = (
        routine.dropna(subset=["site_name", "rain_yesterday_bucket"])
        .groupby("rain_yesterday_bucket")
        .agg(
            avg_enterococci=("enterococci", "mean"),
            median_enterococci=("enterococci", "median"),
            samples=("enterococci", "count"),
            poor_pct=("safety", lambda x: (x == "Poor").mean() * 100),
        )
        .round(2)
        .reset_index()
    )
    bucket_order = ["Dry (0mm)", "Light (<5mm)", "Moderate (5-20mm)", "Heavy (20mm+)"]
    impact["order"] = impact["rain_yesterday_bucket"].apply(
        lambda b: bucket_order.index(b) if b in bucket_order else 99
    )
    impact = impact.sort_values("order").drop(columns="order")
    return impact


def main():
    print("Loading raw...")
    beach, sites, rain = load()
    print(f"  beach: {len(beach):,} rows")
    print(f"  sites: {len(sites):,} rows")
    print(f"  rain:  {len(rain):,} rows")

    print("Normalizing...")
    beach, sites, rain = normalize(beach, sites, rain)

    print("Building master...")
    master = build_master(beach, sites, rain)
    master.to_csv(OUT / "master.csv", index=False)
    print(f"  -> master.csv: {len(master):,} rows")

    missing = master[master["site_name"].isna()]
    if len(missing) > 0:
        print(f"  WARN: {len(missing)} rows have no site_name (id mismatch)")
        print("  unmatched site_ids:", missing["site_id"].unique())

    print("Building summary...")
    summary = build_summary(master)
    summary.to_csv(OUT / "beach_summary.csv", index=False)
    print(f"  -> beach_summary.csv: {len(summary)} rows")

    print("Building monthly...")
    monthly = build_monthly(master)
    monthly.to_csv(OUT / "monthly_by_beach.csv", index=False)
    print(f"  -> monthly_by_beach.csv: {len(monthly):,} rows")

    print("Building beach radial layout...")
    radial = build_beach_radial(summary)
    radial.to_csv(OUT / "beach_radial.csv", index=False)
    print(f"  -> beach_radial.csv: {len(radial)} rows")

    print("Building beach geographic map (chart 0 spike-locator, deprecated)...")
    bmap = build_beach_map(summary)
    bmap.to_csv(OUT / "beach_map.csv", index=False)
    print(f"  -> beach_map.csv: {len(bmap)} rows")

    print("Building beach bivariate (chart 0 — risk map)...")
    bbi = build_beach_bivariate(master)
    bbi.to_csv(OUT / "beach_bivariate.csv", index=False)
    print(f"  -> beach_bivariate.csv: {len(bbi)} rows")

    print("Building rainfall breakdown...")
    rb = build_rainfall_breakdown(master)
    rb.to_csv(OUT / "rainfall_breakdown.csv", index=False)
    print(f"  -> rainfall_breakdown.csv: {len(rb)} rows")

    print("Building beach eras (dumbbell)...")
    eras_wide, eras_long = build_beach_eras(master)
    eras_wide.to_csv(OUT / "beach_eras_wide.csv", index=False)
    eras_long.to_csv(OUT / "beach_eras.csv", index=False)
    print(f"  -> beach_eras_wide.csv: {len(eras_wide)} rows")
    print(f"  -> beach_eras.csv: {len(eras_long)} rows")

    print("Building rainfall impact...")
    impact = build_rainfall_impact(master)
    impact.to_csv(OUT / "rainfall_impact.csv", index=False)
    print(f"  -> rainfall_impact.csv: {len(impact)} rows")

    # Decision matrix: rain bucket × month → poor%
    print("Building decision matrix...")
    region_order = ["Western Shore", "Mornington Peninsula", "Eastern Bayside", "Inner North"]
    bucket_order = ["Dry (0mm)", "Light (<5mm)", "Moderate (5-20mm)", "Heavy (20mm+)"]
    decision = (
        routine_samples(master).dropna(subset=["site_name", "region", "rain_yesterday_bucket"])
        .groupby(["region", "rain_yesterday_bucket", "month"])
        .agg(
            poor_pct=("safety", lambda x: (x == "Poor").mean() * 100),
            avg_enterococci=("enterococci", "mean"),
            samples=("enterococci", "count"),
        )
        .round(2).reset_index()
    )
    full_decision_grid = pd.MultiIndex.from_product(
        [region_order, bucket_order, range(1, 13)],
        names=["region", "rain_yesterday_bucket", "month"]
    ).to_frame(index=False)
    decision = full_decision_grid.merge(
        decision, on=["region", "rain_yesterday_bucket", "month"], how="left"
    )
    decision["samples"] = decision["samples"].fillna(0).astype(int)
    decision["region_order"] = decision["region"].apply(
        lambda r: region_order.index(r) if r in region_order else 99
    )
    decision["bucket_order"] = decision["rain_yesterday_bucket"].apply(
        lambda b: bucket_order.index(b) if b in bucket_order else 99
    )
    decision = decision.sort_values(["region_order", "bucket_order", "month"]).drop(
        columns=["region_order", "bucket_order"]
    )
    decision.to_csv(OUT / "decision_matrix.csv", index=False)
    print(f"  -> decision_matrix.csv: {len(decision)} rows")

    # Year × month calendar (simpler than year × week)
    print("Building year-month calendar...")
    calendar = (
        routine_samples(master).dropna(subset=["site_name"])
        .groupby(["year", "month"])
        .agg(
            poor_pct=("safety", lambda x: (x == "Poor").mean() * 100),
            avg_enterococci=("enterococci", "mean"),
            samples=("enterococci", "count"),
        )
        .round(2).reset_index()
    )
    calendar.to_csv(OUT / "year_month_calendar.csv", index=False)
    print(f"  -> year_month_calendar.csv: {len(calendar)} rows")

    # Region distribution
    print("Building region distribution...")
    region = (
        routine_samples(master).dropna(subset=["site_name", "region"])
        .groupby("region")
        .agg(
            beach_count=("site_id", "nunique"),
            samples=("enterococci", "count"),
            avg_enterococci=("enterococci", "mean"),
            median_enterococci=("enterococci", "median"),
            poor_pct=("safety", lambda x: (x == "Poor").mean() * 100),
        )
        .round(2).reset_index()
    )
    region.to_csv(OUT / "region_summary.csv", index=False)
    print(f"  -> region_summary.csv: {len(region)} rows")

    print("\nDone.")


if __name__ == "__main__":
    main()
