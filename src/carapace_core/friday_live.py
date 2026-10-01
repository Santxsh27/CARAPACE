"""Typed input and mandate models for Financial Friday's live sandbox flow."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FridayMandate(BaseModel):
    """A user-owned standing instruction; execution stays inside these limits."""

    model_config = ConfigDict(extra="forbid")
    instruction: str = Field(min_length=8, max_length=500)
    protected_balance_minor: int = Field(strict=True, ge=0, le=100_000_000)
    automatic_payment_limit_minor: int = Field(strict=True, ge=0, le=10_000_000)
    max_fee_minor: int = Field(default=0, strict=True, ge=0, le=1_000_000)
    automatic_sandbox_execution: bool = False


class IncomingFinancialSignal(BaseModel):
    """Content observed through a user-authorised channel."""

    model_config = ConfigDict(extra="forbid")
    source_type: Literal["MESSAGE", "VOICE_TRANSCRIPT", "QR_TEXT", "BILL_TEXT"]
    content_text: str = Field(min_length=5, max_length=5000)
    event_id: str | None = Field(default=None, min_length=4, max_length=120)


class InterpretedFinancialSignal(BaseModel):
    """Gemini's typed interpretation. It is evidence, never authority."""

    model_config = ConfigDict(extra="forbid")
    request_kind: Literal["BILL", "PAYMENT_REQUEST", "TRANSACTION_ALERT", "UNKNOWN"]
    bill_reference: str | None = Field(default=None, max_length=120)
    provider_name: str | None = Field(default=None, max_length=160)
    amount_minor: int | None = Field(default=None, strict=True, gt=0, le=100_000_000)
    currency: Literal["INR"] = "INR"
    claimed_payee_id: str | None = Field(default=None, max_length=160)
    recurring_requested: bool = False
    summary: str = Field(min_length=5, max_length=500)
    suspicious_instructions: list[str] = Field(default_factory=list, max_length=8)


class TestProviderBill(BaseModel):
    """Authoritative artificial bill published by the enrolled test provider."""

    model_config = ConfigDict(extra="forbid")
    bill_reference: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{3,79}$")
    provider_name: str = Field(min_length=2, max_length=160)
    provider_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    payee_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9@._-]{2,119}$")
    amount_minor: int = Field(strict=True, gt=0, le=10_000_000)
    due_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    currency: Literal["INR"] = "INR"
