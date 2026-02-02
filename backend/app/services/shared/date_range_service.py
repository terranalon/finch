"""Date range service for managing discontinuous date ranges."""

from datetime import date, timedelta


def shrink_date_ranges(
    current_ranges: list[dict],
    transfer_start: date,
    transfer_end: date,
) -> list[dict]:
    """Remove transferred date range from source's ranges.

    When a newer file takes ownership of transactions in a date range,
    the old source's ranges must be shrunk to exclude that period.

    Args:
        current_ranges: List of date range dicts with start_date/end_date strings
        transfer_start: Start of range being transferred to new source
        transfer_end: End of range being transferred to new source

    Returns:
        Updated ranges (may be multiple discontinuous ranges)
    """
    result = []

    for range_dict in current_ranges:
        start = date.fromisoformat(range_dict["start_date"])
        end = date.fromisoformat(range_dict["end_date"])

        # No overlap - keep as is
        if transfer_end < start or transfer_start > end:
            result.append(range_dict)
            continue

        # Full overlap - remove entirely
        if transfer_start <= start and transfer_end >= end:
            continue

        # Partial overlap - split into remaining portions
        if transfer_start > start:
            result.append(
                {
                    "start_date": start.isoformat(),
                    "end_date": (transfer_start - timedelta(days=1)).isoformat(),
                }
            )
        if transfer_end < end:
            result.append(
                {
                    "start_date": (transfer_end + timedelta(days=1)).isoformat(),
                    "end_date": end.isoformat(),
                }
            )

    return merge_ranges(result)


def merge_ranges(ranges: list[dict]) -> list[dict]:
    """Merge adjacent or overlapping date ranges.

    Two ranges are considered adjacent if they are exactly one day apart
    (e.g., end=2024-03-31 and start=2024-04-01).

    Args:
        ranges: List of date range dicts with start_date/end_date strings

    Returns:
        Merged list of ranges, sorted by start_date
    """
    if not ranges:
        return []

    # Sort by start date
    sorted_ranges = sorted(ranges, key=lambda r: r["start_date"])

    merged = [sorted_ranges[0].copy()]

    for current in sorted_ranges[1:]:
        last = merged[-1]
        last_end = date.fromisoformat(last["end_date"])
        current_start = date.fromisoformat(current["start_date"])

        # Check if adjacent (next day) or overlapping
        if current_start <= last_end + timedelta(days=1):
            # Extend the last range
            current_end = date.fromisoformat(current["end_date"])
            if current_end > last_end:
                last["end_date"] = current["end_date"]
        else:
            merged.append(current.copy())

    return merged
