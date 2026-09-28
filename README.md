# Kathmandu Cultural Events

Aggregates cultural events from existing event-listing websites around Kathmandu into one static page, updated automatically on a daily schedule.

## How it works

- `scrapers/` contains one adapter per source website, each implementing `EventSourceAdapter.fetch_events()` from `scrapers/base.py`.
- `pipeline.py` runs every enabled adapter (per `sources.yaml`), merges the results, deduplicates by event id, sorts by start date, and writes `docs/events.json`.
- `docs/` is a static site (`index.html` / `style.css` / `app.js`) that fetches `events.json` and renders it, with Upcoming / Past / All filters.
- `.github/workflows/update-events.yml` runs the pipeline daily and commits the refreshed `docs/events.json`; GitHub Pages serves `docs/` directly.

## Running locally

```
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
python pipeline.py          # writes docs/events.json
python -m http.server --directory docs 8000   # then open http://localhost:8000
```

## Running tests

```
pytest
```

Tests run against a saved HTML fixture (`tests/fixtures/martin_chautari_events.html`) and never hit the network.

## Adding a new source

1. Create `scrapers/<new_site>.py` implementing `EventSourceAdapter` (see `scrapers/martin_chautari.py` for reference).
2. Register it in `scrapers/registry.py`'s `ADAPTERS` dict.
3. Add an entry to `sources.yaml`:
   ```yaml
   - name: <new_site>
     enabled: true
   ```

A source that fails to fetch is logged and skipped — it won't break the other sources' updates.

## One-time GitHub setup

These steps aren't automated and need to be done once by hand:

1. `git init`, commit, create a GitHub repo, and push (`git remote add origin <url>`).
2. Repo Settings → Pages → Source: "Deploy from a branch" → branch `main`, folder `/docs`.
3. Repo Settings → Actions → General → Workflow permissions → "Read and write permissions" (the workflow needs this to push the updated `events.json`).
4. Trigger the workflow once manually (Actions tab → "Update events" → Run workflow) to confirm it works, rather than waiting for the next scheduled run.

The site will then be live at `https://<username>.github.io/<repo>/`.
