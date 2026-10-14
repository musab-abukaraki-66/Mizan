# Publishing and automatic updates

MIZAN's web app only reads precomputed results, so the public site is **static** (`site/`): no server to run or pay for.

* **Live URL** (after the one-time setup below): <https://musab-abukaraki-66.github.io/Mizan/>
* **Build locally:** `cd frontend && npm run build:static && cd .. && python -m mizan export-static --out site`
* **Deploy:** `.github/workflows/pages.yml` publishes `site/` to GitHub Pages (on every push to `main` that changes `site/`, or manually).
* **Keeps itself up to date:** `.github/workflows/update.yml` runs every Monday (and on demand). It re-downloads the Department of
  Statistics workbooks and, **only if the CPI series changed**, validates the data, re-runs the backtests, runs the tests,
  rebuilds `site/`, commits "Data update: CPI through YYYY-MM" and redeploys. If the Department changes its file layout the
  job fails loudly (red run in the Actions tab) instead of publishing bad data.

## One-time setup (≈ 2 minutes)
1. Repository **Settings → General → Danger Zone → Change visibility → Public** (GitHub Pages is free for public repos).
2. Merge the working branch into `main` (the scheduled job and Pages deploys run from the default branch).
3. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. **Actions → Deploy site (GitHub Pages) → Run workflow.** The URL appears in the run summary.

## Notes
* Weekly checks cost nothing when no new month exists (no commit, no deploy).
* The Department typically publishes the new month around the 10th-14th; the next Monday run picks it up.
* To refresh immediately: Actions → *Update data and site* → Run workflow.
* The site shows the data licence/attribution notice and the "independent project, not official" disclaimer on every page.
