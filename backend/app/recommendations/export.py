"""Analysis view export service (FR-034 / T-064)."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Recommendation, SavedAnalysisView


def export_analysis_view(
    db: Session,
    view_id: UUID,
    format: str = "csv",
) -> bytes:
    """
    Export a saved analysis view with recommendations matching its filters.

    FR-034 / T-064: Generate CSV or JSON export of view data + recommendations.
    """
    view = db.query(SavedAnalysisView).filter_by(id=view_id).one_or_none()
    if view is None:
        raise ValueError(f"SavedAnalysisView {view_id} not found")

    # Query recommendations for this tenant (simple approach: all recs for now)
    # In a full implementation, filters_config would filter by metrics/date/domain
    recs = db.query(Recommendation).filter_by(tenant_id=view.tenant_id).all()

    if format == "csv":
        return _export_csv(view, recs)
    elif format == "json":
        return _export_json(view, recs)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _export_csv(view: SavedAnalysisView, recs: list[Recommendation]) -> bytes:
    """Export view and recommendations as CSV."""
    output = io.StringIO()

    # Header
    output.write("AlpMark Analysis View Export\n")
    output.write(f"View: {view.name}\n")
    if view.description:
        output.write(f"Description: {view.description}\n")
    output.write(f"Exported: {datetime.now(UTC).isoformat()}\n")
    output.write(f"Filters: {view.filters_config}\n")
    output.write("\n")

    # Recommendations
    output.write(
        "ID,Status,Domain,Estimated Impact,"
        "Approved At,Implementation Gap,Implemented At,"
        "Outcome Observed At\n"
    )
    for rec in recs:
        output.write(
            f"{rec.id},{rec.status},{rec.domain},{rec.estimated_impact},"
            f"{rec.approved_at},{rec.implementation_gap_flag},"
            f"{rec.implemented_at},{rec.outcome_observed_at}\n"
        )

    return output.getvalue().encode("utf-8")


def _export_json(view: SavedAnalysisView, recs: list[Recommendation]) -> bytes:
    """Export view and recommendations as JSON."""
    import json

    data = {
        "view": {
            "id": str(view.id),
            "name": view.name,
            "description": view.description,
            "filters_config": view.filters_config,
            "created_at": view.created_at.isoformat(),
            "updated_at": view.updated_at.isoformat(),
        },
        "exported_at": datetime.now(UTC).isoformat(),
        "recommendations": [
            {
                "id": str(rec.id),
                "status": rec.status,
                "domain": rec.domain,
                "estimated_impact": float(rec.estimated_impact)
                if rec.estimated_impact
                else None,
                "approved_at": rec.approved_at.isoformat()
                if rec.approved_at
                else None,
                "implementation_gap_flag": rec.implementation_gap_flag,
                "implemented_at": rec.implemented_at.isoformat()
                if rec.implemented_at
                else None,
                "outcome_observed_at": rec.outcome_observed_at.isoformat()
                if rec.outcome_observed_at
                else None,
            }
            for rec in recs
        ],
    }
    return json.dumps(data, indent=2).encode("utf-8")
