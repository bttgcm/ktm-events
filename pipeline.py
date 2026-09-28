"""Orchestrator: run every enabled source adapter, merge, dedupe, sort,
and write the combined result to docs/events.json for the static site.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scrapers.base import Event
from scrapers.registry import ADAPTERS

ROOT = Path(__file__).parent
SOURCES_CONFIG = ROOT / "sources.yaml"
OUTPUT_PATH = ROOT / "docs" / "events.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_enabled_sources() -> list[str]:
    config = yaml.safe_load(SOURCES_CONFIG.read_text(encoding="utf-8"))
    return [s["name"] for s in config.get("sources", []) if s.get("enabled", False)]


def collect_events(source_names: list[str]) -> list[Event]:
    events: list[Event] = []
    for name in source_names:
        adapter_cls = ADAPTERS.get(name)
        if adapter_cls is None:
            logger.warning("No adapter registered for source %r, skipping", name)
            continue
        adapter = adapter_cls()
        try:
            fetched = adapter.fetch_events()
        except Exception as exc:  # noqa: BLE001 - one bad source must not stop the run
            logger.warning("Source %r failed: %s", name, exc)
            continue
        logger.info("Source %r returned %d event(s)", name, len(fetched))
        events.extend(fetched)
    return events


def dedupe(events: list[Event]) -> list[Event]:
    by_id: dict[str, Event] = {}
    for event in events:
        by_id[event.id] = event
    return list(by_id.values())


def sort_by_start(events: list[Event]) -> list[Event]:
    return sorted(events, key=lambda e: e.start)


def write_output(events: list[Event]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "events": [e.to_dict() for e in events],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Wrote %d event(s) to %s", len(events), OUTPUT_PATH)


def main() -> None:
    source_names = load_enabled_sources()
    events = collect_events(source_names)
    events = dedupe(events)
    events = sort_by_start(events)
    write_output(events)


if __name__ == "__main__":
    main()
