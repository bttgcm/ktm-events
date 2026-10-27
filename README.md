# Kathmandu Cultural Events

Aggregates cultural events from existing event-listing websites around Kathmandu into one static page, updated automatically on a daily schedule.

## How it works

- `scrapers/` contains one adapter per source website, each implementing `EventSourceAdapter.fetch_events()` from `scrapers/base.py`.
- `pipeline.py` runs every enabled adapter (per `sources.yaml`), merges the results, deduplicates by event id, drops anything that ended more than 30 days ago (some sources mix years of history into the same page as current events), sorts by start date, and writes `docs/events.json` and `docs/events.ics`.
- `docs/` is a static site (`index.html` / `style.css` / `app.js`) that fetches `events.json` and renders it, with Upcoming / Past / All filters and a per-event "Add to Calendar" download.
- `ics.py` builds `docs/events.ics`, a single iCalendar feed containing every event, for subscribing from a calendar app (see below).
- `.github/workflows/update-events.yml` runs the pipeline daily and commits the refreshed `docs/events.json` and `docs/events.ics`; GitHub Pages serves `docs/` directly.

## Subscribing to the calendar feed

`docs/events.ics` is regenerated on every pipeline run, so subscribing to it (rather than downloading it once) keeps a phone/desktop calendar in sync automatically as new events get scraped in:

- **Apple Calendar** (Mac/iPhone): File → New Calendar Subscription (Mac) or tap the "📅 Subscribe to this calendar" link on the site (iOS/Safari) → paste `https://<username>.github.io/<repo>/events.ics`.
- **Google Calendar**: Other calendars → "+" → "From URL" → paste the same `https://.../events.ics` URL.
- **Outlook**: Add calendar → "Subscribe from web" → paste the same URL.

How often the calendar app re-fetches the feed is controlled by that app (typically every few hours to once a day), not by this project.

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

Tests run against saved HTML/XML fixtures in `tests/fixtures/` and never hit the network.

## Sources

| Source | Adapter | Notes |
|---|---|---|
| Martin Chautari | `scrapers/martin_chautari.py` | Clean, machine-readable `<time>` dates. |
| Taragaon Next | `scrapers/taragaon_next.py` | `/whats-on/` mixes years of history with current events - relies on the 30-day cutoff above. |
| Mandala Theatre | `scrapers/mandala_theatre.py` | Listing page only gives event URLs; all real fields come from each detail page. |
| Kata Jaam | `scrapers/katajaam.py` | A general Kathmandu event-discovery app, not a single cultural org - pulls in nightlife/food events too, not just culture. |
| Nepal Art Council | `scrapers/nepal_art_council.py` | Exhibition dates are free-form prose in the post excerpt, not a labeled field - the most likely of the bunch to break if they reword it. |
| Spotted by Sattya | `scrapers/spotted_by_sattya.py` | A Substack weekly digest, not a per-event listing - parses the RSS feed's body text (day headings + `<strong>` event blocks) rather than a page of event cards. |

**soscbaha.org** was evaluated and intentionally left out: it sits behind a Cloudflare bot-challenge page, so a plain HTTP request never reaches real content (see the comment in `sources.yaml`).

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
