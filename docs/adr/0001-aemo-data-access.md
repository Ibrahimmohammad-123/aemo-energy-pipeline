# ADR 0001: AEMO Data Access Approach

## Status

Accepted — 9 July 2026

## Context

AEMO changed its data access setup in April 2026, and a lot of existing tutorials that scrape the old NEMweb URLs are now out of date. Before writing any ingestion code, I checked what the current public access method actually is.

Two options were checked:

1. **`https://dev.aemo.com.au`** — AEMO's REST API portal. This is for accredited market participants submitting bids, registrations, and settlement data. There's no way to get access as an outside developer, and it's not built for pulling public dispatch/price data anyway. Not usable here.

2. **NEMweb bulk data files** — still public and still updated in real time. The docs moved to `web.nemweb.com.au`, but the actual report files are still served as plain HTTPS directory listings:
   - `https://nemweb.com.au/Reports/CURRENT/` — rolling ~24–48h of recent files
   - `https://nemweb.com.au/Reports/ARCHIVE/` — last ~13 months

   Confirmed both are live via a direct HTTPS GET (plain directory listing, no login, no API key).

### Reports used

| Data | Folder | Filename pattern | Cadence |
|---|---|---|---|
| Dispatch price (regional reference price) | `Reports/CURRENT/DispatchIS_Reports/` | `PUBLIC_DISPATCHIS_<YYYYMMDDHHmm>_<sequence>.zip` | 5 min |
| Generation by unit (SCADA) | `Reports/CURRENT/Dispatch_SCADA/` | `PUBLIC_DISPATCHSCADA_<YYYYMMDDHHmm>_<sequence>.zip` | 5 min |
| Generator / fuel-type reference | `Reports/CURRENT/CDEII/CO2EII_AVAILABLE_GENERATORS.CSV` | fixed filename, plain CSV | updated periodically |

The CDEII file maps `DUID → REGIONID → fuel type → emissions factor` in one small CSV, which is enough to join generation data to fuel type and region without needing AEMO's much bigger participant registration file.

### File format

Each report is a CSV where every row starts with `C` (header/comment), `I` (declares the column names for the section that follows), or `D` (a data row for the most recent `I` header). A single file can contain more than one table, each with its own `I` row, so it can't just be read with `pd.read_csv` — it needs a proper parser. Example:

```
C,SETP.WORLD,CO2EII_AVAILABLE_GENERATORS_WEB,AEMO,PUBLIC,2026/05/29,11:59:49,...
I,CO2EII,PUBLISHING,1,STATIONNAME,DUID,GENSETID,REGIONID,CO2E_EMISSIONS_FACTOR,CO2E_ENERGY_SOURCE,CO2E_DATA_SOURCE
D,CO2EII,PUBLISHING,1,"Appin Power Plant",APPIN,APPIN,NSW1,0.56318004,"Coal seam methane","NGA 2024"
```

### NOTE: timestamps are interval-end

AEMO timestamps mark the **end** of the interval, not the start — a row timestamped `14:00` covers `13:30–14:00`. Worth writing down so it doesn't get mixed up later when joining price and demand data.

### Alternatives considered

- **`dev.aemo.com.au` REST APIs** — rejected, participant-accredited, not public.
- **NEMOSIS / nem-data** — existing Python packages that already wrap NEMweb access. Not used on purpose — writing the client and parser myself is the point of this project.

## Decision

Ingest directly from NEMweb (`Reports/CURRENT/` and `Reports/ARCHIVE/`) over plain HTTPS, no authentication needed. Use `DispatchIS_Reports` (price) and `Dispatch_SCADA` (generation) as the two time-series sources, and `CDEII` as the fuel-type/region reference. Write a custom parser for the `C`/`I`/`D` row format.

## Consequences

- No credentials needed for ingestion, which keeps the client and CI simple.
- The custom parser is the trickiest part of the project and needs solid test coverage.
- Timestamps from these reports are period-end and should be treated that way consistently through the pipeline.
