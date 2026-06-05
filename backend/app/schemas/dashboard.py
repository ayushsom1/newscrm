from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

Severity = Literal["AUTO", "APPROVE", "HUMAN"]


class KpiBlock(BaseModel):
    label: str
    value: int
    hint: str | None = None


class Kpis(BaseModel):
    blocks: list[KpiBlock]
    revenue_running_total_inr: Decimal


class ExceptionQueueItem(BaseModel):
    """Derived from existing tables at query time. ref_url tells the FE where
    to click through."""

    type: str
    ref_id: int
    severity: Severity
    summary: str
    detail: str | None = None
    ref_url: str


class ExceptionQueue(BaseModel):
    items: list[ExceptionQueueItem]
    counts: dict[str, int]  # severity -> count
