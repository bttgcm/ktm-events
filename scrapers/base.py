"""Shared data model and adapter interface for event sources."""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Event:
    title: str
    start: str  # ISO 8601 string, source timezone preserved
    source_name: str
    source_url: str
    description: Optional[str] = None
    end: Optional[str] = None
    location: Optional[str] = None
    categories: list[str] = field(default_factory=list)
    image: Optional[str] = None
    id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.id:
            digest = hashlib.sha1(f"{self.source_name}|{self.source_url}".encode("utf-8"))
            self.id = digest.hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


class EventSourceAdapter(ABC):
    """One implementation per source website."""

    name: str

    @abstractmethod
    def fetch_events(self) -> list[Event]:
        """Fetch and parse events from this source.

        Individual per-event failures (e.g. a single detail page not
        loading) should be handled internally rather than dropping the
        whole run. Total failure (e.g. the site being unreachable) may
        raise - the pipeline catches adapter-level exceptions so one bad
        source doesn't take down the others.
        """
        raise NotImplementedError
