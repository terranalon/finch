"""Overlap detection service for broker data imports.

Prevents duplicate imports by checking for date range overlaps between
existing sources and new uploads.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import BrokerDataSource
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


@dataclass
class CoverageGap:
    """Represents a gap in data coverage."""

    start_date: date
    end_date: date

    @property
    def days(self) -> int:
        """Number of days in this gap."""
        return (self.end_date - self.start_date).days + 1


@dataclass
class CoverageSummary:
    """Summary of data coverage for an account/broker."""

    start_date: date | None
    end_date: date | None
    total_days: int
    sources_count: int
    gaps: list[CoverageGap]


@dataclass
class OverlapAnalysis:
    """Analysis of overlap between new file and existing sources."""

    overlapping_sources: list  # List of BrokerDataSource
    overlap_type: str  # 'none', 'partial', 'full_contains', 'subset'
    affected_transaction_count: int
    sources_to_delete: list  # Sources fully contained (can be auto-deleted)
    requires_confirmation: bool
    message: str


class BrokerOverlapDetector:
    """Detects overlaps and gaps in broker data coverage.

    Used to enforce the strict overlap policy: uploads that overlap with
    existing sources are rejected with an error.
    """

    def check_overlap(
        self,
        db: Session,
        account_id: int,
        broker_type: str,
        start_date: date,
        end_date: date,
        exclude_source_id: int | None = None,
    ) -> BrokerDataSource | None:
        """Check if a date range overlaps with existing sources.

        Two date ranges overlap if they share at least one day.
        Range A (start_a, end_a) overlaps with Range B (start_b, end_b) if:
            start_a <= end_b AND end_a >= start_b

        Args:
            db: Database session
            account_id: Account to check
            broker_type: Broker type to check (overlaps only within same broker)
            start_date: Start of proposed import range
            end_date: End of proposed import range
            exclude_source_id: Optional source ID to exclude (for updates)

        Returns:
            The conflicting BrokerDataSource if overlap found, None otherwise
        """
        query = db.query(BrokerDataSource).filter(
            BrokerDataSource.account_id == account_id,
            BrokerDataSource.broker_type == broker_type,
            BrokerDataSource.status == "completed",  # Only check completed sources
            # Overlap condition: ranges overlap if start <= other_end AND end >= other_start
            BrokerDataSource.start_date <= end_date,
            BrokerDataSource.end_date >= start_date,
        )

        if exclude_source_id:
            query = query.filter(BrokerDataSource.id != exclude_source_id)

        conflicting_source = query.first()

        if conflicting_source:
            logger.warning(
                "Overlap detected for account %d, broker %s: "
                "proposed %s to %s conflicts with source %d (%s to %s)",
                account_id,
                broker_type,
                start_date,
                end_date,
                conflicting_source.id,
                conflicting_source.start_date,
                conflicting_source.end_date,
            )

        return conflicting_source

    def get_coverage_gaps(
        self,
        db: Session,
        account_id: int,
        broker_type: str,
        desired_start: date,
        desired_end: date,
    ) -> list[CoverageGap]:
        """Find gaps in coverage within a desired date range.

        Args:
            db: Database session
            account_id: Account to check
            broker_type: Broker type to check
            desired_start: Start of desired coverage
            desired_end: End of desired coverage

        Returns:
            List of CoverageGap objects representing uncovered periods
        """
        # Get all completed sources for this account/broker, sorted by start date
        sources = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == account_id,
                BrokerDataSource.broker_type == broker_type,
                BrokerDataSource.status == "completed",
            )
            .order_by(BrokerDataSource.start_date)
            .all()
        )

        if not sources:
            # No data at all - entire range is a gap
            return [CoverageGap(start_date=desired_start, end_date=desired_end)]

        gaps: list[CoverageGap] = []
        current_date = desired_start

        for source in sources:
            # If source starts after current date, there's a gap
            if source.start_date > current_date:
                # Adjust gap_end to be the day before the source starts
                gap_end_adjusted = source.start_date - timedelta(days=1)
                if gap_end_adjusted >= current_date:
                    gaps.append(CoverageGap(start_date=current_date, end_date=gap_end_adjusted))

            # Move current date to after this source's coverage
            if source.end_date >= current_date:
                current_date = source.end_date + timedelta(days=1)

            # If we've passed the desired end, stop
            if current_date > desired_end:
                break

        # Check for gap at the end
        if current_date <= desired_end:
            gaps.append(CoverageGap(start_date=current_date, end_date=desired_end))

        return gaps

    def get_coverage_summary(
        self,
        db: Session,
        account_id: int,
        broker_type: str,
    ) -> CoverageSummary:
        """Get a summary of data coverage for an account/broker.

        Args:
            db: Database session
            account_id: Account to check
            broker_type: Broker type to check

        Returns:
            CoverageSummary with coverage statistics
        """
        # Get all completed sources
        sources = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == account_id,
                BrokerDataSource.broker_type == broker_type,
                BrokerDataSource.status == "completed",
            )
            .order_by(BrokerDataSource.start_date)
            .all()
        )

        if not sources:
            return CoverageSummary(
                start_date=None,
                end_date=None,
                total_days=0,
                sources_count=0,
                gaps=[],
            )

        # Find overall range
        overall_start = min(s.start_date for s in sources)
        overall_end = max(s.end_date for s in sources)

        # Calculate total covered days (accounting for overlaps)
        # Use a set of covered dates for accuracy
        covered_dates: set[date] = set()
        for source in sources:
            current = source.start_date
            while current <= source.end_date:
                covered_dates.add(current)
                current += timedelta(days=1)

        # Find gaps within the overall range
        gaps = self.get_coverage_gaps(db, account_id, broker_type, overall_start, overall_end)

        return CoverageSummary(
            start_date=overall_start,
            end_date=overall_end,
            total_days=len(covered_dates),
            sources_count=len(sources),
            gaps=gaps,
        )

    def get_all_sources(
        self,
        db: Session,
        account_id: int,
        broker_type: str | None = None,
    ) -> list[BrokerDataSource]:
        """Get all data sources for an account, optionally filtered by broker.

        Args:
            db: Database session
            account_id: Account to get sources for
            broker_type: Optional broker type filter

        Returns:
            List of BrokerDataSource records
        """
        query = db.query(BrokerDataSource).filter(BrokerDataSource.account_id == account_id)

        if broker_type:
            query = query.filter(BrokerDataSource.broker_type == broker_type)

        return query.order_by(BrokerDataSource.start_date.desc()).all()

    def analyze_overlap(
        self,
        db: Session,
        account_id: int,
        broker_type: str,
        new_start: date,
        new_end: date,
    ) -> OverlapAnalysis:
        """Analyze overlaps and return detailed impact report.

        Determines the type of overlap and what actions are needed:
        - none: No overlap, can import freely
        - partial: Some dates overlap, needs user confirmation
        - full_contains: New file fully contains old sources (can auto-delete)
        - subset: New file is already covered by existing imports

        Args:
            db: Database session
            account_id: Account to check
            broker_type: Broker type to check
            new_start: Start date of new import
            new_end: End date of new import

        Returns:
            OverlapAnalysis with detailed information about the overlap
        """
        overlapping = self._get_overlapping_sources(db, account_id, broker_type, new_start, new_end)

        if not overlapping:
            return OverlapAnalysis(
                overlapping_sources=[],
                overlap_type="none",
                affected_transaction_count=0,
                sources_to_delete=[],
                requires_confirmation=False,
                message="No overlap detected",
            )

        # Count affected transactions
        source_ids = [s.id for s in overlapping]
        txn_count = (
            db.query(func.count(Transaction.id))
            .filter(Transaction.broker_source_id.in_(source_ids))
            .scalar()
            or 0
        )

        # Categorize each overlapping source
        sources_to_delete = []
        has_subset = False

        for source in overlapping:
            new_file_contains_source = new_start <= source.start_date and new_end >= source.end_date
            source_contains_new_file = source.start_date <= new_start and source.end_date >= new_end

            if new_file_contains_source:
                sources_to_delete.append(source)
            elif source_contains_new_file:
                has_subset = True

        # Determine overlap type based on categorization
        overlap_type, message = self._determine_overlap_type(
            overlapping, sources_to_delete, has_subset
        )

        return OverlapAnalysis(
            overlapping_sources=overlapping,
            overlap_type=overlap_type,
            affected_transaction_count=txn_count,
            sources_to_delete=sources_to_delete,
            requires_confirmation=True,
            message=message,
        )

    def _determine_overlap_type(
        self,
        overlapping: list[BrokerDataSource],
        sources_to_delete: list[BrokerDataSource],
        has_subset: bool,
    ) -> tuple[str, str]:
        """Determine overlap type and message based on source categorization."""
        if has_subset:
            return "subset", "This file's date range is already covered by existing imports."

        if len(sources_to_delete) == len(overlapping):
            return (
                "full_contains",
                f"This will replace {len(sources_to_delete)} existing import(s).",
            )

        return "partial", f"Partial overlap with {len(overlapping)} existing import(s)."

    def _get_overlapping_sources(
        self,
        db: Session,
        account_id: int,
        broker_type: str,
        new_start: date,
        new_end: date,
    ) -> list[BrokerDataSource]:
        """Get all sources that overlap with the given date range."""
        return (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == account_id,
                BrokerDataSource.broker_type == broker_type,
                BrokerDataSource.status == "completed",
                BrokerDataSource.start_date <= new_end,
                BrokerDataSource.end_date >= new_start,
            )
            .all()
        )


def get_overlap_detector() -> BrokerOverlapDetector:
    """Get an overlap detector instance.

    Note: BrokerOverlapDetector is stateless, so each call returns a new instance.
    This factory function exists for consistency with other service patterns.
    """
    return BrokerOverlapDetector()
