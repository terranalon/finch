"""Tests for date range service."""

from datetime import date

from app.services.shared.date_range_service import merge_ranges, shrink_date_ranges


class TestShrinkDateRanges:
    def test_full_overlap_returns_empty(self):
        """When transfer range covers entire source range."""
        current = [{"start_date": "2024-01-01", "end_date": "2024-06-30"}]
        result = shrink_date_ranges(current, date(2024, 1, 1), date(2024, 6, 30))
        assert result == []

    def test_partial_overlap_shrinks_range(self):
        """Transfer range takes middle portion."""
        current = [{"start_date": "2024-01-01", "end_date": "2024-12-31"}]
        result = shrink_date_ranges(current, date(2024, 4, 1), date(2024, 6, 30))
        assert len(result) == 2
        assert result[0] == {"start_date": "2024-01-01", "end_date": "2024-03-31"}
        assert result[1] == {"start_date": "2024-07-01", "end_date": "2024-12-31"}

    def test_transfer_at_start_shrinks_beginning(self):
        current = [{"start_date": "2024-01-01", "end_date": "2024-12-31"}]
        result = shrink_date_ranges(current, date(2024, 1, 1), date(2024, 3, 31))
        assert result == [{"start_date": "2024-04-01", "end_date": "2024-12-31"}]

    def test_transfer_at_end_shrinks_end(self):
        current = [{"start_date": "2024-01-01", "end_date": "2024-12-31"}]
        result = shrink_date_ranges(current, date(2024, 10, 1), date(2024, 12, 31))
        assert result == [{"start_date": "2024-01-01", "end_date": "2024-09-30"}]

    def test_no_overlap_keeps_range(self):
        """Transfer range doesn't overlap - keep original."""
        current = [{"start_date": "2024-01-01", "end_date": "2024-03-31"}]
        result = shrink_date_ranges(current, date(2024, 7, 1), date(2024, 9, 30))
        assert result == [{"start_date": "2024-01-01", "end_date": "2024-03-31"}]

    def test_multiple_ranges_partial_overlap(self):
        """Transfer overlaps with one of multiple ranges."""
        current = [
            {"start_date": "2024-01-01", "end_date": "2024-03-31"},
            {"start_date": "2024-07-01", "end_date": "2024-12-31"},
        ]
        result = shrink_date_ranges(current, date(2024, 7, 1), date(2024, 9, 30))
        assert len(result) == 2
        assert result[0] == {"start_date": "2024-01-01", "end_date": "2024-03-31"}
        assert result[1] == {"start_date": "2024-10-01", "end_date": "2024-12-31"}


class TestMergeRanges:
    def test_adjacent_ranges_merge(self):
        ranges = [
            {"start_date": "2024-01-01", "end_date": "2024-03-31"},
            {"start_date": "2024-04-01", "end_date": "2024-06-30"},
        ]
        result = merge_ranges(ranges)
        assert result == [{"start_date": "2024-01-01", "end_date": "2024-06-30"}]

    def test_non_adjacent_ranges_stay_separate(self):
        ranges = [
            {"start_date": "2024-01-01", "end_date": "2024-03-31"},
            {"start_date": "2024-07-01", "end_date": "2024-12-31"},
        ]
        result = merge_ranges(ranges)
        assert len(result) == 2

    def test_empty_list_returns_empty(self):
        result = merge_ranges([])
        assert result == []

    def test_single_range_unchanged(self):
        ranges = [{"start_date": "2024-01-01", "end_date": "2024-06-30"}]
        result = merge_ranges(ranges)
        assert result == [{"start_date": "2024-01-01", "end_date": "2024-06-30"}]

    def test_overlapping_ranges_merge(self):
        """Overlapping ranges should merge (edge case)."""
        ranges = [
            {"start_date": "2024-01-01", "end_date": "2024-04-15"},
            {"start_date": "2024-04-01", "end_date": "2024-06-30"},
        ]
        result = merge_ranges(ranges)
        assert result == [{"start_date": "2024-01-01", "end_date": "2024-06-30"}]

    def test_unsorted_ranges_get_sorted_and_merged(self):
        """Ranges should be sorted before merging."""
        ranges = [
            {"start_date": "2024-07-01", "end_date": "2024-12-31"},
            {"start_date": "2024-01-01", "end_date": "2024-03-31"},
        ]
        result = merge_ranges(ranges)
        assert len(result) == 2
        assert result[0]["start_date"] == "2024-01-01"
        assert result[1]["start_date"] == "2024-07-01"
