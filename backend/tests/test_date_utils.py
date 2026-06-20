"""Tests for date range utilities."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from backend.app.date_utils import (
    DateRangeParams,
    DateWindow,
    calculate_date_range,
    get_window_label,
)


def test_date_window_enum_values() -> None:
    """Test that all window presets are defined."""
    assert DateWindow.SEVEN_DAYS.value == "7d"
    assert DateWindow.THIRTY_DAYS.value == "30d"
    assert DateWindow.NINETY_DAYS.value == "90d"
    assert DateWindow.ONE_YEAR.value == "365d"
    assert DateWindow.MTD.value == "mtd"
    assert DateWindow.QTD.value == "qtd"
    assert DateWindow.YTD.value == "ytd"
    assert DateWindow.CUSTOM.value == "custom"


def test_date_range_params_default() -> None:
    """Test that default window is 90 days."""
    params = DateRangeParams()
    assert params.window == DateWindow.NINETY_DAYS
    assert params.start_date is None
    assert params.end_date is None


def test_date_range_params_custom_requires_dates() -> None:
    """Test that custom window requires start_date and end_date."""
    # Pydantic model allows creation with CUSTOM window without dates
    # Validation happens in calculate_date_range function
    params1 = DateRangeParams(window=DateWindow.CUSTOM)
    with pytest.raises(
        ValueError, match="CUSTOM window requires start_date and end_date"
    ):
        calculate_date_range(params1)

    params2 = DateRangeParams(
        window=DateWindow.CUSTOM, start_date=date(2026, 1, 1)
    )
    with pytest.raises(
        ValueError, match="CUSTOM window requires start_date and end_date"
    ):
        calculate_date_range(params2)

    params3 = DateRangeParams(
        window=DateWindow.CUSTOM, end_date=date(2026, 12, 31)
    )
    with pytest.raises(
        ValueError, match="CUSTOM window requires start_date and end_date"
    ):
        calculate_date_range(params3)


def test_date_range_params_end_after_start() -> None:
    """Test that end_date must be >= start_date."""
    # Valid: end after start
    params = DateRangeParams(
        window=DateWindow.CUSTOM,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    assert params.start_date == date(2026, 1, 1)
    assert params.end_date == date(2026, 12, 31)

    # Valid: end equals start (single day)
    params_same = DateRangeParams(
        window=DateWindow.CUSTOM,
        start_date=date(2026, 6, 15),
        end_date=date(2026, 6, 15),
    )
    assert params_same.start_date == params_same.end_date

    # Invalid: end before start
    with pytest.raises(ValueError, match="end_date must be >= start_date"):
        DateRangeParams(
            window=DateWindow.CUSTOM,
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1),
        )


def test_calculate_date_range_7d() -> None:
    """Test 7-day window calculation."""
    today = date.today()
    params = DateRangeParams(window=DateWindow.SEVEN_DAYS)
    start, end = calculate_date_range(params)

    assert end == today
    assert start == today - timedelta(days=6)
    assert (end - start).days == 6  # 7 days inclusive


def test_calculate_date_range_30d() -> None:
    """Test 30-day window calculation."""
    today = date.today()
    params = DateRangeParams(window=DateWindow.THIRTY_DAYS)
    start, end = calculate_date_range(params)

    assert end == today
    assert start == today - timedelta(days=29)
    assert (end - start).days == 29  # 30 days inclusive


def test_calculate_date_range_90d() -> None:
    """Test 90-day window calculation."""
    today = date.today()
    params = DateRangeParams(window=DateWindow.NINETY_DAYS)
    start, end = calculate_date_range(params)

    assert end == today
    assert start == today - timedelta(days=89)
    assert (end - start).days == 89  # 90 days inclusive


def test_calculate_date_range_365d() -> None:
    """Test 365-day window calculation."""
    today = date.today()
    params = DateRangeParams(window=DateWindow.ONE_YEAR)
    start, end = calculate_date_range(params)

    assert end == today
    assert start == today - timedelta(days=364)
    assert (end - start).days == 364  # 365 days inclusive


def test_calculate_date_range_mtd() -> None:
    """Test month-to-date window calculation."""
    today = date.today()
    params = DateRangeParams(window=DateWindow.MTD)
    start, end = calculate_date_range(params)

    assert end == today
    assert start.day == 1
    assert start.month == today.month
    assert start.year == today.year


def test_calculate_date_range_qtd() -> None:
    """Test quarter-to-date window calculation."""
    today = date.today()
    params = DateRangeParams(window=DateWindow.QTD)
    start, end = calculate_date_range(params)

    assert end == today
    assert start.day == 1

    # Verify quarter start month
    expected_quarter_month = ((today.month - 1) // 3) * 3 + 1
    assert start.month == expected_quarter_month
    assert start.year == today.year


def test_calculate_date_range_ytd() -> None:
    """Test year-to-date window calculation."""
    today = date.today()
    params = DateRangeParams(window=DateWindow.YTD)
    start, end = calculate_date_range(params)

    assert end == today
    assert start == date(today.year, 1, 1)


def test_calculate_date_range_custom() -> None:
    """Test custom date range."""
    params = DateRangeParams(
        window=DateWindow.CUSTOM,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
    )
    start, end = calculate_date_range(params)

    assert start == date(2026, 3, 1)
    assert end == date(2026, 3, 31)


def test_calculate_date_range_custom_without_dates() -> None:
    """Test that custom window without dates raises error."""
    params = DateRangeParams(window=DateWindow.SEVEN_DAYS)
    # Force window to CUSTOM without validation (bypass pydantic)
    params.window = DateWindow.CUSTOM

    with pytest.raises(
        ValueError, match="CUSTOM window requires start_date and end_date"
    ):
        calculate_date_range(params)


def test_calculate_date_range_default() -> None:
    """Test that default params return 90-day window."""
    today = date.today()
    params = DateRangeParams()  # No window specified, uses default
    start, end = calculate_date_range(params)

    assert end == today
    assert start == today - timedelta(days=89)


def test_get_window_label() -> None:
    """Test window label generation."""
    assert get_window_label(DateWindow.SEVEN_DAYS) == "Last 7 Days"
    assert get_window_label(DateWindow.THIRTY_DAYS) == "Last 30 Days"
    assert get_window_label(DateWindow.NINETY_DAYS) == "Last 90 Days"
    assert get_window_label(DateWindow.ONE_YEAR) == "Last 365 Days"
    assert get_window_label(DateWindow.MTD) == "Month to Date"
    assert get_window_label(DateWindow.QTD) == "Quarter to Date"
    assert get_window_label(DateWindow.YTD) == "Year to Date"
    assert get_window_label(DateWindow.CUSTOM) == "Custom Range"


def test_date_range_inclusivity() -> None:
    """Test that date ranges are inclusive on both ends."""
    # Test with a known range
    params = DateRangeParams(
        window=DateWindow.CUSTOM,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
    )
    start, end = calculate_date_range(params)

    # Should include both June 1 and June 7
    assert start == date(2026, 6, 1)
    assert end == date(2026, 6, 7)
    assert (end - start).days == 6  # 7 days inclusive: 1,2,3,4,5,6,7
