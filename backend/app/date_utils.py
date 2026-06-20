"""Date range utilities and window presets for time-series queries."""

from __future__ import annotations

from datetime import date, timedelta
from enum import StrEnum

from pydantic import BaseModel, ValidationInfo, field_validator


class DateWindow(StrEnum):
    """Predefined date window presets."""

    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"
    ONE_YEAR = "365d"
    MTD = "mtd"  # Month-to-date
    QTD = "qtd"  # Quarter-to-date
    YTD = "ytd"  # Year-to-date
    CUSTOM = "custom"


class DateRangeParams(BaseModel):
    """Date range query parameters for time-series endpoints.

    Supports both preset windows and custom date ranges.
    All dates are INCLUSIVE (start and end both included in results).
    All dates interpreted in UTC timezone.
    """

    window: DateWindow | None = DateWindow.NINETY_DAYS
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("end_date")
    @classmethod
    def end_date_must_be_after_start(
        cls, v: date | None, info: ValidationInfo
    ) -> date | None:
        """Validate that end_date is after or equal to start_date."""
        if v is not None and info.data.get("start_date") is not None:
            start = info.data["start_date"]
            if v < start:
                msg = "end_date must be >= start_date"
                raise ValueError(msg)
        return v


def calculate_date_range(params: DateRangeParams) -> tuple[date, date]:
    """Calculate concrete start_date and end_date from window parameters.

    All date ranges are INCLUSIVE (both start and end dates included).
    Uses UTC for all date calculations.

    Args:
        params: DateRangeParams with window or custom dates

    Returns:
        Tuple of (start_date, end_date) both inclusive

    Raises:
        ValueError: If custom window specified without dates
    """
    today = date.today()

    # Custom window: use provided dates
    if params.window == DateWindow.CUSTOM:
        if params.start_date is None or params.end_date is None:
            msg = "CUSTOM window requires start_date and end_date"
            raise ValueError(msg)
        return params.start_date, params.end_date

    # Fixed-day windows
    if params.window == DateWindow.SEVEN_DAYS:
        return today - timedelta(days=6), today
    if params.window == DateWindow.THIRTY_DAYS:
        return today - timedelta(days=29), today
    if params.window == DateWindow.NINETY_DAYS:
        return today - timedelta(days=89), today
    if params.window == DateWindow.ONE_YEAR:
        return today - timedelta(days=364), today

    # Month-to-date: 1st of current month to today
    if params.window == DateWindow.MTD:
        start = today.replace(day=1)
        return start, today

    # Quarter-to-date: 1st day of current quarter to today
    if params.window == DateWindow.QTD:
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_month, day=1)
        return start, today

    # Year-to-date: Jan 1 of current year to today
    if params.window == DateWindow.YTD:
        start = today.replace(month=1, day=1)
        return start, today

    # Default: 90 days
    return today - timedelta(days=89), today


def get_window_label(window: DateWindow) -> str:
    """Get human-readable label for a date window preset.

    Args:
        window: DateWindow enum value

    Returns:
        Human-readable string (e.g., "Last 7 Days", "Month to Date")
    """
    labels = {
        DateWindow.SEVEN_DAYS: "Last 7 Days",
        DateWindow.THIRTY_DAYS: "Last 30 Days",
        DateWindow.NINETY_DAYS: "Last 90 Days",
        DateWindow.ONE_YEAR: "Last 365 Days",
        DateWindow.MTD: "Month to Date",
        DateWindow.QTD: "Quarter to Date",
        DateWindow.YTD: "Year to Date",
        DateWindow.CUSTOM: "Custom Range",
    }
    return labels.get(window, "Unknown")
