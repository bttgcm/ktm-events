"""Maps source names (from sources.yaml) to adapter classes.

To add a new source: write an adapter module implementing
EventSourceAdapter, add it here, then enable it in sources.yaml.
"""

from .base import EventSourceAdapter
from .katajaam import KataJaamAdapter
from .mandala_theatre import MandalaTheatreAdapter
from .martin_chautari import MartinChautariAdapter
from .nepal_art_council import NepalArtCouncilAdapter
from .spotted_by_sattya import SpottedBySattyaAdapter
from .taragaon_next import TaragaonNextAdapter

ADAPTERS: dict[str, type[EventSourceAdapter]] = {
    "martin_chautari": MartinChautariAdapter,
    "taragaon_next": TaragaonNextAdapter,
    "mandala_theatre": MandalaTheatreAdapter,
    "katajaam": KataJaamAdapter,
    "nepal_art_council": NepalArtCouncilAdapter,
    "spotted_by_sattya": SpottedBySattyaAdapter,
}
