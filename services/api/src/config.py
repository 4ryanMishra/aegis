"""
AEGIS Configuration & Thresholds.
Rule #5: Keep all thresholds configurable and documented.
All thresholds here are labeled as PROTOTYPE DEMO THRESHOLDS.
"""

from pydantic import BaseModel, Field


class AegisConfig(BaseModel):
    # Oracle Window Configuration
    window_duration_seconds: int = Field(
        default=3600,
        description="Duration of the delayed oracle verification window in seconds (1 hour)."
    )
    
    # Deviation Thresholds (Prototyped for MVP)
    # If relative deviation exceeds 3.5%, flag abnormal deviation
    abnormal_deviation_threshold: float = Field(
        default=0.035,
        description="Relative deviation threshold (|P_1 - P_2| / P_2) above which anomaly is suspected."
    )
    
    # High deviation threshold (e.g. 5%)
    high_deviation_threshold: float = Field(
        default=0.050,
        description="High relative deviation threshold indicating major oracle divergence."
    )
    
    # Validator Quorum & Dispersion
    min_validator_quorum: int = Field(
        default=3,
        description="Minimum number of active validator observations required for valid P_DEC."
    )
    max_acceptable_dispersion: float = Field(
        default=0.05,
        description="Maximum normalized IQR dispersion among validators before flagging high uncertainty."
    )
    
    # Collateral Risk Parameters
    default_ltv: float = Field(
        default=0.60,
        description="Default Loan-to-Value (LTV) ratio for collateral valuation impact calculations."
    )
    
    # Status & Environment Tag
    environment: str = Field(
        default="SIMULATION",
        description="Execution mode: SIMULATION / TESTNET / LOCAL."
    )


# Global default settings instance
default_config = AegisConfig()
