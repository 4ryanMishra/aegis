"""
Market Observation Adapter (P_MARKET).
Non-negotiable rule #1 & #2: Never present Binance/API data as on-chain data.
Explicitly labels data as off-chain market observation.
"""

from typing import Optional
from ..models.schema import MarketObservation, DataStatus


class MockMarketAdapter:
    def __init__(self, source_name: str = "simulated_binance_adapter"):
        self.source_name = source_name

    def observe_market(
        self,
        price: float,
        timestamp: int,
        symbol: str = "XAU/USD",
        status: DataStatus = DataStatus.SIMULATED
    ) -> MarketObservation:
        """
        Emits independent market observation at window end T1.
        Explicitly flagged as off-chain CEX/DEX observation.
        """
        return MarketObservation(
            value=float(price),
            timestamp=timestamp,
            source=self.source_name,
            status=status,
            symbol=symbol,
            is_offchain=True
        )
