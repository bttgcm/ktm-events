"""Maps source names (from sources.yaml) to adapter classes.

To add a new source: write an adapter module implementing
EventSourceAdapter, add it here, then enable it in sources.yaml.
"""

from .base import EventSourceAdapter
from .martin_chautari import MartinChautariAdapter

ADAPTERS: dict[str, type[EventSourceAdapter]] = {
    "martin_chautari": MartinChautariAdapter,
}
