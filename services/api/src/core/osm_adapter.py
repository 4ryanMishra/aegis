"""
Mock OSM Adapter (P_OSM Baseline).
Non-negotiable rule #1 & #6: Clearly labeled as SIMULATED baseline feed.
Simulates Multipli's 1-hour delayed oracle price entry.
"""

from ..models.schema import OSMFeed, DataStatus


class MockOSMAdapter:
    def __init__(self, source_name: str = "multipli_osm_mock"):
        self.source_name = source_name

    def get_queued_osm(self, initial_price: float, timestamp: int) -> OSMFeed:
        """Emits the delayed OSM price feed received at window start T0."""
        return OSMFeed(
            value=float(initial_price),
            timestamp=timestamp,
            source=self.source_name,
            status=DataStatus.SIMULATED,
            description="Baseline delayed OSM price queued at window start T0"
        )
