from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class VendorHistoryMetrics(BaseModel):
    vendor_id: Any
    previous_batches: int = 0
    approval_rate: float = 0.0  # e.g., 0.92 for 92%
    rejection_rate: float = 0.0  # e.g., 0.08 for 8%
    average_purity: float = 0.0  # e.g., 99.1%
    purity_variance: float = 0.0  # statistical variance of purity
    documentation_completeness: float = 0.0  # e.g., 0.95 (95% complete)
    delivery_reliability: float = 0.0  # e.g., 0.96 (on-time rate)
    incident_count: int = 0  # logged quality/delivery deviations
    average_lead_time: float = 0.0  # days
    price_variance: float = 0.0  # variance vs baseline price
    capacity: float = 0.0  # units per month
    comparison_notes: Dict[str, Any] = Field(default_factory=dict)
