"""Schemas for tenant locale/currency settings (NFR-022 / T-052)."""

import re

from pydantic import BaseModel, ConfigDict, field_validator

# Supported ISO 4217 currency codes (Phase 1 set — extend as needed).
_SUPPORTED_CURRENCIES: frozenset[str] = frozenset(
    {
        "USD",
        "EUR",
        "GBP",
        "INR",
        "AUD",
        "CAD",
        "SGD",
        "AED",
        "JPY",
        "NZD",
        "ZAR",
        "MXN",
        "BRL",
        "CHF",
        "SEK",
        "NOK",
        "DKK",
        "HKD",
        "PLN",
        "CZK",
    }
)

# Approximate units-per-USD for each supported currency (mid-2026 reference
# rates).  Used only for THRESHOLD DEFAULTS and FLOORS — not for live financial
# calculations.  Update periodically as rates drift significantly.
OPS_CURRENCY_SCALE_VS_USD: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 84.0,
    "AUD": 1.56,
    "CAD": 1.36,
    "SGD": 1.35,
    "AED": 3.67,
    "JPY": 156.0,
    "NZD": 1.65,
    "ZAR": 19.0,
    "MXN": 17.5,
    "BRL": 5.0,
    "CHF": 0.90,
    "SEK": 10.5,
    "NOK": 10.8,
    "DKK": 6.9,
    "HKD": 7.79,
    "PLN": 4.0,
    "CZK": 23.0,
}

# USD-denominated baselines for OPS-001 thresholds.
# Scale by OPS_CURRENCY_SCALE_VS_USD[currency] to get the local-currency value.
OPS_USD_DEFAULT = 500.0  # seed default: ~£395 / ₹42,000 / ¥78,000
OPS_USD_FLOOR = 100.0  # suggestion floor: ~£79 / ₹8,400 / ¥15,600

# IETF BCP-47 locale tag pattern: language[-region] e.g. "en-US", "fr-FR", "hi-IN".
_LOCALE_RE = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?$")


class TenantLocaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    base_currency: str
    locale: str


class TenantLocaleUpdateRequest(BaseModel):
    base_currency: str | None = None
    locale: str | None = None

    @field_validator("base_currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        if v is None:
            return v
        upper = v.strip().upper()
        if upper not in _SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency '{v}'. "
                f"Supported: {sorted(_SUPPORTED_CURRENCIES)}"
            )
        return upper

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not _LOCALE_RE.match(stripped):
            raise ValueError(
                f"Invalid locale '{v}'. "
                "Expected IETF BCP-47 format, e.g. 'en-US', 'fr-FR'."
            )
        return stripped
