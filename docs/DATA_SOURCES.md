# Data sources, provenance and reuse

## Primary source (bundled)
| | |
|---|---|
| Publisher | Jordan Department of Statistics (DoS) |
| Dataset | *Monthly Consumer Price Index (2018 = 100)* – "Tables of price indices" |
| Official page | <https://dosweb.dos.gov.jo/economic/price-indices/table-price-indices/> |
| Files | one workbook per year: `https://dosweb.dos.gov.jo/DataBank/Economic/Price_Indices/CPI/{YEAR}.xlsx` (2006 … 2026) |
| Series used | the **All Items** row (headline CPI), 12 monthly values per year |
| Retrieved | recorded in `data/processed/provenance.json` (UTC timestamp, SHA-256 and size of each of the 21 workbooks) |
| Coverage | Jan 2006 – **Sep 2026** (249 months) – the latest month is read from the file, not assumed |
| Base / units | 2018 = 100 (the 2018 average equals 100 exactly), index points |
| Frequency | monthly |
| Seasonal adjustment | not stated by DoS; treated as not seasonally adjusted |
| Transformations | none to the values (full published precision). No interpolation, smoothing or gap filling. |

Since 2006 DoS publishes every year on the 2018 base, so no splicing is done by MIZAN.

## How the data was verified
`python -m mizan ingest` downloads, parses (by header text, never by position) and validates, then records:

1. **Structure:** sorted, unique, no missing months, numeric, positive, plausible range, 2018 average = 100.
2. **DoS internal consistency:** the monthly values reproduce DoS's own *Average* column in all 21 workbooks (±0.01).
3. **Latest official release:** the DoS release of 12 Oct 2026 (as reported by [QNA](https://qna.org.qa/en/News-Area/News/2026-10/12/jordans-inflation-rises-226-percent-since-start-of-2026))
   states annual inflation for Sep 2026 of 2.73 %, +0.16 % vs August and 2.26 % for Jan–Sep. Recomputed from the series:
   2.729 %, +0.164 %, 2.256 % ✔ (also asserted in the test-suite).
4. **IMF cross-check** (`IMF.STA:CPI`, Jordan, monthly index): 235 of 247 overlapping months agree within 0.01 index points.
   The remaining 12 months are all in **2018** (largest: March 2018, DoS 99.545 vs IMF 98.822). Both series average exactly
   100 in 2018, so only the within-year profile differs. The cause was **not determined**; DoS workbooks are used. This is
   reported as a *warning* in the app, not hidden. The IMF data is used for comparison only and is not redistributed.
5. **Basket break:** pre-2018 values are DoS's legacy 2010 = 100 series rescaled by one constant factor (verified on 2017:
   ratio constant to 4 d.p.). From January 2018 DoS uses a new basket, so Dec 2017 → Jan 2018 (+1.02 %; +0.69 % in the legacy
   series) contains a one-time link. This is documented in *Data & Quality* and the Methods page.

## Licence / reuse – please read
* DoS's *Terms & Conditions* (<https://dosweb.dos.gov.jo/terms-conditions/>) say the information is subject to
  intellectual-property (copyright) law "unless noted otherwise" and **do not** grant an open licence.
* Therefore this repository includes **only** the extracted headline index values (`data/processed/jordan_cpi_monthly.csv`,
  249 numbers) with attribution, for non-commercial research and demonstration. The raw DoS workbooks are **not** committed
  (`data/raw/` is git-ignored); their checksums are recorded so the extraction is auditable.
* Rights in the data remain with the Department of Statistics. If the Department asks for removal, delete the CSV and run
  `python -m mizan ingest` locally instead. The MIT licence of this repository covers the code, not the data.
* IMF data: IMF terms restrict systematic redistribution, so IMF values are never stored – only comparison statistics.

## Reproduce
```bash
python -m mizan ingest        # downloads from DoS, validates, rewrites data/processed/*
python -m mizan validate      # validates the bundled series against provenance.json
python -m mizan backtest --force   # rebuilds data/results/results.json
```
