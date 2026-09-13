# Power BI Step-by-Step: F1 Race Pace Dashboard (Supabase PostgreSQL)

Build the Power BI version of the F1 analytics project. You will:
1. Put the F1 data into a free Supabase Postgres warehouse
2. Connect Power BI Desktop straight to it
3. Model it as a star schema, write DAX measures
4. Build 4 report pages and publish with scheduled refresh

Time: ~4–6 hours total. Do it in the order below.

---

## Part 0 — Prerequisites (10 min)

- [ ] Power BI Desktop (free): https://powerbi.microsoft.com/desktop
- [ ] Sign in at https://app.powerbi.com with the same Microsoft account
- [ ] A Supabase project (free): https://supabase.com → Sign in with GitHub → **New project**

---

## Part 1 — Set up the warehouse (20 min)

1. In Supabase, open your project.
2. Go to **SQL Editor → New query**, paste the contents of `powerbi/supabase_schema.sql`, click **Run**.
   This creates the three tables `races`, `drivers`, `laps`.
3. Go to **Project Settings → Database** and copy the **Connection string — Session pooler**
   entry (it has the form `postgresql://postgres.<ref>:<password>@...pooler.supabase.com:5432/postgres`).
4. In the repo root, create `.env` from `powerbi/.env.example` and paste the connection string
   in `SUPABASE_DATABASE_URL`. If your password has `@`, `:`, or `/`, URL-encode them
   (`@` → `%40`, `:` → `%3A`, `/` → `%2F`).
5. Ingest the data:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r ingest\requirements.txt
   python ingest\ingest_to_supabase.py --year 2026
   ```

   First run downloads the season from the FastF1 API (~5–10 min), then it might be cached.
   Rerunning is safe — it skips nothing but upserts without duplicates.

6. Verify in Supabase **Table Editor** that `laps` has thousands of rows and `races` contains every
   2026 grand prix (you need Monaco to be listed).

---

## Part 2 — Connect Power BI Desktop (10 min)

1. Open Power BI Desktop. **Get Data → PostgreSQL database** (long list, search "postgres").
2. Fill in:
   - **Server:** `db.<your-ref>.supabase.co` (the hostname after `postgres.` in the connection string)
   - **Database:** `postgres`
3. Choose **DirectQuery or Import?** → use **Import** (easy, supports the free scheduled refresh we want).
4. Credentials → **Database** → username `postgres` + your DB password → Encrypt by default → Connect.

Power BI shows only the **views/tables it can see**. Select all three tables:
`laps`, `drivers`, `races`. Click **Load** (load all three).

> Why this matters: Power BI can't call the FastF1 API itself. The warehouse is the
> "single source of truth" both Power BI and (optionally) your Streamlit app read.

---

## Part 3 — Data types & quick cleanup (10 min)

Open **Model view** (left toolbar, second icon). Click each table and set types in the
**Data** tab if Power BI guessed wrong:

| Table     | Column           | Type          |
|-----------|------------------|---------------|
| races     | event_date       | Date          |
| races     | total_laps       | Whole number  |
| drivers   | driver_number    | Whole number  |
| laps      | lap_time_seconds | Decimal number |
| laps      | lap_number       | Whole number  |
| laps      | tyre_life        | Whole number  |
| laps      | stint            | Whole number  |
| laps      | pit_in/out_time  | Decimal number |

Also in **Transform Data** (Power Query), you can label `is_personal_best` as a True/False
column; leave it for now.

---

## Part 4 — Star schema (model) (10 min)

In **Model view** set up relationships:

1. From **laps → races**: relationship
   - Column(s): `race_season`, `race_round` (multi-column) **or** simpler — create a key column:

   In **Transform Data → races**, add a custom column `race_key`:
   ```
   race_key = Text.From([season]) & "-" & Text.From([round_number])
   ```
   Do the same in `laps`:
   ```
   race_key = Text.From([race_season]) & "-" & Text.From([race_round])
   ```
   Then one clean relationship: **laps[race_key] (many) → races[race_key] (one)**, Cross filter: Single, both directions off.

2. Link **laps → drivers** (per-race driver dimension): in `laps` add
   `driver_race_code`:
   ```
   driver_race_code = Text.From([race_season]) & "-" & Text.From([race_round]) & "-" & [driver_code]
   ```
   in `drivers` add:
   ```
   driver_race_code = Text.From([race_season]) & "-" & Text.From([race_round]) & "-" & [driver_code]
   ```
   Relationship: **laps[driver_race_code] (many) → drivers[driver_race_code] (one)**.

   (If the multi-key version works fine in your Power BI version, use it directly.)

3. **Result:** a star: `races` and `drivers` on the "one" side, `laps` in the middle.

---

## Part 5 — DAX measures (20 min)

In **Report view**, right-click the `laps` table → **New measure**. Paste these:

```dax
// Core pace metrics
Fastest Lap (s)     = MIN(laps[lap_time_seconds])
Avg Pace (s)        = AVERAGE(laps[lap_time_seconds])
Median Pace (s)     = MEDIAN(laps[lap_time_seconds])
Consistency (STDEV) = STDEV.P(laps[lap_time_seconds])

// Driver / race context
Race Count          = DISTINCTCOUNT(laps[race_key])
Driver Count        = DISTINCTCOUNT(laps[driver_code])

// Tyres
Pit Stops           =
    CALCULATE(
        COUNTROWS(laps),
        FILTER(laps, NOT(ISBLANK(laps[pit_in_time])) || NOT(ISBLANK(laps[pit_out_time])))
    )
Best Lap per Compound =
    MINX(VALUES(laps[compound]), MIN(laps[lap_time_seconds]))

// Season-over-season reference
Prev Season Pace    = CALCULATE([Avg Pace (s)], SAMEPERIODLASTYEAR(races[event_date]))
```

> `minx` / time intelligence only behave right when **races[event_date]** is your date table.
> If you get "no date hierarchy", add the `races` table as a **Mark as date table** using
> `event_date` (Table tools → Mark as date table).

---

## Part 6 — Build the 4 pages (1–2 hrs)

### Page 1 — Season Overview
- Add a **Slicer** bound to `races[name]` (dropdown/multi-select).
- **KPIs (Cards):** `Fastest Lap (s)`, `Avg Pace (s)`, `Race Count`.
- **Line chart:** `races[name]` (axis) → `Avg Pace (s)` (values).
- **Bar chart (Top N 5):** `drivers[full_name]` → `Fastest Lap (s)`.
- Optional: a **map** of `races[country]` referencing the races table if the countries resolve.

Title the page *"2026 Season Overview"*.

### Page 2 — Monaco Race Pace (deep-dive)
- Slicer = `races[name]`, set **default to Monaco**.
- **Line chart:** `laps[lap_number]` (axis) → `laps[lap_time_seconds]`, legend `driver_code`.
- **Table:** Driver, `Fastest Lap (s)`, `Avg Pace (s)`, `Consistency (STDEV)` sorted by fastest lap.
- Slider slicer to limit lap numbers if the chart is noisy.

### Page 3 — Tyre Degradation
- **Scatter chart:** `laps[tyre_life]` (x) → `laps[lap_time_seconds]` (y),
  legend `compound`, size maybe lap count.
- Add slicers: driver + compound.
- Adds psychedelic fun, but keep `compound` in the legend = the degradation story.

### Page 4 — Pit Stops & Strategy
- **Table:** `drivers[full_name]` → `Pit Stops`, plus `Best Lap per Compound` matrix
  (rows driver, columns compound, values fastest lap).

---

## Part 7 — Publish & schedule refresh (15 min)

1. **File → Save** the report (save the `.pbix` e.g. in `powerbi/`).
2. **Publish** to your workspace in app.powerbi.com.
3. In the service, open the dataset → **Settings → Scheduled refresh**:
   - Turn **On** Refresh frequency (e.g. Daily 7:00 AM).
   - Set **Refresh credentials**: Database → `postgres` / your password (same as Part 2).
   - Click **Apply**.
4. The first cloud refresh will download from Supabase over the internet — no on-prem gateway needed.

> If the dataset needs the credentials for a direct cloud connection, re-enter them and use
> **Test connection** before saving.

---

## Part 8 — Interview story (2 min)

> "I rebuilt my F1 analytics project in Power BI. The export pipeline takes FastF1 race data into
> a Postgres warehouse on Supabase; Power BI connects to it via the PostgreSQL connector, models it
> as a star schema with `races` and `drivers` as dimensions and `laps` as the fact table, and I wrote
> DAX for pace, consistency and tyre degradation. It publishes to the Power BI service with a
> scheduled refresh — no gateway, free tier."

---

## Troubleshooting

- **"Could not load file" / auth**: verify the password is the **database password**, not the
  anon/service key in project settings. Use URL-decoded real password in Power BI.
- **Relationship "can't be created"**: check columns are the same data type on both sides; the
  key columns must both be text.
- **Table shows mask of zeros with no time**: `lap_time_seconds` got treated as time — re-set
  measure to use the decimal column, not the original `LapTime`.
- **First ingest slow**: normal, it's downloading the season. Reruns use the FastF1 cache.
- **Scheduled refresh fails with "gateway"**: choose "Direct connection" / cloud source, not
  on-prem gateway.

LCR: your instance, 5432, `postgres` schema, tables `public.races`, `public.drivers`, `public.laps`.