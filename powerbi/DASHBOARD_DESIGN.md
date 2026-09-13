# Power BI Dashboard Design — F1 Race Pace

Spec for `Analysis_Dash.pbix`. Canvas: **1920 × 1080**. Data model: `races`, `drivers` (per-race),
`laps` from Supabase Postgres (`F1Supabase` ODBC DSN). Target: portfolio + interview demo.

---

## 0. Fix your current Page 1 before anything else

1. **Clear the slicer filter** — the `races.name` slicer is hard-wired to *Hungarian Grand Prix*.
   Open the visual filter and reset / select-all so the whole season shows. (Re-apply later only if you want a fixed demo state.)
2. **Line chart sort** — `Avg Pace (s)` is sorted descending by value. Change to sort by
   `races[round_number]` ascending so races appear in calendar order.
3. **Bar chart sort** — `Fastest Lap (s)` is sorted descending (slowest first). Set **Top N = 10**,
   sort **ascending** (fastest lap first).

---

## 1. Pre-flight checklist (confirm in Fields pane)

- ☐ `laps` has column **race_key** (needed by `Race Count`)
- ☐ `laps` has column **driver_race_code**
- ☐ `drivers` has columns **race_season**, **race_round**, **driver_race_code**, **full_name**, **team**
- ☐ `races` marked as date table on **event_date** (Table tools → Mark as date table)
- ☐ All 9 measures exist (Section 3)
- ☐ Relationships exist (Section 2)

Missing a column? Add it in **Transform Data** (Power Query) with the M snippets below.

### M: add `race_key`

On the **races** table (custom column):
```
race_key = Text.From([season]) & "-" & Text.From([round_number])
```

On the **laps** table:
```
race_key = Text.From([race_season]) & "-" & Text.From([race_round])
```

### M: add `driver_race_code`

On **laps**:
```
driver_race_code = Text.From([race_season]) & "-" & Text.From([race_round]) & "-" & [driver_code]
```

On **drivers**:
```
driver_race_code = Text.From([race_season]) & "-" & Text.From([race_round]) & "-" & [driver_code]
```

After adding columns: **Close & Apply**. Set both helper columns to **Text** data type.

---

## 2. Relationships (Model view)

| From (many) | To (one) | Column |
|-------------|----------|--------|
| laps | races | `race_key` → `race_key` |
| laps | drivers | `driver_race_code` → `driver_race_code` |

Cross filter direction: **Single** (both). No bidirectional arrows.

---

## 3. Final DAX — create one measure per dialog box

Right-click the **laps** table → New measure → paste ONE of these, click OK, repeat.

| Right-click | Measure | Expression |
|-------------|---------|------------|
| laps | `Fastest Lap (s)` | `MIN(laps[lap_time_seconds])` |
| laps | `Avg Pace (s)` | `AVERAGE(laps[lap_time_seconds])` |
| laps | `Median Pace (s)` | `MEDIAN(laps[lap_time_seconds])` |
| laps | `Consistency (STDEV)` | `STDEV.P(laps[lap_time_seconds])` |
| laps | `Race Count` | `DISTINCTCOUNT(laps[race_key])` |
| laps | `Driver Count` | `DISTINCTCOUNT(laps[driver_code])` |
| laps | `Pit Stops` | `CALCULATE(COUNTROWS(laps), FILTER(laps, NOT(ISBLANK(laps[pit_in_time])) \|\| NOT(ISBLANK(laps[pit_out_time]))))` |
| laps | `Best Lap per Compound` | `MINX(VALUES(laps[compound]), MIN(laps[lap_time_seconds]))` |
| laps | `Prev Season Pace` | `CALCULATE([Avg Pace (s)], SAMEPERIODLASTYEAR(races[event_date]))` |

Notes:
- `Pit Stops` and `Average` names use spaces/parentheses — always reference with brackets `[ ]`.
- If `Prev Season Pace` errors: the `races` table isn't marked as a date table (do it first).
- If `Race Count` errors: `race_key` is missing (add it, Section 1).

---

## 4. Page layout

All coordinates in px on a 1920×1080 page.

### Page 1 — "Season Overview" (you're ~70% done)

| Visual | Type | Position (x, y, w, h) | Fields |
|--------|------|-----------------------|--------|
| S1 | Slicer | 32, 32, 1100, 40 | `races.name` (multi-select) |
| S2 | Slicer (optional) | 1160, 32, 500, 40 | `drivers.team` |
| K1 | Card | 32, 100, 300, 110 | `laps[Fastest Lap (s)]` |
| K2 | Card | 356, 100, 300, 110 | `laps[Avg Pace (s)]` |
| K3 | Card | 680, 100, 300, 110 | `laps[Race Count]` |
| V1 | Line chart | 32, 240, 1240, 520 | Axis `races.name` (sort by `races.round_number` asc)... use `races[round_number]` as Axis instead and format it as the GP name for cleaner order |
| V2 | Bar chart | 1300, 240, 588, 520 | Category `drivers.full_name`, Values `laps[Fastest Lap (s)]`, **Top N 10, ascending** |
| T1 | Table | 32, 800, 1856, 220 | `drivers.full_name`, `drivers.team`, `laps[Fastest Lap (s)]`, `laps[Avg Pace (s)]`, `laps[Consistency (STDEV)]` |

> Tip: to keep a clean calendar order on V1's axis, use **`races.round_number`** as the Axis and set
> the axis label to `races.name` via the data label/category options, or simply sort-on-axis by `round_number`.

### Page 2 — "Monaco Race Pace"

| Visual | Type | Position | Fields |
|--------|------|----------|--------|
| S1 | Slicer | 32, 32, 1000, 40 | `races.name` — pin/filter to **Monaco Grand Prix** for the demo |
| S2 | Slicer | 1060, 32, 828, 40 | `drivers.full_name` (multi-select) |
| V1 | Line chart | 32, 140, 1240, 520 | Axis `laps[lap_number]`, Values `laps[lap_time_seconds]`, Legend `laps[driver_code]` |
| V2 | Slicer (slider) | 32, 700, 1240, 80 | `laps[lap_number]` (range slider) |
| T1 | Table | 1300, 140, 588, 640 | `laps[driver_code]`, `drivers.full_name`, `laps[Fastest Lap (s)]`, `laps[Avg Pace (s)]`, `laps[Consistency (STDEV)]`, `laps[Pit Stops]` |

### Page 3 — "Tyre Degradation"

| Visual | Type | Position | Fields |
|--------|------|----------|--------|
| S1 | Slicer | 32, 32, 900, 40 | `drivers.full_name` |
| S2 | Slicer | 960, 32, 420, 40 | `laps.compound` |
| V1 | Scatter | 32, 140, 1240, 540 | X `laps[tyre_life]`, Y `laps[lap_time_seconds]`, Legend `laps[compound]` |
| M1 | Matrix | 1300, 140, 588, 540 | Rows `drivers.full_name`, Columns `laps.compound`, Values `laps[Best Lap per Compound]` |

### Page 4 — "Pit Stops & Strategy"

| Visual | Type | Position | Fields |
|--------|------|----------|--------|
| V1 | Clustered bar | 32, 140, 900, 460 | Category `drivers.full_name`, Values `laps[Pit Stops]` |
| V2 | Donut | 960, 140, 460, 460 | Legend `laps.compound`, Values `COUNTROWS(laps)` (donut of laps per compound) |
| T1 | Table | 32, 640, 1400, 340 | `laps[driver_code]`, `drivers.full_name`, `laps[lap_number]`, `laps[compound]`, `laps[pit_in_time]`, `laps[pit_out_time]` |
| F1 | Page filter | — | `laps[pit_in_time]` **is not blank** (Values dropdown → filter) |

---

## 5. Publish, refresh, embed

1. **Save** the report as `powerbi\Analysis_Dash.pbix`.
2. **Publish** to your workspace on app.powerbi.com.
3. Open the dataset → **Settings → Scheduled refresh**:
   - Refresh frequency: Daily (e.g. 07:00).
   - Credentials: Database → `postgres` / password → Test connection → Apply.

> **ODBC caveat:** the `F1Supabase` DSN connects over ODBC, which the cloud service treats as a
> gateway-type source. If scheduled refresh in the cloud fails, either accept manual refresh, or
> switch the source to the native PostgreSQL connector later (Part 2 of `POWERBI_STEPBYSTEP.md`)
> and keep Supabase's "Enforce SSL" setting consistent with the chosen connect mode.

4. **Embed for portfolio/README:** in the workspace → report → **Share → Embed report →
   Website or portal** → copy the `https://app.powerbi.com/view?r=...` link.

---

## 6. Interview one-liner (Day 7)

> "I rebuilt my F1 analytics project as a native Power BI dashboard — FastF1 → Postgres warehouse on
> Supabase, modeled as a star schema with `races`/`drivers` dimensions and `laps` as the fact table,
> DAX for pace, consistency and tyre degradation, published with a scheduled refresh. Monaco is the
> deep-dive page."